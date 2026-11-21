"""BE separate critic for matched morphology and source/rig proof, false contact gates."""
import math
def check(x):
    def need(y,msg):
        if not y:raise ValueError(msg)
    need(x.get("schema")=="scp.n03d-be.exact-identical-morph-53-163-v1" and
         x.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         x.get("mpfb_official_commit")=="9de0707fdc88438d7c53a1a2ac7937d9221e2431" and
         x.get("source_100style_git_blob")=="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61" and
         x.get("same_morphology_before_rig") is True and
         x.get("source_360_frame_clock_hz")==60 and
         x.get("shoe_heels_or_toe_force_verified") is False and
         x.get("true_floor_known") is False and
         x.get("body_anatomical_joint_centers_proven") is False and
         x.get("independent_multi_camera_visual_pass") is False and
         x.get("actor_production_identity_accepted") is False and
         x.get("mvp_accepted") is False,
         "SOURCE_OR_PHYSICAL_EVIDENCE_FALSIFICATION")
    need(x.get("actor") in ("AsterOriginal","JuniperOriginal") and
         len(x.get("exact_source_body_mesh_sha256",""))==64 and
         len(x.get("source_100style_sha256",""))==64 and
         isinstance(x.get("same_body_vertex_count"),int) and
         x["same_body_vertex_count"]>=10000,"SOURCE_OR_BODY_FINGERPRINT")
    need(x.get("actual_material_scope")==
         "SOURCE_BODY_ARMATURE_ONLY_FIXED_VERTEX_IDS_NOT_RENDER_MASK",
         "UNDECLARED_SOURCE_MESH_MODIFIER_PROJECTION")
    mod=x.get("non_armature_display_modifiers_excluded")
    need(isinstance(mod,dict) and set(mod)=={"default","game_engine"} and
         all(isinstance(v,list) and
             all(isinstance(m,dict) and set(m)=={"name","type"} and
                 m["type"]!="ARMATURE" for m in v) for v in mod.values()),
         "UNTRACEABLE_MASK_MODIFIER_EXCLUSIONS")
    need(x.get("evaluated_morphology_matched_before_rigging") is True and
         isinstance(x.get("actual_evaluated_macro_shape"),dict) and
         x["actual_evaluated_macro_shape"].get("sha256")==x["exact_source_body_mesh_sha256"] and
         x["actual_evaluated_macro_shape"].get("vertices")==x.get("same_body_vertex_count") and
         len(x.get("underlying_core_mesh_sha256",""))==64 and
         isinstance(x.get("shape_key_profile_fingerprint"),dict) and
         len(x["shape_key_profile_fingerprint"].get("shape_key_weight_sha256",""))==64 and
         x["shape_key_profile_fingerprint"].get("active_shape_key_count",0)>0,
         "UNEVALUATED_SOURCE_MORPHOLOGY_NOT_AUTHORITY")
    need(x.get("post_rig_shape_equivalence_not_assumed") is True,"FALSE_POST_RIG_IDENTICAL_CLAIM")
    post=x.get("post_rig_evaluated_shape_per_rig")
    drift=x.get("post_rig_shape_drift_per_rig")
    need(isinstance(post,dict) and isinstance(drift,dict) and
         set(post)=={"default","game_engine"} and set(drift)=={"default","game_engine"},
         "MISSING_POST_RIG_SHAPE_RECEIPTS")
    for rig in post:
        need(post[rig].get("vertices")==x["same_body_vertex_count"] and
             len(post[rig].get("sha256",""))==64,"POST_RIG_SHAPE_MISSING")
        z=drift[rig]
        for key in ("max_world_centered_vertex_displacement_m",
                    "rms_world_centered_vertex_displacement_m"):
            need(type(z.get(key)) in (int,float) and math.isfinite(z[key]) and z[key]>=0,
                 "NONFINITE_SOURCE_RIG_REFIT_DRIFT")
        need(z.get("pre_and_post_evaluated_shape_identical")==
             (post[rig]["sha256"]==x["exact_source_body_mesh_sha256"]),
             "FALSE_POST_RIG_REFIT_EQUIVALENCE")
    diffs=x["named_rig_joint_head_differences_m"]
    need(set(diffs)=={"LeftHip","LeftKnee","LeftAnkle","LeftToe","RightHip","RightKnee","RightAnkle","RightToe"},
         "NAMED_JOINTS_UNVERIFIED")
    need(all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in diffs.values()),
         "INVALID_JOINT_DELTA")
    res=x.get("results",[])
    need(len(res)==4 and set((a.get("rig"),a.get("mode")) for a in res)==
         {(rig,mode) for rig in ("default","game_engine")
          for mode in ("direct_canonical","rest_frame_conjugated")},"FACTORS_NOT_COMPLETE")
    for a in res:
        need(a.get("bone_count")=={"default":163,"game_engine":53}[a["rig"]] and
             a.get("original_body_SHA256")==x["exact_source_body_mesh_sha256"] and
             a.get("n_real_60hz_frames")==360 and a.get("source_frame_interval")==[120,479] and
             a.get("own_low_height_reference_not_authenticated_ground") is True and
             a.get("gait_contact_accepted") is False,
             "SOURCE_NATIVE_FACTOR_MISMATCH")
        need(type(a.get("leg_scale_ratio")) in (int,float) and
             .5<=a["leg_scale_ratio"]<=2.5,"UNREACHABLE_SCALE")
        need(set(a.get("skin_vertex_cohorts",{}))=={"L","R"} and
             all(type(v)==int and v>=5 for v in a["skin_vertex_cohorts"].values()),
             "UNVERIFIED_SKIN")
        for side,v in a.get("actual_material",{}).items():
            need(side in ("L","R") and v.get("samples_60hz")==360 and
                 v.get("source_ground_is_known") is False and
                 v.get("true_force_contact_measured") is False,
                 "FORGED_MATERIAL_GROUND")
            keys=("p50_fullclip_stable_material_xy_speed_mps",
                  "max_fullclip_stable_material_xy_speed_mps",
                  "minimum_skin_z_m","maximum_skin_z_m","relative_min_reference_Z_m")
            need(all(type(v.get(k)) in (int,float) and math.isfinite(v[k]) for k in keys),
                 "NONFINITE_NATIVE_MATERIAL")
    return "HOLD"
