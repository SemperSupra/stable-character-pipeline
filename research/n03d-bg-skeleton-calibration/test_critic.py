"""BG independent failure controls: no cherry-picked toe fit, zero source motion or false floor."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import check,TRAIN,HOLD,MODES
def fixture():
    f={"schema":"scp.n03d-bg.world-similarity-source-to-native-360-v1",
       "source_class":"PUBLIC_ORIGINAL_CC0_THREE_CONTROLLER",
       "original_three_commit":"3f5b4896f1b28501b40aa9c408e47dba51322443",
       "source_and_native_same_public_GLBFIle":True,
       "calibration_orthogonal_no_reflection":True,
       "measured_ground_force":False,"body_style_or_actor_identity_accepted":False,
       "true_sole_contact_accepted":False,"mvp_accepted":False,
       "status":"PASS_NARROW_SOURCE_TO_NATIVE_WORLD_MATCH_HOLD_PHYSICS",
       "rig":"rigify","blender_native_bones":161,
       "source_model_git_blob":"d3327b94c302278b5471c24d712ef5dc49f0d682",
       "source_pose_sha256":"a"*64,"source_model_sha256":"b"*64,
       "calibration_fitted_using_only_original_rest_bone_centres":sorted(TRAIN),
       "out_of_sample_calibration_joints":sorted(HOLD)}
    fit={}
    for mode in MODES:
        fit[mode]={"matrix_source_world_to_native_world_colmajor":[1.]*16,
                   "train":{"rms_m":0.001 if mode.startswith("five") else .5,"max_m":.5,
                            "by_joint_m":{key:.001 for key in TRAIN}},
                   "heldout":{"rms_m":.05,"max_m":.06,
                            "by_joint_m":{key:.05 for key in HOLD}}}
    f["calibration_rest_landmark_results"]=fit
    mat={"samples":360,"stable_material_count":26,
         "fullclip_p50_xy_speed_mps":.55,"nonswing_p50_xy_speed_mps":.3,
         "nonswing_adjacent_pairs":121,"near_self_low_p50_xy_speed_mps":None,
         "near_self_low_adjacent_pairs":0,"own_min_z_m":-.01,"own_max_z_m":.06,
         "source_nonswing_is_not_force_verified":True,"actual_sole_and_ground_unverified":True}
    errs={k:{"p50_m":.01,"max_m":.05} for k in HOLD}
    f["retarget_models"]=[{"mode":mode,"actual_native_blender_frames":360,
                           "actual_native_skin_mesh_count":3,
                           "source_controller_phases_are_not_true_contact":True,
                           "physical_contact_accepted":False,
                           "real_native_foot_material":{"L":mat.copy(),"R":mat.copy()},
                           "world_ankle_and_toe_delta_errors":copy.deepcopy(errs)}
                          for mode in MODES]
    return f
class Controls(unittest.TestCase):
    def test_narrow(self):self.assertEqual(check(fixture()),"HOLD")
    def test_forge_grf(self):
        d=fixture();d["measured_ground_force"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_SOURCE"):check(d)
    def test_forge_sole(self):
        d=fixture();d["true_sole_contact_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_SOURCE"):check(d)
    def test_forge_private(self):
        d=fixture();d["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_SOURCE"):check(d)
    def test_rig_identity(self):
        d=fixture();d["source_model_git_blob"]="f"*40
        with self.assertRaisesRegex(ValueError,"WRONG_ORIGINAL"):check(d)
    def test_holdout_train_collision(self):
        d=fixture();d["calibration_fitted_using_only_original_rest_bone_centres"].append("LeftAnkle")
        with self.assertRaisesRegex(ValueError,"TRAIN_HOLDOUT"):check(d)
    def test_heldout_missing(self):
        d=fixture();d["calibration_rest_landmark_results"]["five_landmark_rest_similarity"]["heldout"]["by_joint_m"].pop("LeftToe")
        with self.assertRaisesRegex(ValueError,"TRAIN_TEST_SET_CHANGED"):check(d)
    def test_forge_no_svd(self):
        d=fixture();d["calibration_rest_landmark_results"]["five_landmark_rest_similarity"]["train"]["rms_m"]=.8
        d["calibration_rest_landmark_results"]["five_landmark_rest_similarity"]["train"]["max_m"]=.9
        with self.assertRaisesRegex(ValueError,"TRAIN_FIT_IS_NOT_OPTIMAL"):check(d)
    def test_nonfinite_matrix(self):
        d=fixture();d["calibration_rest_landmark_results"]["five_landmark_rest_similarity"]["matrix_source_world_to_native_world_colmajor"][0]=math.nan
        with self.assertRaisesRegex(ValueError,"SIM3_MATRIX"):check(d)
    def test_missing_native_frame(self):
        d=fixture();d["retarget_models"][0]["actual_native_blender_frames"]=143
        with self.assertRaisesRegex(ValueError,"FAKE_SOURCE_CONTACT"):check(d)
    def test_forge_nonswing(self):
        d=fixture();d["retarget_models"][0]["real_native_foot_material"]["L"]["source_nonswing_is_not_force_verified"]=False
        with self.assertRaisesRegex(ValueError,"FALSE_SOLE"):check(d)
    def test_forge_stance(self):
        d=fixture();d["retarget_models"][1]["physical_contact_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FAKE_SOURCE_CONTACT"):check(d)
    def test_missing_side(self):
        d=fixture();d["retarget_models"][0]["real_native_foot_material"].pop("R")
        with self.assertRaisesRegex(ValueError,"NO_INDEPENDENT_BILATERAL"):check(d)
    def test_bad_toe(self):
        d=fixture();d["retarget_models"][0]["world_ankle_and_toe_delta_errors"]["LeftToe"]["p50_m"]=-.1
        with self.assertRaisesRegex(ValueError,"INVALID_SOURCE"):check(d)
    def test_no_height_stance_is_unknown(self):
        d=fixture();d["retarget_models"][0]["real_native_foot_material"]["L"]["near_self_low_p50_xy_speed_mps"]=None
        self.assertEqual(check(d),"HOLD")
if __name__=="__main__":unittest.main()
