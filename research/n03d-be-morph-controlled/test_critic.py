"""Adversarial morphology-matched official MPFB source and contact controls."""
import copy,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import check
def example():
    r={"schema":"scp.n03d-be.exact-identical-morph-53-163-v1",
       "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
       "actor":"AsterOriginal","mpfb_official_commit":"9de0707fdc88438d7c53a1a2ac7937d9221e2431",
       "source_100style_git_blob":"a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
       "source_100style_sha256":"a"*64,"source_360_frame_clock_hz":60,
       "same_morphology_before_rig":True,"exact_source_body_mesh_sha256":"b"*64,
       "same_body_vertex_count":19158,
       "underlying_core_mesh_sha256":"f"*64,
       "actual_evaluated_macro_shape":{"sha256":"b"*64,"vertices":19158},
       "shape_key_profile_fingerprint":{"shape_key_weight_sha256":"c"*64,
           "active_shape_key_count":37,"all_shape_key_count":88},
       "evaluated_morphology_matched_before_rigging":True,
       "post_rig_shape_equivalence_not_assumed":True,
       "post_rig_evaluated_shape_per_rig":{"default":{"sha256":"d"*64,"vertices":19158},
                                         "game_engine":{"sha256":"e"*64,"vertices":19158}},
       "post_rig_shape_drift_per_rig":{"default":{"max_world_centered_vertex_displacement_m":.01,
           "rms_world_centered_vertex_displacement_m":.001,
           "pre_and_post_evaluated_shape_identical":False},
           "game_engine":{"max_world_centered_vertex_displacement_m":.02,
           "rms_world_centered_vertex_displacement_m":.005,
           "pre_and_post_evaluated_shape_identical":False}},
       "actual_material_scope":"SOURCE_BODY_ARMATURE_ONLY_FIXED_VERTEX_IDS_NOT_RENDER_MASK",
       "non_armature_display_modifiers_excluded":{"default":[{"name":"TopologyMask","type":"MASK"}],"game_engine":[{"name":"TopologyMask","type":"MASK"}]},
       "named_rig_joint_head_differences_m":{s+n:0.01 for s in ("Left","Right")
                                    for n in ("Hip","Knee","Ankle","Toe")},
       "shoe_heels_or_toe_force_verified":False,"true_floor_known":False,
       "body_anatomical_joint_centers_proven":False,"independent_multi_camera_visual_pass":False,
       "actor_production_identity_accepted":False,"mvp_accepted":False}
    m={"samples_60hz":360,"minimum_skin_z_m":-.05,
       "maximum_skin_z_m":.08,"relative_min_reference_Z_m":-.05,
       "p50_fullclip_stable_material_xy_speed_mps":.4,
       "max_fullclip_stable_material_xy_speed_mps":1.9,
       "source_ground_is_known":False,"true_force_contact_measured":False}
    r["results"]=[{"rig":rig,"mode":mode,"bone_count":163 if rig=="default" else 53,
                  "original_body_SHA256":"b"*64,"n_real_60hz_frames":360,
                  "source_frame_interval":[120,479],"own_low_height_reference_not_authenticated_ground":True,
                  "gait_contact_accepted":False,"leg_scale_ratio":1.0,
                  "skin_vertex_cohorts":{"L":55,"R":55},
                  "actual_material":{"L":m.copy(),"R":m.copy()}}
                  for rig in ("default","game_engine")
                  for mode in ("direct_canonical","rest_frame_conjugated")]
    return r
class Critical(unittest.TestCase):
    def test_narrow_success(self):self.assertEqual(check(example()),"HOLD")
    def test_false_morph(self):
        d=example();d["same_morphology_before_rig"]=False
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_PHYSICAL"):check(d)
    def test_false_force(self):
        d=example();d["shoe_heels_or_toe_force_verified"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_PHYSICAL"):check(d)
    def test_private(self):
        d=example();d["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_PHYSICAL"):check(d)
    def test_morph_sha_drift(self):
        d=example();d["results"][0]["original_body_SHA256"]="0"*64
        with self.assertRaisesRegex(ValueError,"SOURCE_NATIVE_FACTOR_MISMATCH"):check(d)
    def test_unmatched_clock(self):
        d=example();d["results"][0]["n_real_60hz_frames"]=143
        with self.assertRaisesRegex(ValueError,"SOURCE_NATIVE_FACTOR_MISMATCH"):check(d)
    def test_missing_rig(self):
        d=example();d["results"].pop()
        with self.assertRaisesRegex(ValueError,"FACTORS_NOT_COMPLETE"):check(d)
    def test_forged_ground(self):
        d=example();d["results"][0]["actual_material"]["L"]["source_ground_is_known"]=True
        with self.assertRaisesRegex(ValueError,"FORGED_MATERIAL_GROUND"):check(d)
    def test_no_stance_not_zero(self):
        d=example();d["results"][0]["actual_material"]["L"]["candidate_near_low_adjacent_pairs"]=0
        self.assertEqual(check(d),"HOLD")
    def test_nonfinite(self):
        d=example();d["results"][1]["actual_material"]["R"]["minimum_skin_z_m"]=math.nan
        with self.assertRaisesRegex(ValueError,"NONFINITE_NATIVE_MATERIAL"):check(d)
    def test_rig_count(self):
        d=example();d["results"][0]["bone_count"]=161
        with self.assertRaisesRegex(ValueError,"SOURCE_NATIVE_FACTOR_MISMATCH"):check(d)
    def test_falsified_evaluated_shape(self):
        d=example();d["actual_evaluated_macro_shape"]["sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"UNEVALUATED_SOURCE_MORPHOLOGY_NOT_AUTHORITY"):check(d)
    def test_shape_key_absent(self):
        d=example();d["shape_key_profile_fingerprint"]["active_shape_key_count"]=0
        with self.assertRaisesRegex(ValueError,"UNEVALUATED_SOURCE_MORPHOLOGY_NOT_AUTHORITY"):check(d)
    def test_refit_drift_forged(self):
        d=example();d["post_rig_shape_drift_per_rig"]["default"]["pre_and_post_evaluated_shape_identical"]=True
        with self.assertRaisesRegex(ValueError,"FALSE_POST_RIG_REFIT_EQUIVALENCE"):check(d)
    def test_missing_drift_receipts(self):
        d=example();d["post_rig_shape_drift_per_rig"].pop("game_engine")
        with self.assertRaisesRegex(ValueError,"MISSING_POST_RIG_SHAPE_RECEIPTS"):check(d)
    def test_false_render_mask(self):
        d=example();d["actual_material_scope"]="FULL_RENDERED_CLOTHES"
        with self.assertRaisesRegex(ValueError,"UNDECLARED_SOURCE_MESH_MODIFIER_PROJECTION"):check(d)
    def test_missing_modifier_receipt(self):
        d=example();d["non_armature_display_modifiers_excluded"]={}
        with self.assertRaisesRegex(ValueError,"UNTRACEABLE_MASK_MODIFIER_EXCLUSIONS"):check(d)
    def test_gait_promotion(self):
        d=example();d["results"][0]["gait_contact_accepted"]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_NATIVE_FACTOR_MISMATCH"):check(d)
if __name__=="__main__":unittest.main()
