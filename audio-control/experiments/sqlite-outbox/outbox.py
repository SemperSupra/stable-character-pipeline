"""Synthetic audio-control SQLite WAL/outbox interview (Python stdlib).

Not a deployable audio daemon. Commands commit intent + effect records atomically
within SQLite before any external effect is eligible. No real audio or host auth.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import sqlite3
from pathlib import Path

_VALID_ID = re.compile(r"^[A-Za-z0-9_.-]{1,96}$")

class Invalid(ValueError):
    pass

class Conflict(ValueError):
    pass

@dataclass(frozen=True)
class Result:
    status: str
    revision: int
    state: str
    replayed: bool
    effects: tuple[str, ...]

class Store:
    def __init__(self, file: Path | str) -> None:
        self.file = Path(file)
        if not self.file.is_absolute() or str(self.file) == ":memory:":
            raise Invalid("require an existing absolute on-disk database path")
        if not self.file.parent.is_dir():
            raise Invalid("database directory must exist")
        self.conn = sqlite3.connect(str(self.file), timeout=10, isolation_level=None)
        if self.conn.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower() != "wal":
            raise Invalid("WAL not admitted by SQLite")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
            principal TEXT NOT NULL, session TEXT NOT NULL, target TEXT NOT NULL,
            epoch INTEGER NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
            PRIMARY KEY(principal, session))""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS operations (
            principal TEXT NOT NULL, session TEXT NOT NULL, opid TEXT NOT NULL,
            action TEXT NOT NULL, body_hash TEXT NOT NULL, receipt TEXT NOT NULL,
            PRIMARY KEY(principal, session, opid))""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS outbox (
            principal TEXT NOT NULL, session TEXT NOT NULL, opid TEXT NOT NULL,
            effect TEXT NOT NULL, status TEXT NOT NULL,
            PRIMARY KEY(principal, session, opid, effect),
            FOREIGN KEY(principal, session, opid) REFERENCES operations(principal, session, opid))""")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _validate(principal: str, session: str, opid: str, target: str) -> None:
        if not all(_VALID_ID.fullmatch(s) for s in (principal, session, opid, target)):
            raise Invalid("unsafe or blank scoped identity")

    @staticmethod
    def _body_hash(action: str, target: str, epoch: int, plan_sha256: str) -> str:
        data = json.dumps([action, target, epoch, plan_sha256], separators=(",", ":")).encode()
        return hashlib.sha256(data).hexdigest()

    def apply(self, principal: str, session: str, opid: str, action: str,
              target: str, epoch: int, plan_sha256: str = "",
              *, synthetic_human_grant: bool = False) -> Result:
        self._validate(principal, session, opid, target)
        if action not in {"request_start", "stop"} or epoch < 1:
            raise Invalid("unsupported action/epoch")
        if action == "request_start" and not (len(plan_sha256) == 64 and
             all(c in "0123456789abcdef" for c in plan_sha256)):
            raise Invalid("start requires immutable lowercase SHA-256 plan")
        digest = self._body_hash(action, target, epoch, plan_sha256)
        c = self.conn
        c.execute("BEGIN IMMEDIATE")
        try:
            old = c.execute(
                "SELECT body_hash, receipt FROM operations WHERE principal=? AND session=? AND opid=?",
                (principal, session, opid)).fetchone()
            if old is not None:
                if old[0] != digest:
                    raise Conflict("operation ID reused with different action/content")
                parsed = json.loads(old[1])
                c.execute("COMMIT")
                return Result(parsed["status"], parsed["revision"], parsed["state"], True, ())
            existing = c.execute(
                "SELECT target, epoch, state, revision FROM sessions WHERE principal=? AND session=?",
                (principal, session)).fetchone()
            effect = None
            if action == "request_start":
                if not synthetic_human_grant:
                    raise Invalid("synthetic human grant absent; cannot request physical start")
                if existing is not None:
                    raise Conflict("already an admitted session; restart requires new session")
                new_state, revision = "start_pending", 1
                c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)",
                          (principal, session, target, epoch, new_state, revision))
                effect = "host_authorize_then_start"
            else:
                if existing is None:
                    # STOP must not fabricate confirmation of silence. Unknown
                    # target/lease demands privileged host discovery and STOP.
                    new_state, revision = "unknown_stop_requested", 1
                    c.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?)",
                              (principal, session, target, epoch, new_state, revision))
                    effect = "discover_then_stop"
                else:
                    if existing[0] != target or existing[1] != epoch:
                        raise Conflict("stop target/epoch differs from accepted binding")
                    new_state, revision = "stop_pending", existing[3] + 1
                    c.execute("UPDATE sessions SET state=?,revision=? WHERE principal=? AND session=?",
                              (new_state, revision, principal, session))
                    # A prepared START must never be eligible once STOP commits.
                    c.execute("""UPDATE outbox SET status='canceled_by_stop'
                        WHERE principal=? AND session=? AND effect='host_authorize_then_start'
                        AND status='pending'""", (principal, session))
                    effect = "host_stop_now"
            receipt = {"status": "accepted", "revision": revision, "state": new_state}
            c.execute("INSERT INTO operations VALUES(?,?,?,?,?,?)",
                      (principal, session, opid, action, digest,
                       json.dumps(receipt, separators=(",", ":"), sort_keys=True)))
            if effect:
                c.execute("INSERT INTO outbox VALUES(?,?,?,?,?)",
                          (principal, session, opid, effect, "pending"))
            c.execute("COMMIT")
            return Result(receipt["status"], revision, new_state, False, (effect,) if effect else ())
        except BaseException:
            c.execute("ROLLBACK")
            raise

    def recovery_snapshot(self, principal: str, session: str) -> dict:
        """Read only. Never advertises a restarted physical START as safe."""
        old = self.conn.execute(
            "SELECT target, epoch, state, revision FROM sessions WHERE principal=? AND session=?",
            (principal, session)).fetchone()
        if old is None:
            return {"state": "unknown", "requires_host_reconcile": True,
                    "may_issue_start": False, "effects": []}
        effects = self.conn.execute(
            "SELECT effect,status FROM outbox WHERE principal=? AND session=? ORDER BY opid,effect",
            (principal, session)).fetchall()
        return {"state": old[2], "revision": old[3], "epoch": old[1],
                "requires_host_reconcile": True, "may_issue_start": False,
                "effects": [list(x) for x in effects]}

    def counts(self) -> tuple[int, int]:
        return (self.conn.execute("SELECT COUNT(*) FROM operations").fetchone()[0],
                self.conn.execute("SELECT COUNT(*) FROM outbox").fetchone()[0])
