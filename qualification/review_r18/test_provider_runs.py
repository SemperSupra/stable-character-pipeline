import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import provider_runs as m
def fixture():
 return {rid:{"id":rid,"head_sha":m.SOURCE,"path":path,"event":"pull_request",
  "status":"completed","conclusion":"success","run_attempt":1,
  "repository":{"full_name":m.REPO},"head_repository":{"full_name":m.REPO}}
  for rid,path in m.REQUIRED.items()}
class ProviderRunReview(unittest.TestCase):
 def test_complete_provider_snapshot_still_release_hold(self):
  report=m.validate(fixture())
  self.assertEqual(report["decision"],"HOLD_RELEASE_AND_CPE_PROMOTION")
  self.assertEqual(report["artifact_byte_integrity"],"NOT_VERIFIED_BY_RUN_METADATA")
 def deny(self,change,code):
  rows=fixture();change(rows)
  with self.assertRaisesRegex(m.ProviderMismatch,code):m.validate(rows)
 def test_foreign_repository(self):
  self.deny(lambda x:x[41237673021]["repository"].update(full_name="foreign/repo"),"REPOSITORY")
 def test_wrong_branch_sha(self):
  self.deny(lambda x:x[41237672990].update(head_sha="b"*40),"HEAD_SHA")
 def test_same_job_substitution(self):
  self.deny(lambda x:x[41237673011].update(path=m.REQUIRED[41237673021]),"WORKFLOW_PATH")
 def test_cancelled_or_failed(self):
  self.deny(lambda x:x[41237673021].update(conclusion="failure"),"RUN_NOT_GREEN")
 def test_non_pr_run(self):
  self.deny(lambda x:x[41237673011].update(event="workflow_dispatch"),"RUN_TRIGGER")
 def test_missing_run(self):
  self.deny(lambda x:x.pop(41237673011),"RUN_SET")
if __name__=="__main__":unittest.main()
