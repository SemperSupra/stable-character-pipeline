"""BI independent source, actual CC0 weighted shoe, 356 source-domain 60Hz critic."""
import math
ACTORS={"AsterOriginal","JuniperOriginal"}
SRC="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
def need(ok,why):
    if not ok:raise ValueError(why)
def finite(value):
    need(type(value) in (int,float) and math.isfinite(value) and abs(value)<10000,
         "NATIVE_SHOE_NONFINITE")
def check(doc):
    need(doc.get("schema")=="scp.n03d-bi.actual-cc0-shoe-60hz-fixed-heel-ball.v1" and
         doc.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         doc.get("original_100style_motion_git_blob")==SRC and
         doc.get("source_original_action_clock_hz")==12 and
         doc.get("actual_blender_subframe_clock_hz")==60 and
         doc.get("source_original_60hz_frame_window")==[120,479] and
         doc.get("native_60hz_source_supported_samples")==356 and
         doc.get("native_retarged_action_last_keyframe")==71 and
         doc.get("excluded_unbacked_source_60hz_tail_frames")==[356,357,358,359] and
         doc.get("native_blender_version")==[5,2,4] and
         doc.get("registered_original_CC0_shoes") is True and
         doc.get("original_ground_plane_zero_authenticated") is True and
         doc.get("anatomical_plantar_force_measured") is False and
         doc.get("true_contact_stance_accepted") is False and
         doc.get("protected_likeness_used") is False and
         doc.get("independent_visual_reality_accepted") is False and
         doc.get("mvp_accepted") is False and
         doc.get("status")=="PASS_NARROW_ACTUAL_CC0_SHOE_PATCH_60HZ_HOLD_TRUE_CONTACT",
         "SOURCE_CLOCK_OR_FALSE_PHYSICAL_MVP_PROMOTION")
    need(len(doc.get("original_source_retarget_scene_sha256",""))==64,
         "ORIGINAL_SCENE_SHA_MISSING")
    people=doc.get("actors")
    need(isinstance(people,list) and len(people)==2 and
         {p.get("actor") for p in people}==ACTORS,
         "NOT_TWO_SOURCE_SAFE_ACTORS")
    for a in people:
        need(a.get("source_shoe_asset") and a.get("genuine_cc0_shoe_name") and
             type(a.get("mesh_vertex_count"))==int and a["mesh_vertex_count"]>=600 and
             len(a.get("sampled_five_shoe_material_sha256",[]))==5 and
             len(set(a["sampled_five_shoe_material_sha256"]))>=4 and
             all(isinstance(h,str) and len(h)==64 for h in a["sampled_five_shoe_material_sha256"]),
             "NO_ACTUAL_MOVING_CC0_SHOE")
        patches=a.get("source_actual_deformed_shoe_patches",{})
        regions=a.get("persistent_source_rest_foot_regions",{})
        need(set(patches)=={"L","R"} and set(regions)=={"L","R"},
             "NO_BILATERAL_RIG_SHOE")
        source_sides=set()
        for side in ("L","R"):
            patch=patches[side];reg=regions[side]
            weights=patch.get("source_cc0_shoe_skin_named_side")
            need(weights.get("label")==side and
                 .85<=weights.get("rig_weight_dominance",0)<=1.0,
                 "ACTUAL_CC0_SHOE_SIDE_WEIGHT_NOT_QUALIFIED")
            source_sides.add(patch.get("source_local_rest_partition"))
            need(len(reg.get("shoe_heel_ids_sha256",""))==64 and
                 len(reg.get("shoe_ball_ids_sha256",""))==64 and
                 reg["shoe_heel_ids_sha256"]!=reg["shoe_ball_ids_sha256"] and
                 reg.get("n_heel",0)>=8 and reg.get("n_ball",0)>=8 and
                 reg.get("source_partition_vertices",0)>=80 and
                 reg.get("foot_tip_anatomical_or_pressure_verified") is False,
                 "SHOE_SOURCE_FIXED_HEEL_BALL_UNVERIFIED")
            need(patch.get("shoe_surface_plant_force_proven") is False,
                 "FAKE_SHOE_PLANT_FORCE")
            for k in ("persistent_heel_region","persistent_ball_region"):
                val=patch[k]
                need(val.get("source_samples_60hz")==356 and
                     val.get("actual_fixed_source_shoe_vertex_ids")==reg[
                         "n_heel" if k=="persistent_heel_region" else "n_ball"] and
                     val.get("real_flat_park_ground_plane_z_m")==0. and
                     val.get("anatomical_foot_contact_or_force_accepted") is False,
                     "SOURCE_GROUND_OR_SHOE_MATERIAL_NOT_NATIVE")
                for z in ("min_world_shoe_z_m","max_world_shoe_z_m",
                          "max_penetration_below_actual_ground_m",
                          "median_fullclip_shoe_region_xy_speed_mps"):finite(val[z])
                need(val["max_world_shoe_z_m"]>=val["min_world_shoe_z_m"] and
                     val["max_penetration_below_actual_ground_m"]>=0 and
                     val["median_fullclip_shoe_region_xy_speed_mps"]>=0 and
                     val.get("near_flat_plane_pairs_threshold_12mm") in range(356),
                     "SHOE_CONTACT_GEOMETRY_OUT_OF_RANGE")
                if val.get("median_near_plane_speed_mps") is not None:
                    finite(val["median_near_plane_speed_mps"])
            for z in ("toe_minus_heel_height_min_m","toe_minus_heel_height_max_m",
                      "toe_minus_heel_height_p50_m"):finite(patch[z])
            need(patch["toe_minus_heel_height_min_m"]<=patch[
                 "toe_minus_heel_height_p50_m"]<=patch["toe_minus_heel_height_max_m"],
                 "PHYSICAL_SHOE_PITCH_MATH")
        need(source_sides=={"rest_local_x_negative","rest_local_x_positive"},
             "SOURCE_REST_LOCAL_PARTITIONS_DUPLICATED")
    return "HOLD"
