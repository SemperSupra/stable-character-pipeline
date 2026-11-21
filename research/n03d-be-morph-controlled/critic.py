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
