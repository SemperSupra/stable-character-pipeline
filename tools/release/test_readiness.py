import importlib.util
import pathlib
import unittest
spec=importlib.util.spec_from_file_location("readiness",pathlib.Path(__file__).parent/"readiness.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def fixture():
 sha="a"*40
 return {"schema":"scp.synthetic-release-intake.v1","source_commit":sha,"scope":"public-original-synthetic","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","scientific":{"human_behavior":"FAIL_ABSTRACT_LIMBS_ONLY","human_anatomy":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM"},"release":"HELD_R009_NOT_RUN_NOT_ADMITTED","workflows":[{"kind":kind,"source_commit":sha,"status":"completed","conclusion":"success","run_id":i+1,"artifact_digest":None} for i,kind in enumerate(("native_two_camera","source_recovery","human_browser"))]}
class R16Intake(unittest.TestCase):
 def test_even_all_claimed_green_keeps_release_hold(self):
  self.assertEqual(m.audit(fixture())["decision"],"HOLD_RELEASE_AND_CPE_PROMOTION")
 def test_missing_native_rejected(self):
  r=fixture();r["workflows"].pop()
  with self.assertRaises(m.InvalidEvidence):m.audit(r)
 def test_cross_source_rejected(self):
  r=fixture();r["workflows"][0]["source_commit"]="b"*40
  with self.assertRaises(m.InvalidEvidence):m.audit(r)
 def test_forged_release_rejected(self):
  r=fixture();r["release"]="RELEASED"
  with self.assertRaises(m.InvalidEvidence):m.audit(r)
 def test_failed_workflow_rejected(self):
  r=fixture();r["workflows"][0]["conclusion"]="failure"
  with self.assertRaises(m.InvalidEvidence):m.audit(r)
 def test_private_source_rejected(self):
  r=fixture();r["scope"]="private-human"
  with self.assertRaises(m.InvalidEvidence):m.audit(r)
if __name__=="__main__":unittest.main()
