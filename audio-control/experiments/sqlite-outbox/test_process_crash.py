"""Synthetic SQLite WAL process-kill boundaries, beyond in-process ABORT tests.

No audio effect executor; committed intent is NOT evidence that sound played.
"""
from pathlib import Path
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest

from outbox import Store

P = "synthetic_human"
S = "synthetic_session"
T = "synthetic_audio_target"
SHA = hashlib.sha256(b"public no-audio plan").hexdigest()

# This child intentionally calls os._exit() with an uncommitted transaction.
# It uses the exact tables created by the candidate Store before exiting.
MID_TRANSACTION = """
import os,sqlite3,sys
p=sys.argv[1]
c=sqlite3.connect(p,isolation_level=None,timeout=5)
c.execute('PRAGMA journal_mode=WAL')
c.execute('PRAGMA synchronous=FULL')
c.execute('BEGIN IMMEDIATE')
c.execute("INSERT INTO sessions VALUES('synthetic_human','synthetic_session','synthetic_audio_target',1,'start_pending',1)")
c.execute("INSERT INTO operations VALUES('synthetic_human','synthetic_session','op_crash','request_start','a','{}')")
os._exit(91)
"""
# The candidate Store commits both operation and outbox before the process
# terminates without returning a receipt to its parent.
POST_COMMIT = """
import os,sys
from outbox import Store
s=Store(sys.argv[1])
s.apply('synthetic_human','synthetic_session','op_start','request_start',
        'synthetic_audio_target',1,sys.argv[2],synthetic_human_grant=True)
os._exit(92)
"""

class ProcessCrashBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.file=Path(temp.name)/"control.db"
        self.cwd=str(Path(__file__).resolve().parent)

    def run_child(self,script,*args,expected):
        child=subprocess.run([sys.executable,"-c",script,str(self.file),*args],
                             cwd=self.cwd,text=True,capture_output=True,timeout=15)
        self.assertEqual(child.returncode,expected,child.stderr)
        return child

    def test_terminated_uncommitted_transaction_has_no_partial_start(self):
        with Store(self.file): pass # Ensure only verified candidate schema exists.
        self.run_child(MID_TRANSACTION,expected=91)
        with Store(self.file) as s:
            self.assertEqual(s.counts(),(0,0))
            self.assertEqual(s.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],0)
            self.assertEqual(s.conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
            self.assertTrue(s.recovery_snapshot(P,S)["requires_host_reconcile"])
            self.assertFalse(s.recovery_snapshot(P,S)["may_issue_start"])

    def test_committed_start_without_delivered_receipt_is_not_redispatched(self):
        self.run_child(POST_COMMIT,SHA,expected=92)
        with Store(self.file) as s:
            snap=s.recovery_snapshot(P,S)
            self.assertEqual(snap["state"],"start_pending")
            self.assertTrue(snap["requires_host_reconcile"])
            self.assertFalse(snap["may_issue_start"])
            self.assertEqual(s.counts(),(1,1))
            replay=s.apply(P,S,"op_start","request_start",T,1,SHA,synthetic_human_grant=True)
            self.assertTrue(replay.replayed)
            self.assertEqual(replay.effects,())
            self.assertEqual(s.conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")

    def test_crash_does_not_convert_pending_intent_into_verified_device_state(self):
        self.run_child(POST_COMMIT,SHA,expected=92)
        with Store(self.file) as s:
            original=s.recovery_snapshot(P,S)
            self.assertIn(["host_authorize_then_start","pending"],original["effects"])
            stop=s.apply(P,S,"stop_after_restart","stop",T,1)
            self.assertEqual(stop.state,"stop_pending")
            current=s.recovery_snapshot(P,S)
            self.assertIn(["host_authorize_then_start","canceled_by_stop"],current["effects"])
            self.assertIn(["host_stop_now","pending"],current["effects"])
            self.assertTrue(current["requires_host_reconcile"])
            self.assertFalse(current["may_issue_start"])
            self.assertNotEqual(current["state"],"stopped")

if __name__=="__main__":
    unittest.main(verbosity=2)
