"""Negative scientific promotion controls; all cases synthetic source-contract fixtures."""
import unittest,hashlib,json,copy
from adjudicate import adjudicate,RIGHTS,CAMERAS,SOURCE_SHA,MODEL_SHA,sha
def fixtures(profile="forward"):
 # Original SHA is a frozen public source; actual integration checks full byte identity.
 # For synthetic controls, use original source bytes fetched in CI via separate integration,
 # and exercise inner logic by patching only the explicit SHA lookup in a subclass.
 source={"schema":"scp.walk_w7a_original_approach.v1","rights":RIGHTS,"profile":profile,"fps_num":12,"fps_den":1,"actors":[{},{}]}
 raw=json.dumps(source,sort_keys=True).encode();digest=sha(raw)
 from adjudicate import SOURCE_SHA as pins
 pins[profile]=digest
 native={"source_sha256":digest,"rights":RIGHTS}
 render={"source_motion_sha256":digest,"rights":RIGHTS,"W8_arm_motion":"ACTUAL_KEYED_RIGID_UPPER_PROXY_24FRAME","torso_arm_skinning":"NOT_DEFORM_RIGGED","cameras":[]}
 rollup={"source_motion_sha256":digest,"status":"PASS_ALL_REQUIRED_VIEWS_L1_ONLY","cameras":[]}
 prior={"source_sha256":digest,"rights":RIGHTS,"status":"FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED","naturalness_acceptance":"NO","real_person_R009":"HELD"}
 views={};hog={};decodes={}
 for i,c in enumerate(CAMERAS):
  v=b"VIDEO"+bytes([i])*1200
  digest_video=sha(v)
  render["cameras"].append({"camera":c,"video_sha256":digest_video})
  rollup["cameras"].append({"camera":c,"video_sha256":digest_video,"status":"PASS_L1_VIDEO_ONLY"})
  views[c]={"video":v,"qa":{"schema":"scp.visualqa.l1_video.v1","source_sha256":digest_video,"frames_decoded":24,"video":{"rate":"12/1"},"status":"PASS_L1_VIDEO_ONLY","failures":[]}}
  hog[c]={"schema":"scp.visualqa.w9b_clean_hog.v1","profile":profile,"camera":c,"original_clean_h264_sha256":digest_video,"model_weights_sha256":MODEL_SHA,"gt_supplied_to_detector":False,"independent_pose_landmarks":"NOT_AVAILABLE_HOG_BOXES_ONLY","rendered_human_behavior":"UNKNOWN_NO_POSE_ROM_OR_GAIT_PRIOR","observations":[{"tick":n,"pts_num":n,"pts_den":12,"candidate_count":0,"candidates":[]} for n in range(24)],"frames_with_candidates":0,"frames_with_more_than_two_candidates":0}
  decodes[c]={"frames_decoded":24,"source_sha256":digest_video,"fps":"12/1","decoded_framemd5_manifest_sha256":"a"*64}
 geom={"schema":"scp.visualqa.w9c_independent_clock_projection.v1","profile":profile,"source_sha256":sha(raw),"status":"PASS_SYNCHRONIZED_SOURCE_PROJECTION_ONLY","native_synchronized_camera_sample_count":288,"same_tick_pair_count":24,"exact_W8_201_pixel_correspondence":"NOT_RUN_DIFFERENT_NATIVE_MODEL_BINARY","max_uv_error":1e-7}
 return [profile,raw,native,render,rollup,prior,views,hog,geom,decodes]
class ScientificControls(unittest.TestCase):
 def setUp(self):self.args=fixtures()
 def runq(self):return adjudicate(*self.args)
 def negative(self,code):
  with self.assertRaisesRegex(ValueError,code):self.runq()
 def test_fail_dominates_green_l1_geometry_and_detector(self):
  r=self.runq();self.assertEqual(r["overall"],"FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED")
  self.assertFalse(r["can_merge_release_deploy_or_promote"])
 def test_changed_clean_video(self):
  self.args[6][CAMERAS[0]]["video"]+=b"x";self.negative("VIDEO_SHA_MISMATCH")
 def test_cross_source_model(self):
  self.args[7][CAMERAS[1]]["original_clean_h264_sha256"]="0"*64;self.negative("MODEL_SCOPE")
 def test_forced_human_behavior_pass(self):
  self.args[5]["status"]="PASS_HUMAN";self.negative("FORGED_BEHAVIOR")
 def test_model_claims_pose_from_hog(self):
  self.args[7][CAMERAS[0]]["independent_pose_landmarks"]="PASS";self.negative("MODEL_SCOPE")
 def test_gt_leak_to_model(self):
  self.args[7][CAMERAS[0]]["gt_supplied_to_detector"]=True;self.negative("MODEL_SCOPE")
 def test_missing_view(self):
  del self.args[7][CAMERAS[0]];self.negative("MISSING_CLEAN_OBSERVER")
 def test_wrong_native_camera(self):
  self.args[3]["cameras"][0]["camera"]="OriginalOblique";self.negative("REQUIRED_VIEWS")
 def test_wrong_geometry_scope(self):
  self.args[8]["exact_W8_201_pixel_correspondence"]="PASS";self.negative("GEOMETRY_SOURCE")
 def test_false_l1_success(self):
  self.args[6][CAMERAS[0]]["qa"]["status"]="FAIL"
  self.negative("L1_FROZEN_STATUS")
 def test_authentic_l1_fail_dominates(self):
  c=CAMERAS[0];self.args[6][c]["qa"]["status"]="FAIL"
  self.args[6][c]["qa"]["failures"]=["FREEZE_SPAN_DETECTED"]
  self.args[4]["cameras"][0]["status"]="FAIL"
  self.args[4]["status"]="FAIL_L1_ANY_REQUIRED_VIEW"
  self.args[5]["status"]="FAIL_L1_AND_FULLBODY_PROXY_UNQUALIFIED"
  self.assertEqual(self.runq()["overall"],"FAIL_L1_AND_FULLBODY_HUMAN_BEHAVIOR")
 def test_wrong_source_rights(self):
  self.args[2]["rights"]="PRIVATE_RIGHTS";self.negative("RIGHTS_OR_PROXY")
if __name__=="__main__":unittest.main()
