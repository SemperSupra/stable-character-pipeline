"""BF crossruntime source & physical negative controls; independent of Three library."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import verify
def fixture():
    a={"schema":"scp.n03d-bf.live-three-controller-to-native-blender-skin.v1",
       "source_class":"ORIGINAL_PUBLIC_CC0_THREE_RUNTIME",
       "controller_repo_commit":"3f5b4896f1b28501b40aa9c408e47dba51322443",
       "motion_same_360frames_and_model":True,
       "source_100style_mocap_matched":False,
       "true_sole_and_anatomical_contact_proven":False,
       "source_measured_ground_force_proven":False,
       "independent_visual_accepted":False,"mvp_accepted":False,
       "rig":"rigify","native_rig_bones":161,
       "source_model_git_blob":"d3327b94c302278b5471c24d712ef5dc49f0d682",
       "source_model_sha256":"1"*64,"source_pose_trace_sha256":"2"*64,
       "native_leg_length_m":.8,"source_leg_length_m":.9,
       "actual_native_blender_skinned_meshes":3,
       "status":"PASS_NARROW_ACTUAL_CONTROLLER_TO_SKIN_REPLAY_HOLD_CONTACT"}
    mat={"source_frames":360,"foot_material_count":53,"local_low_m":-.04,
         "high_m":.07,"p50_all_foot_material_xy_speed_mps":.4,
         "p50_native_material_in_controller_declared_nonswing_mps":.3,
         "p50_material_near_own_low_height_mps":.2,
         "actual_sole_ground_and_force_contact_verified":False}
    mis={"coordinate_frame":"THREE_Y_UP_VS_BLENDER_Z_UP_CALIBRATED_BY_FIRST_FRAME_TRANSLATION_ONLY",
         "p50_joint_displacement_error_m":.03,"max_joint_displacement_error_m":.15}
    a["trials"]=[{"mode":mode,"native_60hz_frames":360,
                  "controller_source_phases_not_ground_truth":True,
                  "mvp_or_physical_contact_accepted":False,
                  "actual_skinned_material":{"L":mat.copy(),"R":mat.copy()},
                  "source_joint_displacement_errors":{"L":mis.copy(),"R":mis.copy()}}
                 for mode in ("direct_local_delta","bone_rest_conjugated_delta")]
    return a
class Controls(unittest.TestCase):
    def test_narrow(self):self.assertEqual(verify(fixture()),"HOLD")
    def test_true_ground_spoof(self):
        x=fixture();x["source_measured_ground_force_proven"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_PHYSICAL"):verify(x)
    def test_nonswing_not_source_force(self):
        x=fixture();x["trials"][0]["controller_source_phases_not_ground_truth"]=False
        with self.assertRaisesRegex(ValueError,"FAKE_SOURCE_CLOCK_OR_STANCE"):verify(x)
    def test_model_sha(self):
        x=fixture();x["source_model_git_blob"]="a"*40
        with self.assertRaisesRegex(ValueError,"ACTUAL_ORIGINAL_RIG"):verify(x)
    def test_missing_60hz(self):
        x=fixture();x["trials"][0]["native_60hz_frames"]=60
        with self.assertRaisesRegex(ValueError,"FAKE_SOURCE_CLOCK_OR_STANCE"):verify(x)
    def test_no_source_integrity(self):
        x=fixture();x["source_pose_trace_sha256"]="1"*6
        with self.assertRaisesRegex(ValueError,"ACTUAL_ORIGINAL_RIG"):verify(x)
    def test_false_sole(self):
        x=fixture();x["trials"][1]["actual_skinned_material"]["R"]["actual_sole_ground_and_force_contact_verified"]=True
        with self.assertRaisesRegex(ValueError,"NO_VALID_MATERIAL_OR_FAKE_CONTACT"):verify(x)
    def test_bad_frame_correspondence(self):
        x=fixture();x["trials"][1]["source_joint_displacement_errors"]["L"]["coordinate_frame"]="KNOWN_SOURCE_WORLD"
        with self.assertRaisesRegex(ValueError,"NO_TRUSTWORTHY_POSE_REFERENCE"):verify(x)
    def test_no_fit_is_not_pass(self):
        x=fixture();x["trials"][0]["actual_skinned_material"]["R"]["p50_material_near_own_low_height_mps"]=None
        self.assertEqual(verify(x),"HOLD")
    def test_fake_mvp(self):
        x=fixture();x["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_PHYSICAL"):verify(x)
    def test_nan(self):
        x=fixture();x["trials"][0]["actual_skinned_material"]["L"]["local_low_m"]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE_NUMERICAL_MEASURE"):verify(x)
    def test_original_named_rig(self):
        x=fixture();x["rig"]="named";x["native_rig_bones"]=65
        x["source_model_git_blob"]="2f86c50b2938f0f7d78df7ff9835864d6af0fd4a"
        self.assertEqual(verify(x),"HOLD")
if __name__=="__main__":unittest.main()
