"""BE independent same-body provenance, source-clock, rig-native and false-floor critic."""
import math
NAMES=("AsterOriginal","JuniperOriginal")
RIGS=("default","game_engine")
MODES=("direct_canonical","rest_frame_conjugated")
def need(ok,s):
    if not ok:raise ValueError(s)
def n(v):
    need(type(v) in (int,float) and math.isfinite(v),"NONFINITE")
    return float(v)
def assess(v):
    need(v.get("schema")=="scp.n03d-be.identical-phenotype-two-official-MPF-rigs.v1" and
         v.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         v.get("MPFB_original_source_commit")=="9de0707fdc88438d7c53a1a2ac7937d9221e2431" and
         v.get("source_motion_blob_sha1")=="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61" and
         v.get("source_frames")==[120,479] and v.get("source_rate_hz")==60 and
         v.get("official_blender_version")==[5,2,4] and
         v.get("morphology_independently_measured") is True and
         v.get("shoe_asset_present") is False and
         v.get("source_floor_calibrated") is False and
         v.get("force_contact_verified") is False and
         v.get("physical_gait_accepted") is False and
         v.get("mvp_accepted") is False and v.get("status")=="HOLD_PHYSICS_AND_SHOE_CONTACT",
         "PROVENANCE_OR_PHYSICS_PROMOTION")
    actors=v.get("morphologies")
    need(len(actors)==2 and set(a["actor"] for a in actors)==set(NAMES),"ACTOR_OR_SHAPE_SET")
    passed={}
    for a in actors:
        m=a["rest_body_match"]
        need(a["default_bones"]==163 and a["game_engine_bones"]==53 and
             m["count"]>10000 and
             n(m["max_rest_vertex_deviation_m"])>=0 and
             n(m["p50_rest_vertex_deviation_m"])>=0 and
             m["same_morphology_max_1mm"] == (m["max_rest_vertex_deviation_m"]<=.001),
             "NOT_163_VS_53_REAL_MORPHOLOGY")
        passed[a["actor"]]=m["same_morphology_max_1mm"]
    ts=v.get("native_trials",[])
    need(len(ts)==8 and
         set((t["actor"],t["rig"],t["mode"]) for t in ts)==
         {(a,r,m) for a in NAMES for r in RIGS for m in MODES},
         "MISSING_ACTUAL_NATIVE_COMPARISON")
    out=[]
    for t in ts:
        need(t["bone_count"]== (163 if t["rig"]=="default" else 53) and
             t["source_frames"]==[120,479] and t["native_rate_hz"]==60 and
             t["native_original_source_blender_pose_samples_per_side"]==360 and
             t["true_shoe_contact_accepted"] is False,"RIG_POSE_OR_CONTACT")
        need(abs(n(t["matched_rest_shape_max_deviation_m"])-
                 n(next(a for a in actors if a["actor"]==t["actor"])["rest_body_match"]["max_rest_vertex_deviation_m"]))<1e-8,
             "MORPHOLOGY_UNBOUND")
        foot=t["fixed_native_body_material_foot_witness"]
        need(set(foot)=={"L","R"},"NO_BILATERAL_SENSOR")
        for side,m in foot.items():
            need(m["frames"]==360 and m["floor_calibrated"] is False and
                 m["ground_force_measured"] is False and
                 m["real_shoe_mesh_measured"] is False,
                 "FALSE_SHOE_OR_FORCE")
            for key in ("min_native_foot_body_z_m","max_native_foot_body_z_m",
                        "p50_fullclip_stable_body_foot_xy_speed_mps",
                        "max_fullclip_stable_body_foot_xy_speed_mps"):
                n(m[key])
            need(m["max_native_foot_body_z_m"]>=m["min_native_foot_body_z_m"] and
                 m["p50_fullclip_stable_body_foot_xy_speed_mps"]>=0 and
                 m["max_fullclip_stable_body_foot_xy_speed_mps"]>=
                 m["p50_fullclip_stable_body_foot_xy_speed_mps"],
                 "IMPOSSIBLE_BODY_FOOT_TRAJECTORY")
        out.append({"actor":t["actor"],"rig":t["rig"],"mode":t["mode"],
                    "matched_morphology_1mm":passed[t["actor"]],
                    "actual_native_body_skin_not_shoe":True,
                    "bilateral_body_foot_sensor":foot,
                    "physical_gait_accepted":False})
    return {"schema":"scp.n03d-be.independent-native-critic.v1",
            "status":"HOLD_PHYSICS_SHOES_VISUAL",
            "all_morphology_matched_to_1mm":all(passed.values()),
            "actor_match":passed,
            "mvp_accepted":False,"trials":out}
