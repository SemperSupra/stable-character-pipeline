"""BD native 60Hz source-sha, bilateral material, false floor and force critic controls."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import assess
def fixture():
    a={"schema":"scp.n03d-bd.same-100style-rig-matched-native.v1",
       "candidate":"vsim","target_native_rig_bones":53,
       "source_class":"PUBLIC_SOURCE_RIGHTS_RESEARCH_ONLY",
       "source_same_360_frames_for_all_candidates":True,
       "source_mocap_ground_force_proven":False,
       "source_rights_paid_or_protected":False,
       "true_anatomical_correspondence_accepted":False,
       "original_motion_file_published":False,
       "actual_blender_skin_actuated":True,
       "physical_gait_accepted":False,"mvp_accepted":False,
       "original_100style_blob":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
       "source_commit":"10938b4881b55c5801faded89e427407ddf14bce",
       "source_sha256":"a"*64,"model_sha256":"b"*64}
    tr=[]
    for mode in ("direct_canonical","rest_frame_conjugated"):
        tr.append({"mode":mode,"source_frames":[120,479],"source_fps":60,
           "native_actually_evaluated_skinned_60hz_samples_per_foot":360,
           "source_floor_calibrated":False,"output_reference_is_own_lowest_skin_sample":True,
           "actual_skin_cohorts":{"L":25,"R":30},
           "rig_foot_measures":{s:{"samples_60hz":360,
             "minimum_skin_z_m":-.05,"maximum_skin_z_m":.09,
             "relative_min_reference_Z_m":-.05,
             "candidate_near_low_adjacent_pairs":11,
             "p50_fullclip_stable_material_xy_speed_mps":.3,
             "max_fullclip_stable_material_xy_speed_mps":1.9,
             "source_ground_is_known":False,"true_force_contact_measured":False}
             for s in ("L","R")}})
    a["trials"]=tr;return a
class BD(unittest.TestCase):
    def test_hold(self):self.assertEqual(assess(fixture()),"HOLD")
    def test_gait_forged(self):
        a=fixture();a["physical_gait_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SPOOFED_PROVENANCE_OR_GAIT_ACCEPTANCE"):assess(a)
    def test_true_force_forged(self):
        a=fixture();a["source_mocap_ground_force_proven"]=True
        with self.assertRaisesRegex(ValueError,"SPOOFED_PROVENANCE_OR_GAIT_ACCEPTANCE"):assess(a)
    def test_bad_source(self):
        a=fixture();a["original_100style_blob"]="b"*40
        with self.assertRaisesRegex(ValueError,"SRC_SHA_OR_COMMIT"):assess(a)
    def test_wrong_clock(self):
        a=fixture();a["trials"][1]["source_frames"]=[120,480]
        with self.assertRaisesRegex(ValueError,"FALSE_SOURCE_FLOOR_OR_CLOCK"):assess(a)
    def test_missing_skin(self):
        a=fixture();a["trials"][0]["actual_skin_cohorts"]["L"]=0
        with self.assertRaisesRegex(ValueError,"NO_NATIVE_SKIN_PARTITION"):assess(a)
    def test_alias_rig_allowed(self):
        a=fixture();a["candidate"]="rigify";a["target_native_rig_bones"]=161
        self.assertEqual(assess(a),"HOLD")
    def test_no_contact_episode_not_success(self):
        a=fixture();a["trials"][0]["rig_foot_measures"]["L"]["candidate_near_low_adjacent_pairs"]=0
        self.assertEqual(assess(a),"HOLD")
    def test_forged_true_floor(self):
        a=fixture();a["trials"][0]["source_floor_calibrated"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_SOURCE_FLOOR_OR_CLOCK"):assess(a)
    def test_nonfinite_rejected(self):
        a=fixture();a["trials"][0]["rig_foot_measures"]["R"]["minimum_skin_z_m"]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE"):assess(a)
    def test_mvp_false_promotion(self):
        a=fixture();a["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SPOOFED_PROVENANCE_OR_GAIT_ACCEPTANCE"):assess(a)
if __name__=="__main__":unittest.main()
