"""BF hostile original source rights and true-shoe no-contact/unknown controls."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import assess
def fixture():
    actors=[{"name":a,"default_bones":163,"game_engine_bones":53,
             "body_rest_vertex_delta":{"count":19000,
                "max_rest_vertex_deviation_m":0.0,"same_morphology_max_1mm":True}}
            for a in ("AsterOriginal","JuniperOriginal")]
    source={f"{a}:{r}":{"garment":"toigo_stiletto_booties" if a=="AsterOriginal" else "toigo_ballet_flats",
           "shoe_total_vertices":600,"actual_skin":True}
            for a in ("AsterOriginal","JuniperOriginal")
            for r in ("default","game_engine")}
    trials=[]
    for a in actors:
        for r in ("default","game_engine"):
            for mode in ("direct_canonical","rest_frame_conjugated"):
                info={s:{"weighted_shoe_vertices":240,"persistent_low_vertices":48,
                         "heel_proxy_vertices":16,"toe_proxy_vertices":16,
                         "actual_anatomical_sole_heel_toe_verified":False,
                         "side_assigned_from_real_source_skin_weights":True} for s in ("L","R")}
                material={s:{region:{"samples_60hz":360,"min_native_mesh_z_m":-.07,
                  "max_native_mesh_z_m":.11,
                  "max_reference_penetration_known":False,
                  "fullclip_p50_persistent_material_xy_speed_mps":.2,
                  "fullclip_max_persistent_material_xy_speed_mps":1.4,
                  "low_relative_adjacent_pairs":0,
                  "low_relative_p50_persistent_material_xy_speed_mps":None,
                  "sole_labeled_anatomically":False,"physical_contact_accepted":False}
                    for region in ("heel_proxy","toe_proxy","full_low_cohort")}
                    for s in ("L","R")}
                trials.append({"actor":a["name"],"rig":r,"mode":mode,
                    "source_frames":[120,479],"native_source_fps":60,
                    "source_body_shape_max_delta_m":0.0,
                    "rig_bones":163 if r=="default" else 53,
                    "actual_mesh_source_asset":source[f'{a["name"]}:{r}']["garment"],
                    "actual_original_CC0_shoe_skinned":True,
                    "original_rig_rest_toe_proxy":info,
                    "native_60hz_shoe_material":material,
                    "ground_contact_true":False,"anatomical_sole_verified":False,
                    "visual_accepted":False,"physical_gait_accepted":False})
    return {"schema":"scp.n03d-bf.identical-morphology-real-cc0-worn-footwear.v1",
        "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
        "MPFB_upstream_commit":"9de0707fdc88438d7c53a1a2ac7937d9221e2431",
        "source_original_100style_blob":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
        "original_cc0_shoe_pack_sha256":"ded3f70428505eabbf1f6d7b5f61196a7366ef20757103d276ad0ed336c35ada",
        "official_Blender_version":[5,2,4],
        "source_original_rate_hz":60,"source_frames":[120,479],
        "true_skin_model_actors":actors,
        "actual_shoe_sources":source,
        "source_body_cloth_or_shoe_saved":False,
        "raw_100style_media_published":False,
        "true_contact_force_measured":False,
        "true_anatomical_heel_toe_verified":False,
        "source_floor_measured":False,"independent_visual_accepted":False,
        "physical_gait_accepted":False,"mvp_accepted":False,
        "status":"HOLD_PHYSICAL_CONTACT_AND_VISUAL",
        "actual_native_360x60hz_trials":trials}
class Controls(unittest.TestCase):
    def test_real_shoe_fixture_hold(self):
        x=assess(fixture())
        self.assertEqual(x["status"],"HOLD_PHYSICAL_AND_VISUAL")
        self.assertEqual(len(x["trials"]),8)
    def test_no_heel_toe_verification(self):
        x=fixture();x["true_anatomical_heel_toe_verified"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_FORGED_RELEASE"):assess(x)
    def test_source_motion_hard_pin(self):
        x=fixture();x["source_original_100style_blob"]="0"*40
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_FORGED_RELEASE"):assess(x)
    def test_no_project_mvp(self):
        x=fixture();x["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_FORGED_RELEASE"):assess(x)
    def test_wrong_real_shoe_pack(self):
        x=fixture();x["original_cc0_shoe_pack_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_FORGED_RELEASE"):assess(x)
    def test_no_raw_blend_public(self):
        x=fixture();x["source_body_cloth_or_shoe_saved"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_OR_FORGED_RELEASE"):assess(x)
    def test_no_unverified_side(self):
        x=fixture();x["actual_native_360x60hz_trials"][0]["original_rig_rest_toe_proxy"]["L"]["side_assigned_from_real_source_skin_weights"]=False
        with self.assertRaisesRegex(ValueError,"FALSE_TOE_AUTHORITY"):assess(x)
    def test_fake_footwear(self):
        x=fixture();x["actual_shoe_sources"]["AsterOriginal:default"]["actual_skin"]=False
        with self.assertRaisesRegex(ValueError,"NO_REAL_SKINNED_CC0_SHOE"):assess(x)
    def test_fake_planted(self):
        x=fixture();x["actual_native_360x60hz_trials"][0]["native_60hz_shoe_material"]["L"]["heel_proxy"]["physical_contact_accepted"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_PLANTED_GROUND_ACCEPTANCE"):assess(x)
    def test_nonsensical_zero_contact_is_unknown(self):
        x=fixture();self.assertEqual(assess(x)["status"],"HOLD_PHYSICAL_AND_VISUAL")
    def test_wrong_timebase(self):
        x=fixture();x["actual_native_360x60hz_trials"][0]["native_source_fps"]=24
        with self.assertRaisesRegex(ValueError,"FALSE_MATERIAL_OR_NATIVE_ADMISSION"):assess(x)
    def test_nonfinite(self):
        x=fixture();x["actual_native_360x60hz_trials"][0]["native_60hz_shoe_material"]["L"]["toe_proxy"]["min_native_mesh_z_m"]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE_MATERIAL"):assess(x)
if __name__=="__main__":unittest.main()
