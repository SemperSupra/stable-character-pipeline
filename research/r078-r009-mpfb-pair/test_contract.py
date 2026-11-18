import copy,unittest
import contract as c
class Profiles(unittest.TestCase):
 def example(self):
  return {"schema":c.SCHEMA,"source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
  "mpfb_upstream_commit":c.UPSTREAM,"fps":12,"frames":72,
  "actors":[{"name":x["name"],"bones":163,"body_vertices":14517,"rest_pose_sha256":"a"*64,"mid_pose_sha256":"b"*64,
  "native_body_shape_metrics":{"bbox_x_over_height":.55,"bbox_y_over_height":.23,"leg_segments":{
   "upper_L_over_height":.23,"upper_R_over_height":.23,"lower_L_over_height":.21,"lower_R_over_height":.21},
   "measured_from":"EVALUATED_SAVED_MPF_BODY_AND_NATIVE_REST_RIG","anatomical_landmark_centres_accepted":False}} for x in c.PROFILES],
  "photoreal_accepted":False,"gait_accepted":False,"real_identity_accepted":False,
  "mvp_accepted":False,"release_authorized":False}
 def test_two_originals(self):self.assertTrue(c.validate_profiles())
 def test_distinct_bodies_required(self):
  s=[dict(x) for x in c.PROFILES];s[1]["height"]=s[0]["height"];s[1]["weight"]=s[0]["weight"]
  with self.assertRaisesRegex(ValueError,"SUBSTITUTE_BODIES_NOT_DISTINCT"):c.validate_profiles(s)
 def test_out_of_range(self):
  s=[dict(x) for x in c.PROFILES];s[0]["weight"]=1.1
  with self.assertRaisesRegex(ValueError,"MACRO_OUT_OF_ENVELOPE"):c.validate_profiles(s)
 def test_forged_actor(self):
  s=[dict(x) for x in c.PROFILES];s[0]["name"]="NaomiWu"
  with self.assertRaisesRegex(ValueError,"ORIGINAL_IDENTITY_KEYS_CHANGED"):c.validate_profiles(s)
 def test_source_trajectory(self):
  a,b=c.source_centers(0);x,y=c.source_centers(71)
  self.assertAlmostEqual(b-a,6.7);self.assertAlmostEqual(y-x,1.58)
 def test_bad_frame(self):
  with self.assertRaisesRegex(ValueError,"FRAME_OUT_OF_RANGE"):c.source_centers(72)
 def test_valid_narrow_only(self):self.assertTrue(c.validate_receipt(self.example()))
 def test_false_mvp_rejected(self):
  r=self.example();r["mvp_accepted"]=True
  with self.assertRaisesRegex(ValueError,"FALSE_PRODUCT_ACCEPTANCE"):c.validate_receipt(r)
 def test_static_body_rejected(self):
  r=self.example();r["actors"][0]["mid_pose_sha256"]="a"*64
  with self.assertRaisesRegex(ValueError,"NOT_DEFORMING_REAL_MPF_BODIES"):c.validate_receipt(r)
 def test_synthetic_manikin_forged_as_mpfb(self):
  r=self.example();r["actors"][0]["bones"]=17
  with self.assertRaisesRegex(ValueError,"NOT_REAL_MPF_FRONTEND_RIG"):c.validate_receipt(r)
 def test_upstream_provenance_rejected(self):
  r=self.example();r["mpfb_upstream_commit"]="0"*40
  with self.assertRaisesRegex(ValueError,"UPSTREAM_NOT_PINNED"):c.validate_receipt(r)
 def test_nonfemale_preset_rejected_as_model_drift(self):
  s=[dict(x) for x in c.PROFILES];s[0]["gender"]=1.1
  with self.assertRaisesRegex(ValueError,"MACRO_OUT_OF_ENVELOPE"):c.validate_profiles(s)
 def test_missing_native_metrics_fails_closed(self):
  r=self.example();del r["actors"][0]["native_body_shape_metrics"]
  with self.assertRaisesRegex(ValueError,"SHAPE_METRICS_MISSING"):c.validate_receipt(r)
 def test_fabricated_anatomical_centres_rejected(self):
  r=self.example();r["actors"][0]["native_body_shape_metrics"]["anatomical_landmark_centres_accepted"]=True
  with self.assertRaisesRegex(ValueError,"FALSE_ANATOMY_ACCEPTANCE"):c.validate_receipt(r)
 def test_nonfinite_geometry_rejected(self):
  r=self.example();r["actors"][1]["native_body_shape_metrics"]["bbox_y_over_height"]=float("nan")
  with self.assertRaisesRegex(ValueError,"INVALID_BODY_METRIC"):c.validate_receipt(r)
 def test_bad_character_order(self):
  r=self.example();r["actors"].reverse()
  with self.assertRaisesRegex(ValueError,"SOURCE_ACTOR_NAMES_DRIFT"):c.validate_receipt(r)
if __name__=="__main__":unittest.main()
