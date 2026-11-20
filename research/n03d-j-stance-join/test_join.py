import unittest,math,sys
from pathlib import Path
from join import parse_partition,reconcile
class FakeSegment:
 @staticmethod
 def analyze(s):
  return {"algorithms":{k:{"segments":[],"raw_candidate_frames":0} for k in ("height_velocity","hysteresis_min_dwell","viterbi_transition_cost")},
          "near_ground_skate_sample_indices":[],"penetration_over_10mm_sample_indices":[]}
def samples():
 return [{"t_s":round(i/24,9),"z_m":.004,"xy_m":[i*.001,0.]} for i in range(143)]
def pair():
 d={"schema":"scp.n03d-g.evaluated-foot-contact-observer.v1",
  "source_scene_sha256":"a"*64,"sample_count_per_side":143,"frame_rate_hz":24,
  "side_labels":"REST_LOCAL_X_PARTITION_NOT_VERIFIED_ANATOMICAL_SIDES",
  "natural_gait_accepted":False,"mvp_accepted":False,"actors":[]}
 f={"schema":"scp.n03d-f1.native-shoe-foot-weights.v1",
  "source_scene_sha256":"a"*64,"source_trace_sha256":"b"*64,
  "gait_contact_accepted":False,"anatomical_side_verified":False,"actors":[]}
 for name in ("AsterOriginal","JuniperOriginal"):
  d["actors"].append({"actor":name,"native_bones":163,"sides":{k:{"samples":samples(),"anatomical_side_verified":False} for k in ("rest_local_x_negative","rest_local_x_positive")}})
  f["actors"].append({"actor":name,"native_163_bone_source_rig":True,
      "partitions":[{"rest_local_partition":key,"candidate_rig_side":{"label":v,"dominance":1.,"reason":"CANDIDATE_SOURCE_RIG_SIDE_NOT_ANATOMICAL"}} for key,v in (("rest_local_x_negative","R"),("rest_local_x_positive","L"))]})
 return d,f
class SourceJoin(unittest.TestCase):
 def run_pair(self,d=None,f=None):
  if d is None or f is None:d,f=pair()
  return reconcile(d,f,FakeSegment,"b"*64,"c"*64)
 def test_exact_source_valid_no_contact_accepted(self):
  x=self.run_pair()
  self.assertEqual(x["rate_hz"],24)
  self.assertFalse(x["physical_foot_plant_accepted"])
  self.assertEqual([x["actors"][0]["partitions"][k]["candidate_mpbf_rig_foot_side"] for k in (0,1)],["R","L"])
 def test_source_scene_drift(self):
  d,f=pair();f["source_scene_sha256"]="9"*64
  with self.assertRaisesRegex(ValueError,"DIFFERENT_NATIVE_SOURCE"):self.run_pair(d,f)
 def test_trace_receipt_drift(self):
  d,f=pair();f["source_trace_sha256"]="9"*64
  with self.assertRaisesRegex(ValueError,"TRACE_RECEIPT"):self.run_pair(d,f)
 def test_bad_clock(self):
  d,f=pair();d["actors"][0]["sides"]["rest_local_x_negative"]["samples"][44]["t_s"]=.5
  with self.assertRaisesRegex(ValueError,"CLOCK_NOT_24HZ"):self.run_pair(d,f)
 def test_wrong_actor(self):
  d,f=pair();d["actors"][0]["actor"]="Naomi"
  with self.assertRaisesRegex(ValueError,"SOURCE_ACTOR_SET"):self.run_pair(d,f)
 def test_missing_map(self):
  d,f=pair();f["actors"][0]["partitions"].pop()
  with self.assertRaisesRegex(ValueError,"SOURCE_PARTITION_COUNT"):self.run_pair(d,f)
 def test_same_side_twice(self):
  d,f=pair();f["actors"][0]["partitions"][1]["candidate_rig_side"]["label"]="R"
  with self.assertRaisesRegex(ValueError,"NOT_ONE_TO_ONE"):self.run_pair(d,f)
 def test_low_source_confidence(self):
  d,f=pair();f["actors"][0]["partitions"][0]["candidate_rig_side"]["dominance"]=.6
  with self.assertRaisesRegex(ValueError,"LOW_SHOE"):self.run_pair(d,f)
 def test_unverified_anatomy_stays_false(self):
  d,f=pair();d["actors"][0]["sides"]["rest_local_x_negative"]["anatomical_side_verified"]=True
  with self.assertRaisesRegex(ValueError,"ANATOMICAL_SIDE"):self.run_pair(d,f)
 def test_false_source_approval(self):
  d,f=pair();d["natural_gait_accepted"]=True
  with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_SOURCE_ACCEPTANCE"):self.run_pair(d,f)
 def test_nan_rejected(self):
  d,f=pair();d["actors"][0]["sides"]["rest_local_x_negative"]["samples"][18]["z_m"]=float("nan")
  with self.assertRaisesRegex(ValueError,"INVALID_GROUND_Z"):self.run_pair(d,f)
 def test_missing_sample(self):
  d,f=pair();d["actors"][0]["sides"]["rest_local_x_negative"]["samples"].pop()
  with self.assertRaisesRegex(ValueError,"SOURCE_24HZ"):self.run_pair(d,f)
if __name__=="__main__":unittest.main()
