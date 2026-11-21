"""Independent source-only 60Hz real skinned foot material critic, no physical promotion."""
import math
MODELS={"vsim":53,"cc":53,"rigify":161}
MODES={"direct_canonical","rest_frame_conjugated"}
def need(c,why):
    if not c:raise ValueError(why)
def number(x):
    need(type(x) in (int,float) and math.isfinite(x) and abs(x)<10000,"NONFINITE")
    return float(x)
def assess(d):
    need(d.get("schema")=="scp.n03d-bd.same-100style-rig-matched-native.v1" and
         d.get("source_class")=="PUBLIC_SOURCE_RIGHTS_RESEARCH_ONLY" and
         d.get("source_same_360_frames_for_all_candidates") is True and
         d.get("source_mocap_ground_force_proven") is False and
         d.get("source_rights_paid_or_protected") is False and
         d.get("true_anatomical_correspondence_accepted") is False and
         d.get("original_motion_file_published") is False and
         d.get("actual_blender_skin_actuated") is True and
         d.get("physical_gait_accepted") is False and d.get("mvp_accepted") is False,
         "SPOOFED_PROVENANCE_OR_GAIT_ACCEPTANCE")
    need(d.get("candidate") in MODELS and d.get("target_native_rig_bones")==MODELS[d["candidate"]],
         "NONMATCHED_NATIVE_RIG")
    need(d.get("original_100style_blob")=="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61" and
         d.get("source_commit")=="10938b4881b55c5801faded89e427407ddf14bce" and
         len(d.get("source_sha256",""))==64 and len(d.get("model_sha256",""))==64,
         "SRC_SHA_OR_COMMIT")
    trials=d.get("trials",[])
    need(len(trials)==2 and set(x.get("mode") for x in trials)==MODES,"MISSING_ACTUATION_ABLATION")
    for a in trials:
        need(a.get("source_frames")==[120,479] and a.get("source_fps")==60 and
             a.get("native_actually_evaluated_skinned_60hz_samples_per_foot")==360 and
             a.get("source_floor_calibrated") is False and
             a.get("output_reference_is_own_lowest_skin_sample") is True,
             "FALSE_SOURCE_FLOOR_OR_CLOCK")
        cohorts=a.get("actual_skin_cohorts",{})
        measures=a.get("rig_foot_measures",{})
        need(set(cohorts)=={"L","R"} and set(measures)=={"L","R"} and
             all(type(v)==int and v>=5 for v in cohorts.values()),"NO_NATIVE_SKIN_PARTITION")
        for side,m in measures.items():
            need(m["samples_60hz"]==360 and
                 m["source_ground_is_known"] is False and
                 m["true_force_contact_measured"] is False and
                 m["candidate_near_low_adjacent_pairs"]>=0,
                 "FALSE_FORCE_OR_SAMPLE")
            for key in ("minimum_skin_z_m","maximum_skin_z_m","relative_min_reference_Z_m",
                        "p50_fullclip_stable_material_xy_speed_mps",
                        "max_fullclip_stable_material_xy_speed_mps"):
                number(m[key])
            need(m["maximum_skin_z_m"]>=m["minimum_skin_z_m"] and
                 m["p50_fullclip_stable_material_xy_speed_mps"]>=0 and
                 m["max_fullclip_stable_material_xy_speed_mps"]>=
                 m["p50_fullclip_stable_material_xy_speed_mps"],"MOTION_RANGE")
    return "HOLD"
