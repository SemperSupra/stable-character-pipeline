import copy, math, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from critic import check
def fixture():
    d=dict(schema="scp.n03d-bi.actual-cc0-shoe-60hz-fixed-heel-ball.v1",
        source_class="ORIGINAL_FICTIONAL_MPFBCORE_CC0",
        original_source_retarget_scene_sha256="f"*64,
        original_100style_motion_git_blob="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61",
        source_original_action_clock_hz=12, actual_blender_subframe_clock_hz=60,
        source_original_60hz_frame_window=[120,479],native_60hz_source_supported_samples=356,
        native_retarged_action_last_keyframe=71,
        excluded_unbacked_source_60hz_tail_frames=[356,357,358,359],
        native_blender_version=[5,2,4],registered_original_CC0_shoes=True,
        original_ground_plane_zero_authenticated=True,anatomical_plantar_force_measured=False,
        true_contact_stance_accepted=False,protected_likeness_used=False,
        independent_visual_reality_accepted=False,mvp_accepted=False,
        status="PASS_NARROW_ACTUAL_CC0_SHOE_PATCH_60HZ_HOLD_TRUE_CONTACT")
    metric=dict(source_samples_60hz=356,actual_fixed_source_shoe_vertex_ids=16,
        real_flat_park_ground_plane_z_m=0.,min_world_shoe_z_m=-.08,
        max_world_shoe_z_m=.3,max_penetration_below_actual_ground_m=.08,
        median_fullclip_shoe_region_xy_speed_mps=.95,
        near_flat_plane_pairs_threshold_12mm=50,median_near_plane_speed_mps=.23,
        anatomical_foot_contact_or_force_accepted=False)
    d["actors"]=[]
    for actor in ("AsterOriginal","JuniperOriginal"):
        patches={};regions={}
        for side,part in (("L","rest_local_x_positive"),("R","rest_local_x_negative")):
            patches[side]=dict(source_cc0_shoe_skin_named_side={
                "label":side,"rig_weight_dominance":.99},
                source_local_rest_partition=part,
                persistent_heel_region=metric.copy(),persistent_ball_region=metric.copy(),
                toe_minus_heel_height_min_m=-.09,toe_minus_heel_height_max_m=.12,
                toe_minus_heel_height_p50_m=.02,shoe_surface_plant_force_proven=False)
            regions[side]=dict(source_partition_vertices=300,shoe_heel_ids_sha256="a"*64,
                shoe_ball_ids_sha256="d"*64,n_heel=16,n_ball=16,
                foot_tip_anatomical_or_pressure_verified=False)
        d["actors"].append(dict(actor=actor,source_shoe_asset="CC0 Shoes",
            genuine_cc0_shoe_name="OriginalCC0",mesh_vertex_count=1200,
            sampled_five_shoe_material_sha256=[str(i).zfill(64) for i in (0,80,160,240,355)],
            persistent_source_rest_foot_regions=regions,
            source_actual_deformed_shoe_patches=patches))
    return d
class Controls(unittest.TestCase):
    def test_narrow(self):self.assertEqual(check(fixture()),"HOLD")
    def bad(self,mutate,pattern):
        d=fixture();mutate(d)
        with self.assertRaisesRegex(ValueError,pattern):check(d)
    def test_protected(self):self.bad(lambda x:x.update(protected_likeness_used=True),"SOURCE_CLOCK")
    def test_fake_mvp(self):self.bad(lambda x:x.update(mvp_accepted=True),"SOURCE_CLOCK")
    def test_false_360(self):self.bad(lambda x:x.update(native_60hz_source_supported_samples=360),"SOURCE_CLOCK")
    def test_false_tail(self):self.bad(lambda x:x.update(excluded_unbacked_source_60hz_tail_frames=[]),"SOURCE_CLOCK")
    def test_source(self):self.bad(lambda x:x.update(original_100style_motion_git_blob="0"*40),"SOURCE_CLOCK")
    def test_label(self):self.bad(lambda x:x["actors"][0]["source_actual_deformed_shoe_patches"]["L"]["source_cc0_shoe_skin_named_side"].update(label="R"),"ACTUAL_CC0")
    def test_weak_weights(self):self.bad(lambda x:x["actors"][0]["source_actual_deformed_shoe_patches"]["R"]["source_cc0_shoe_skin_named_side"].update(rig_weight_dominance=.51),"ACTUAL_CC0")
    def test_static(self):self.bad(lambda x:x["actors"][0].update(sampled_five_shoe_material_sha256=["b"*64]*5),"NO_ACTUAL")
    def test_force(self):self.bad(lambda x:x["actors"][1]["source_actual_deformed_shoe_patches"]["L"].update(shoe_surface_plant_force_proven=True),"FAKE_SHOE")
    def test_heel(self):self.bad(lambda x:x["actors"][0]["persistent_source_rest_foot_regions"]["L"].update(n_heel=0),"SHOE_SOURCE")
    def test_flat_ground(self):self.bad(lambda x:x["actors"][0]["source_actual_deformed_shoe_patches"]["R"]["persistent_ball_region"].update(real_flat_park_ground_plane_z_m=.08),"SOURCE_GROUND")
    def test_nonfinite(self):self.bad(lambda x:x["actors"][1]["source_actual_deformed_shoe_patches"]["L"]["persistent_heel_region"].update(min_world_shoe_z_m=math.nan),"NATIVE_SHOE")
    def test_none_contact(self):
        d=fixture();m=d["actors"][0]["source_actual_deformed_shoe_patches"]["R"]["persistent_heel_region"]
        m.update(near_flat_plane_pairs_threshold_12mm=0,median_near_plane_speed_mps=None)
        self.assertEqual(check(d),"HOLD")
if __name__=="__main__":unittest.main()
