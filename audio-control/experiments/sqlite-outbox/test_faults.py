"""Fault-injection falsifiers for synthetic SQLite WAL command/outbox atomicity."""
from pathlib import Path
import hashlib
import sqlite3
import tempfile
import unittest

from outbox import Store

P = "synthetic_human"
S = "synthetic_session"
T = "synthetic_device"
DIGEST = hashlib.sha256(b"synthetic public plan").hexdigest()

class TransactionFailureQualification(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "audio-control.sqlite"

    def test_outbox_insert_abort_rolls_back_entire_start_intent(self):
        with Store(self.db) as s:
            s.conn.execute("""CREATE TRIGGER simulate_full_outbox
                BEFORE INSERT ON outbox
                BEGIN SELECT RAISE(ABORT, 'synthetic outbox persistence failure'); END""")
            with self.assertRaises(sqlite3.IntegrityError):
                s.apply(P,S,"start1","request_start",T,1,DIGEST,synthetic_human_grant=True)
            self.assertEqual(s.counts(), (0,0))
            self.assertEqual(s.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],0)
            self.assertTrue(s.recovery_snapshot(P,S)["requires_host_reconcile"])
            s.conn.execute("DROP TRIGGER simulate_full_outbox")
            resumed=s.apply(P,S,"start1","request_start",T,1,DIGEST,synthetic_human_grant=True)
            self.assertFalse(resumed.replayed)
            self.assertEqual(s.counts(),(1,1))

    def test_stop_outbox_abort_rolls_back_cancellation_and_leaves_physical_state_unknown(self):
        with Store(self.db) as s:
            s.apply(P,S,"start1","request_start",T,1,DIGEST,synthetic_human_grant=True)
            s.conn.execute("""CREATE TRIGGER simulate_stop_write_failure
                BEFORE INSERT ON outbox
                WHEN NEW.effect = 'host_stop_now'
                BEGIN SELECT RAISE(ABORT, 'synthetic stop outbox failure'); END""")
            with self.assertRaises(sqlite3.IntegrityError):
                s.apply(P,S,"stop1","stop",T,1)
            snap=s.recovery_snapshot(P,S)
            self.assertEqual(snap["state"],"start_pending")
            self.assertIn(["host_authorize_then_start","pending"],snap["effects"])
            self.assertEqual(s.counts(),(1,1))
            self.assertTrue(snap["requires_host_reconcile"])
            self.assertFalse(snap["may_issue_start"])
            # This is a deliberate demonstration that SQLite persistence
            # failure alone CANNOT guarantee physical emergency STOP.
            s.conn.execute("DROP TRIGGER simulate_stop_write_failure")
            result=s.apply(P,S,"stop1","stop",T,1)
            self.assertEqual(result.state,"stop_pending")
            self.assertEqual(s.counts(),(2,2))

    def test_writer_lock_rejects_without_partially_admitting_emergency_stop(self):
        with Store(self.db) as first:
            first.apply(P,S,"start1","request_start",T,1,DIGEST,synthetic_human_grant=True)
        with Store(self.db) as locker, Store(self.db) as contender:
            locker.conn.execute("BEGIN IMMEDIATE")
            contender.conn.execute("PRAGMA busy_timeout=50")
            try:
                with self.assertRaises(sqlite3.OperationalError):
                    contender.apply(P,S,"stop_when_locked","stop",T,1)
            finally:
                locker.conn.execute("ROLLBACK")
            self.assertEqual(contender.counts(),(1,1))
            self.assertEqual(contender.recovery_snapshot(P,S)["state"],"start_pending")
            self.assertTrue(contender.recovery_snapshot(P,S)["requires_host_reconcile"])
        # Caller/host must have a separately privileged, non-SQLite-dependent
        # emergency STOP path; the SQLite experiment has NO such implementation.

if __name__ == "__main__":
    unittest.main(verbosity=2)
