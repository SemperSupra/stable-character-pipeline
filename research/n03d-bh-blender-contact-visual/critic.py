"""BH independent original MakeHuman 60Hz material and actual PNG critic."""
import math
PIN="9de0707fdc88438d7c53a1a2ac7937d9221e2431"
SHA={
 "AsterOriginal":"9156e167a19083500fc5323155166abd3daa2a93510bacb8beeb7de8c83c4a4b",
 "JuniperOriginal":"8dfa35c38f3df7cbff4601232d4a8b7dcc1d0ee74f34ead424c787cf638aa918"}
def need(x,msg):
    if not x:raise ValueError(msg)
def scalar(x):
    need(type(x) in (int,float) and math.isfinite(x) and abs(x)<10000,"INVALID_NATIVE_MATERIAL_NUMBER")
    return x
def check(doc):
    need(doc.get("schema")=="scp.n03d-bh.original-mpfb-multi-view-contact-proxy.v1" and
         doc.get("public_original_substitute_only") is True and
         doc.get("mpfb_official_source_commit")==PIN and
         doc.get("motion_git_blob")=="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61" and
         doc.get("source_60hz_frames")==[120,479] and
         doc.get("real_blender_5_2_4_version")==[5,2,4] and
         doc.get("reference_cameras_are_static_per_view") is False and
         doc.get("reference_camera_angles_fixed_but_track_root") is True and
         doc.get("all_images_contain_subject_foreground") is True and
         doc.get("characters_wear_real_CC0_shoes") is False and
         doc.get("true_anatomical_heel_ball_semantics_calibrated") is False and
         doc.get("real_force_grf") is False and
         doc.get("floor_contact_verified") is False and
         doc.get("independent_critics_approved_realism") is False and
         doc.get("protected_actors_or_likeness_used") is False and
         doc.get("mvp_accepted") is False and
         doc.get("status")=="PASS_NARROW_NATIVE_HEEL_BALL_PROXY_AND_REAL_RASTER_HOLD_REALISM",
         "SOURCE_OR_PROTECTED_PHYSICAL_FALSE_PROMOTION")
    need(doc.get("actor") in SHA and doc.get("rig") in ("default","game_engine") and
         doc.get("body_actual_evaluated_shape_sha256")==SHA[doc["actor"]],
         "SOURCE_MORPHOLOGY_DRIFT")
    groups=doc.get("fixed_heel_ball_body_vertex_region_receipts",{})
    results=doc.get("material_results",{})
    need(set(groups)=={"L","R"} and set(results)=={"L","R"},
         "MISSING_BILATERAL_SOURCE_HEEL_BALL")
    for side in ("L","R"):
        g=groups[side]
        need(all(type(g[k])==int and g[k]>=5 for k in ("n_heel","n_ball")) and
             g.get("source_weighted_total",0)>=25 and
             len(g.get("rest_axis",[]))==3 and
             all(type(z) in (float,int) and math.isfinite(z) for z in g["rest_axis"]),
             "ORIGINAL_HEEL_BALL_PARTITION")
        r=results[side]
        need(r.get("true_heel_ball_anatomical_joints_corroborated") is False,
             "FAKE_ANATOMICAL_HEEL_BALL_ACCEPTANCE")
        for name in ("heel_region","ball_region"):
            m=r[name]
            need(m.get("samples_60hz")==360 and
                 m.get("native_body_region_not_worn_shoe") is True and
                 m.get("foot_material_fixed_ids") is True and
                 m.get("actual_force_support_ground_verified") is False,
                 "FALSE_SHOE_OR_TIMELINE")
            for key in ("global_min_z_m","global_max_z_m","fullclip_p50_xy_speed_mps"):
                scalar(m[key])
            need(m["global_max_z_m"]>=m["global_min_z_m"] and
                 m["fullclip_p50_xy_speed_mps"]>=0 and
                 type(m.get("near_own_low_adjacent_pairs"))==int and
                 m["near_own_low_adjacent_pairs"]>=0,
                 "BAD_NATIVE_CONTACT_CANDIDATE")
            if m.get("near_own_low_p50_xy_speed_mps") is not None:
                scalar(m["near_own_low_p50_xy_speed_mps"])
        for key in ("ball_minus_heel_height_p50_m","ball_minus_heel_height_min_m",
                    "ball_minus_heel_height_max_m"):scalar(r[key])
        need(r["ball_minus_heel_height_min_m"]<=r["ball_minus_heel_height_p50_m"]<=
             r["ball_minus_heel_height_max_m"],"BAD_HEEL_ROLLOVER_RANGES")
    stills=doc.get("genuine_blender_workbench_original_source_stills",[])
    need(len(stills)==6 and
         {(v.get("view"),v.get("source_index_60hz")) for v in stills}==
         {(view,idx) for view in ("front","profile") for idx in (0,180,359)},
         "NO_TRUE_TWO_CAMERA_THREE_TIME_VISUAL")
    need(len({x["png_sha256"] for x in stills})>=4,
         "SOURCE_SAFE_RASTER_NOT_DISTINCT")
    for v in stills:
        need(v.get("body_source_only_CC0_not_photo") is True and
             isinstance(v.get("png_sha256"),str) and len(v["png_sha256"])==64 and
             type(v.get("bytes")) is int and v["bytes"]>2000 and
             type(v.get("visible_nonblack_character_pixels")) is int and
             v["visible_nonblack_character_pixels"]>=300 and
             0.002<=scalar(v.get("visible_nonblack_character_fraction"))<=.80 and
             v.get("camera_follows_original_actor_root") is True and
             isinstance(v.get("camera_target_m"),list) and len(v["camera_target_m"])==3 and
             all(type(z) in (float,int) and math.isfinite(z) for z in v["camera_target_m"]) and
             v.get("png")==f'{doc["actor"]}_{doc["rig"]}_{v["view"]}_{v["source_index_60hz"]:03d}.png',
             "FAKE_WORKBENCH_PNG_OR_SOURCE")
    return "HOLD"
