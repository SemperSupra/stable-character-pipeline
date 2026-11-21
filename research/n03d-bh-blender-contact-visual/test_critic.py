"""BH hostile publication, sole-forgery and sampling controls."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import check,SHA
def fixture():
    x={"schema":"scp.n03d-bh.original-mpfb-multi-view-contact-proxy.v1",
       "actor":"AsterOriginal","rig":"game_engine",
       "public_original_substitute_only":True,
       "mpfb_official_source_commit":"9de0707fdc88438d7c53a1a2ac7937d9221e2431",
       "motion_git_blob":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
       "source_60hz_frames":[120,479],
       "body_actual_evaluated_shape_sha256":SHA["AsterOriginal"],
       "real_blender_5_2_4_version":[5,2,4],
       "reference_cameras_are_static_per_view":True,
       "characters_wear_real_CC0_shoes":False,
       "true_anatomical_heel_ball_semantics_calibrated":False,
       "real_force_grf":False,"floor_contact_verified":False,
       "independent_critics_approved_realism":False,
       "protected_actors_or_likeness_used":False,"mvp_accepted":False,
       "status":"PASS_NARROW_NATIVE_HEEL_BALL_PROXY_AND_REAL_RASTER_HOLD_REALISM"}
    m={"samples_60hz":360,"native_body_region_not_worn_shoe":True,
       "foot_material_fixed_ids":True,"global_min_z_m":-.04,
       "global_max_z_m":.08,"fullclip_p50_xy_speed_mps":.5,
       "near_own_low_adjacent_pairs":12,"near_own_low_p50_xy_speed_mps":.2,
       "actual_force_support_ground_verified":False}
    x["material_results"]={s:{"heel_region":m.copy(),"ball_region":m.copy(),
       "ball_minus_heel_height_p50_m":.01,"ball_minus_heel_height_min_m":-.04,
       "ball_minus_heel_height_max_m":.05,
       "true_heel_ball_anatomical_joints_corroborated":False} for s in ("L","R")}
    x["fixed_heel_ball_body_vertex_region_receipts"]={
        s:{"n_heel":15,"n_ball":15,"source_weighted_total":400,
           "rest_axis":[0.1,.99,0.]} for s in ("L","R")}
    x["genuine_blender_workbench_original_source_stills"]=[
        {"view":v,"source_index_60hz":i,"relative_seconds":round(i/60,6),
         "png":f"AsterOriginal_game_engine_{v}_{i:03d}.png",
         "png_sha256":f"{v[:1]}{i:03d}".ljust(64,"x"),
         "bytes":5000,"body_source_only_CC0_not_photo":True}
         for v in ("front","profile") for i in (0,180,359)]
    return x
class Tests(unittest.TestCase):
    def test_narrow(self):self.assertEqual(check(fixture()),"HOLD")
    def test_fake_shoe(self):
        r=fixture();r["characters_wear_real_CC0_shoes"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_PROTECTED"):check(r)
    def test_fake_mvp(self):
        r=fixture();r["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_PROTECTED"):check(r)
    def test_fake_true_floor(self):
        r=fixture();r["floor_contact_verified"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_PROTECTED"):check(r)
    def test_bad_body(self):
        r=fixture();r["body_actual_evaluated_shape_sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"SOURCE_MORPHOLOGY"):check(r)
    def test_unknown_visual(self):
        r=fixture();r["genuine_blender_workbench_original_source_stills"].pop()
        with self.assertRaisesRegex(ValueError,"NO_TRUE_TWO_CAMERA"):check(r)
    def test_forged_raster_all_equal(self):
        r=fixture()
        for im in r["genuine_blender_workbench_original_source_stills"]:im["png_sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"SOURCE_SAFE_RASTER"):check(r)
    def test_no_heel(self):
        r=fixture();r["fixed_heel_ball_body_vertex_region_receipts"]["L"]["n_heel"]=0
        with self.assertRaisesRegex(ValueError,"ORIGINAL_HEEL_BALL"):check(r)
    def test_fake_force(self):
        r=fixture();r["material_results"]["L"]["ball_region"]["actual_force_support_ground_verified"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_SHOE_OR_TIMELINE"):check(r)
    def test_missing_native(self):
        r=fixture();r["material_results"]["R"]["heel_region"]["samples_60hz"]=60
        with self.assertRaisesRegex(ValueError,"FALSE_SHOE_OR_TIMELINE"):check(r)
    def test_nonfinite(self):
        r=fixture();r["material_results"]["L"]["heel_region"]["global_max_z_m"]=math.nan
        with self.assertRaisesRegex(ValueError,"INVALID_NATIVE_MATERIAL"):check(r)
    def test_heel_ball_separation_inverted(self):
        r=fixture();r["material_results"]["R"]["ball_minus_heel_height_p50_m"]=.9
        with self.assertRaisesRegex(ValueError,"BAD_HEEL_ROLLOVER"):check(r)
    def test_no_low_support_is_unknown(self):
        r=fixture();r["material_results"]["L"]["ball_region"]["near_own_low_adjacent_pairs"]=0
        r["material_results"]["L"]["ball_region"]["near_own_low_p50_xy_speed_mps"]=None
        self.assertEqual(check(r),"HOLD")
if __name__=="__main__":unittest.main()
