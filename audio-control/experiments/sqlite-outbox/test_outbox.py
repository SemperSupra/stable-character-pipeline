"""CPU-only SQLite transactional outbox invariants, no audio or user records."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from outbox import Conflict, Invalid, Store

P = "human_synthetic"
S = "session_demo"
T = "selected_device_synthetic"
PLAN = hashlib.sha256(b"original public synthetic intent").hexdigest()

class SQLiteOutboxQualification(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "control.sqlite"

    def admit(self, store, op="op_start", principal=P, session=S):
        return store.apply(principal, session, op, "request_start", T, 7, PLAN,
                           synthetic_human_grant=True)

    def test_atomic_intent_and_stop_fences_unissued_start(self):
        with Store(self.db) as s:
            first = self.admit(s)
            self.assertEqual((first.state, first.effects), ("start_pending", ("host_authorize_then_start",)))
            self.assertEqual(s.counts(), (1, 1))
        with Store(self.db) as s:
            recovered = s.recovery_snapshot(P, S)
            self.assertTrue(recovered["requires_host_reconcile"])
            self.assertFalse(recovered["may_issue_start"])
            self.assertIn(["host_authorize_then_start", "pending"], recovered["effects"])
            stop = s.apply(P, S, "op_stop", "stop", T, 7)
            self.assertEqual((stop.state, stop.effects), ("stop_pending", ("host_stop_now",)))
            effects = s.recovery_snapshot(P, S)["effects"]
            self.assertIn(["host_authorize_then_start", "canceled_by_stop"], effects)
            self.assertIn(["host_stop_now", "pending"], effects)
            self.assertEqual(s.counts(), (2, 2))
            replay = self.admit(s)
            self.assertTrue(replay.replayed)
            self.assertEqual(replay.effects, ())
            self.assertEqual(replay.state, "start_pending")  # Original historical receipt.
            self.assertEqual(s.recovery_snapshot(P, S)["state"], "stop_pending")

    def test_absent_human_grant_does_not_persist(self):
        with Store(self.db) as s:
            with self.assertRaises(Invalid):
                s.apply(P, S, "unauthorized", "request_start", T, 7, PLAN)
            self.assertEqual(s.counts(), (0, 0))
            self.assertTrue(s.recovery_snapshot(P, S)["requires_host_reconcile"])

    def test_conflicting_replay_and_atomic_rollback(self):
        with Store(self.db) as s:
            self.admit(s)
            with self.assertRaises(Conflict):
                s.apply(P, S, "op_start", "stop", T, 7)
            with self.assertRaises(Conflict):
                s.apply(P, S, "wrong_binding", "stop", "another_device", 7)
            with self.assertRaises(Invalid):
                s.apply(P, "../bad", "id", "stop", T, 7)
            self.assertEqual(s.counts(), (1, 1))

    def test_stop_unknown_target_never_fabricates_physical_silence(self):
        with Store(self.db) as s:
            result = s.apply(P, S, "stop_first", "stop", T, 7)
            self.assertEqual(result.state, "unknown_stop_requested")
            self.assertEqual(result.effects, ("discover_then_stop",))
            self.assertTrue(s.recovery_snapshot(P, S)["requires_host_reconcile"])
            self.assertFalse(s.recovery_snapshot(P, S)["may_issue_start"])
            followup = s.apply(P, S, "second_stop", "stop", T, 7)
            self.assertEqual(followup.state, "unknown_stop_requested")
            self.assertEqual(followup.effects, ("discover_then_stop",))
            with self.assertRaises(Conflict):
                self.admit(s)

    def test_principal_scoped_id_collision(self):
        with Store(self.db) as s:
            self.admit(s, principal="human_a")
            self.admit(s, principal="human_b")
            self.assertEqual(s.counts(), (2, 2))

    def test_separate_process_exit_and_reopen(self):
        script = (
            "from pathlib import Path;from outbox import Store;"
            "import sys;"
            "s=Store(Path(sys.argv[1]));"
            "r=s.apply('human_synthetic','session_demo','op_start',"
            "'request_start','selected_device_synthetic',7,sys.argv[2],"
            "synthetic_human_grant=True);"
            "print(r.state);s.close()"
        )
        cwd = str(Path(__file__).resolve().parent)
        run = subprocess.run([sys.executable, "-c", script, str(self.db), PLAN],
                             cwd=cwd, capture_output=True, text=True, check=True)
        self.assertEqual(run.stdout.strip(), "start_pending")
        with Store(self.db) as s:
            self.assertEqual(s.recovery_snapshot(P, S)["state"], "start_pending")
            self.assertTrue(s.recovery_snapshot(P, S)["requires_host_reconcile"])
            replay = self.admit(s)
            self.assertTrue(replay.replayed)
            self.assertEqual(replay.effects, ())

    def test_concurrent_writers_receive_single_eligibility(self):
        count = 6
        barrier = threading.Barrier(count)
        def worker(_):
            with Store(self.db) as s:
                barrier.wait(timeout=10)
                return self.admit(s)
        with Store(self.db):
            pass  # Initialize WAL/schema before concurrent open interviews.
        with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
            all_results = list(pool.map(worker, range(count)))
        self.assertEqual(sum(not x.replayed for x in all_results), 1)
        self.assertEqual(sum(bool(x.effects) for x in all_results), 1)
        with Store(self.db) as s:
            self.assertEqual(s.counts(), (1, 1))
            self.assertTrue(s.recovery_snapshot(P, S)["requires_host_reconcile"])

    def test_sqlite_wal_and_full_synchronous_are_actually_set(self):
        with Store(self.db) as s:
            self.assertEqual(s.conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal")
            self.assertEqual(s.conn.execute("PRAGMA synchronous").fetchone()[0], 2)
            self.assertEqual(s.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
