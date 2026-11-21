"""BE hypothetical controls must never self-authorize same morphology or foot contact."""
import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import assess
def fixture():
    people=[{"actor":a,"default_bones":163,"game_engine_bones":53,
             "rest_body_match":{"count":19000,"max_rest_vertex_deviation_m":0.0,
                                "p50_rest_vertex_deviation_m":0.0,"same_morphology_max_1mm":True}}
            for a in ("AsterOriginal","JuniperOriginal")]
    trials=[]
    for a in people:
        for rig in ("default","game_engine"):
            for mode in ("direct_canonical","rest_frame_conjugated"):
                foot={side:{"frames":360,"min_native_foot_body_z_m":-.05,
                            "max_native_foot_body_z_m":.1,
                            "p50_fullclip_stable_body_foot_xy_speed_mps":.4,
                            "max_fullclip_stable_body_foot_xy_speed_mps":1.9,
                            "candidate_low_relative_pairs":0,
                            "p50_low_relative_body_foot_xy_speed_mps":None,
                            "floor_calibrated":False,"ground_force_measured":False,
                            "real_shoe_mesh_measured":False} for side in ("L","R")}
                trials.append({"actor":a["actor"],"rig":rig,"mode":mode,
                               "bone_count":163 if rig=="default" else 53,
                               "source_frames":[120,479],"native_rate_hz":60,
                               "native_original_source_blender_pose_samples_per_side":360,
                               "matched_rest_shape_max_deviation_m":0.0,
                               "true_shoe_contact_accepted":False,
                               "fixed_native_body_material_foot_witness":foot})
    return {"schema":"scp.n03d-be.identical-phenotype-two-official-MPF-rigs.v1",
            "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
            "MPFB_original_source_commit":"9de0707fdc88438d7c53a1a2ac7937d9221e2431",
            "source_motion_blob_sha1":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
            "source_frames":[120,479],"source_rate_hz":60,"official_blender_version":[5,2,4],
            "morphology_independently_measured":True,"shoe_asset_present":False,
            "source_floor_calibrated":False,"force_contact_verified":False,
            "physical_gait_accepted":False,"mvp_accepted":False,
            "status":"HOLD_PHYSICS_AND_SHOE_CONTACT","morphologies":people,
            "native_trials":trials}
class BE(unittest.TestCase):
    def test_fixture_narrow(self):
        a=assess(fixture())
        self.assertTrue(a["all_morphology_matched_to_1mm"])
        self.assertEqual(a["status"],"HOLD_PHYSICS_SHOES_VISUAL")
        self.assertEqual(len(a["trials"]),8)
    def test_no_morphology_false_pass(self):
        a=fixture()
        for item in a["morphologies"]:
            item["rest_body_match"]["max_rest_vertex_deviation_m"]=.003
            item["rest_body_match"]["same_morphology_max_1mm"]=False
        for t in a["native_trials"]:t["matched_rest_shape_max_deviation_m"]=.003
        result=assess(a);self.assertFalse(result["all_morphology_matched_to_1mm"])
    def test_forged_contact(self):
        a=fixture();a["force_contact_verified"]=True
        with self.assertRaisesRegex(ValueError,"PROVENANCE_OR_PHYSICS_PROMOTION"):assess(a)
    def test_fake_shoe(self):
        a=fixture();a["native_trials"][0]["fixed_native_body_material_foot_witness"]["L"]["real_shoe_mesh_measured"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_SHOE_OR_FORCE"):assess(a)
    def test_missing_trial(self):
        a=fixture();a["native_trials"].pop()
        with self.assertRaisesRegex(ValueError,"MISSING_ACTUAL_NATIVE_COMPARISON"):assess(a)
    def test_wrong_clock(self):
        a=fixture();a["native_trials"][0]["native_rate_hz"]=24
        with self.assertRaisesRegex(ValueError,"RIG_POSE_OR_CONTACT"):assess(a)
    def test_wrong_bones(self):
        a=fixture();a["morphologies"][0]["game_engine_bones"]=47
        with self.assertRaisesRegex(ValueError,"NOT_163_VS_53_REAL_MORPHOLOGY"):assess(a)
    def test_witness_nonfinite(self):
        a=fixture();a["native_trials"][0]["fixed_native_body_material_foot_witness"]["R"]["min_native_foot_body_z_m"]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE"):assess(a)
    def test_wrong_source_blob(self):
        a=fixture();a["source_motion_blob_sha1"]="b"*40
        with self.assertRaisesRegex(ValueError,"PROVENANCE_OR_PHYSICS_PROMOTION"):assess(a)
    def test_fake_mvp(self):
        a=fixture();a["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"PROVENANCE_OR_PHYSICS_PROMOTION"):assess(a)
if __name__=="__main__":unittest.main()
