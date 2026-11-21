"""BJ sceptical synthetic source/target data fixture; real native source remains separate."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import check,MORPH,TRAIN,TEST
def fixture():
    d={"schema":"scp.n03d-bj.same-morph-source-fk-to-blender-world-joints.v1",
       "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0","actor":"AsterOriginal",
       "original_100style_source_git_blob":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
       "original_100style_source_sha256":"b"*64,
       "source_100style_frame_window":[120,479],"true_source_100style_clock_hz":60,
       "official_mpfb_source_commit":"9de0707fdc88438d7c53a1a2ac7937d9221e2431",
       "source_no_ground_reaction_force_available":True,
       "source_first_frame_is_walk_not_neutral_rest":True,
       "fitted_holdout_used_in_training":False,
       "true_anatomical_side_or_sole_accepted":False,
       "photo_or_identity_protected_used":False,"mvp_accepted":False,
       "status":"PASS_NARROW_MORPH_MATCHED_60HZ_SOURCE_NATIVE_TRAJECTORY_HOLD_GAIT"}
    d["source_world_fk"]={k:{"speed_p50_mps":.5,"speed_p95_mps":2.0,
                             "total_displacement_m":2.} for k in TRAIN|TEST}
    d["rigs"]=[]
    for rig,count in (("default",163),("game_engine",53)):
        modes=[]
        for mode in ("direct_canonical","rest_frame_conjugated"):
            for root_method in ("legacy_fixed_axis_root","five_landmark_sim3_root"):
                modes.append({"rig":rig,"mode":mode,"root_method":root_method,
             "actual_native_60hz_frames":360,
             "source_fk_motion_world_samples":360,"actual_deformed_skin_verified":True,
             "native_real_body_local_shape_sha_samples":[str(i).zfill(64) for i in (0,80,160,240,359)],
             "true_ground_or_force_proven":False,"mvp_accepted":False,
             "source_fk_to_native_dynamic_residuals":{k:{
               "p50_dynamic_displacement_error_m":.1,"p95_dynamic_displacement_error_m":.3,
               "max_dynamic_displacement_error_m":.6,"target_world_step_speed_p50_mps":.5}
               for k in TRAIN|TEST}})
        d["rigs"].append({"rig":rig,"bone_count":count,
          "actual_same_source_evaluated_shape_sha256":MORPH[d["actor"]],
          "actual_native_source_pre_rig_shape_vertices":19158,
          "first_recorded_walk_pose_used_not_source_tpose":True,
          "source_mocap_vs_target_rest_calibration_fit_scale":1.1,
          "five_training_joints":sorted(TRAIN),"four_heldout_joints":sorted(TEST),
          "source_to_native_walkfirst_rest_alignment_errors_m":{k:.05 for k in TRAIN|TEST},
          "modes":modes})
    return d
class Controls(unittest.TestCase):
    def test_narrow(self):self.assertEqual(check(fixture()),"HOLD")
    def alter(self,path,value,err):
        d=fixture();path(d,value)
        with self.assertRaisesRegex(ValueError,err):check(d)
    def test_no_protected(self):self.alter(lambda d,v:d.update(photo_or_identity_protected_used=v),True,"FALSE_SOURCE")
    def test_no_accept(self):self.alter(lambda d,v:d.update(mvp_accepted=v),True,"FALSE_SOURCE")
    def test_force(self):self.alter(lambda d,v:d.update(source_no_ground_reaction_force_available=v),False,"FALSE_SOURCE")
    def test_heldout_fit(self):self.alter(lambda d,v:d.update(fitted_holdout_used_in_training=v),True,"FALSE_SOURCE")
    def test_not_tpose(self):self.alter(lambda d,v:d.update(source_first_frame_is_walk_not_neutral_rest=v),False,"FALSE_SOURCE")
    def test_wrong_source(self):self.alter(lambda d,v:d.update(original_100style_source_git_blob=v),"x"*40,"FALSE_SOURCE")
    def test_wrong_person(self):self.alter(lambda d,v:d.update(actor=v),"Naomi","FALSE_SOURCE")
    def test_changed_shape(self):self.alter(lambda d,v:d["rigs"][1].update(actual_same_source_evaluated_shape_sha256=v),"f"*64,"SOURCE_MORPHOLOGY")
    def test_wrong_bones(self):self.alter(lambda d,v:d["rigs"][1].update(bone_count=v),163,"SOURCE_MORPHOLOGY")
    def test_heldout_leak(self):self.alter(lambda d,v:d["rigs"][1]["five_training_joints"].append(v),"LeftAnkle","SOURCE_MORPHOLOGY")
    def test_fake_360(self):self.alter(lambda d,v:d["rigs"][0]["modes"][1].update(actual_native_60hz_frames=v),72,"SOURCE_NATIVE_60HZ")
    def test_missed_pose(self):self.alter(lambda d,v:d["rigs"][0]["modes"][1].update(native_real_body_local_shape_sha_samples=v),["a"*64]*5,"FALSE_RIGID_ROOT")
    def test_sim3_root_factor_missing(self):
        self.alter(lambda d,v:d["rigs"][0]["modes"][0].update(root_method=v),
                   "five_landmark_sim3_root","NATIVE_POSE_VS_PROPER_SIM3_ROOT")
    def test_nonfinite(self):self.alter(lambda d,v:d["rigs"][0]["modes"][0]["source_fk_to_native_dynamic_residuals"]["LeftAnkle"].update(max_dynamic_displacement_error_m=v),math.nan,"INVALID_SOURCE")
    def test_order(self):self.alter(lambda d,v:d["rigs"][0]["modes"][0]["source_fk_to_native_dynamic_residuals"]["LeftToe"].update(p50_dynamic_displacement_error_m=v),1.,"SOURCE_TRAJECTORY")
if __name__=="__main__":unittest.main()
