import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from gate import decide,SCHEMA,SIDES
def fixture(kind="clean"):
 def sample(i):
  t=i/24.
  if kind=="hover":z=.05
  elif kind=="penetration" and i==22:z=-.09
  else:z=.004
  v=1.1/24 if kind=="skate" else .003/24
  return {"t_s":t,"z_m":z,"xy_m":[i*v,0.]}
 def side():
  return {"shoe_rest_mesh_sha256":"d"*64,"anatomical_side_verified":True,
   "samples":[sample(i) for i in range(143)]}
 return {"schema":SCHEMA,"source_class":"ORIGINAL_FICTIONAL_CC0",
  "source_scene_sha256":"a"*64,"retarget_action_sha256":"b"*64,
  "source_wardrobe_sha256":"c"*64,"frame_rate_hz":24,
  "actors":[{"actor":name,"sides":{side_name:side() for side_name in SIDES}} for name in ("AsterOriginal","JuniperOriginal")],
  "independent_visual_review_passed":True,"post_ik_source_rig_verified":True,"root_correction_m":.002}
class NumericGates(unittest.TestCase):
 def test_synthetic_positive_narrow_not_mvp(self):
  r=decide(fixture())
  self.assertTrue(r["contact_metrics_pass_narrow"])
  self.assertFalse(r["mvp_accepted"])
 def test_hover_no_contact_cannot_pass(self):
  r=decide(fixture("hover"))
  self.assertIn("UNKNOWN_SLIDING_NOT_OBSERVABLE",r["fail_reasons"])
  self.assertFalse(r["contact_metrics_pass_narrow"])
 def test_slide_over_threshold(self):
  r=decide(fixture("skate"))
  self.assertIn("NEAR_GROUND_SKATING_GT_0P08_MPS",r["fail_reasons"])
 def test_penetration_source(self):
  r=decide(fixture("penetration"))
  self.assertIn("PENETRATION_GT_10MM",r["fail_reasons"])
 def test_label_doesnt_prove_anatomy(self):
  s=fixture();s["actors"][0]["sides"][SIDES[0]]["anatomical_side_verified"]=False
  self.assertIn("ANATOMICAL_PARTITION_UNVERIFIED",decide(s)["fail_reasons"])
 def test_no_visual_waiver(self):
  s=fixture();s["independent_visual_review_passed"]=False
  self.assertIn("INDEPENDENT_VISUAL_REVIEW_NOT_PASSED",decide(s)["fail_reasons"])
 def test_root_lift_over_limit(self):
  s=fixture();s["root_correction_m"]=.2
  self.assertIn("EXCESSIVE_ROOT_CORRECTION",decide(s)["fail_reasons"])
 def test_source_sha_reuse(self):
  s=fixture();s["source_scene_sha256"]="c"*64
  with self.assertRaisesRegex(ValueError,"REUSED_SOURCE"):decide(s)
 def test_missing_frames_not_pass(self):
  s=fixture();s["actors"][0]["sides"][SIDES[0]]["samples"]=s["actors"][0]["sides"][SIDES[0]]["samples"][:1]
  with self.assertRaisesRegex(ValueError,"SAMPLES_INSUFFICIENT"):decide(s)
 def test_nonmonotonic(self):
  s=fixture();s["actors"][0]["sides"][SIDES[0]]["samples"][12]["t_s"]=.0
  with self.assertRaisesRegex(ValueError,"CLOCK_NOT_MONOTONIC"):decide(s)
 def test_nonfinite(self):
  s=fixture();s["actors"][0]["sides"][SIDES[0]]["samples"][6]["z_m"]=math.nan
  with self.assertRaisesRegex(ValueError,"SHOE_Z_NONFINITE"):decide(s)
 def test_missing_kinematics(self):
  s=fixture();s["post_ik_source_rig_verified"]=False
  self.assertIn("POST_IK_RIG_NOT_VERIFIED",decide(s)["fail_reasons"])
 def test_no_false_source(self):
  s=fixture();s["source_class"]="ALISON_PROTECTED"
  with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS"):decide(s)
if __name__=="__main__":unittest.main()
