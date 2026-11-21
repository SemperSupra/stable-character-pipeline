"""BF independent cross-runtime real source/Blender skinned material and false force critic."""
import math
EXPECTED="3f5b4896f1b28501b40aa9c408e47dba51322443"
MODES={"direct_local_delta","bone_rest_conjugated_delta"}
BLOBS={"rigify":"d3327b94c302278b5471c24d712ef5dc49f0d682",
       "named":"2f86c50b2938f0f7d78df7ff9835864d6af0fd4a"}
def require(ok,message):
    if not ok:raise ValueError(message)
def number(x):
    require(type(x) in (int,float) and math.isfinite(x) and abs(x)<10000,"NONFINITE_NUMERICAL_MEASURE")
    return float(x)
def verify(r):
    require(r.get("schema")=="scp.n03d-bf.live-three-controller-to-native-blender-skin.v1" and
            r.get("source_class")=="ORIGINAL_PUBLIC_CC0_THREE_RUNTIME" and
            r.get("controller_repo_commit")==EXPECTED and
            r.get("motion_same_360frames_and_model") is True and
            r.get("source_100style_mocap_matched") is False and
            r.get("true_sole_and_anatomical_contact_proven") is False and
            r.get("source_measured_ground_force_proven") is False and
            r.get("independent_visual_accepted") is False and
            r.get("mvp_accepted") is False and
            r.get("status")=="PASS_NARROW_ACTUAL_CONTROLLER_TO_SKIN_REPLAY_HOLD_CONTACT",
            "SOURCE_OR_PHYSICAL_FALSE_PROMOTION")
    require(r.get("rig") in BLOBS and
            r.get("source_model_git_blob")==BLOBS[r["rig"]] and
            len(r.get("source_model_sha256",""))==64 and
            len(r.get("source_pose_trace_sha256",""))==64 and
            (r.get("native_rig_bones")==161 if r["rig"]=="rigify" else r.get("native_rig_bones",0)>10) and
            r.get("actual_native_blender_skinned_meshes",0)>0,"ACTUAL_ORIGINAL_RIG_NOT_AUTHENTIC")
    number(r["native_leg_length_m"]);number(r["source_leg_length_m"])
    trials=r.get("trials")
    require(isinstance(trials,list) and len(trials)==2 and
            set(t.get("mode") for t in trials)==MODES,"ABLATION_NOT_COMPLETE")
    for t in trials:
        require(t.get("native_60hz_frames")==360 and
                t.get("controller_source_phases_not_ground_truth") is True and
                t.get("mvp_or_physical_contact_accepted") is False,"FAKE_SOURCE_CLOCK_OR_STANCE")
        mat=t.get("actual_skinned_material")
        miss=t.get("source_joint_displacement_errors")
        require(isinstance(mat,dict) and isinstance(miss,dict) and
                set(mat)=={"L","R"} and set(miss)=={"L","R"},"MISSING_BILATERAL_SKIN")
        for side in ("L","R"):
            d=mat[side]
            require(d.get("source_frames")==360 and
                    d.get("foot_material_count",0)>=5 and
                    d.get("actual_sole_ground_and_force_contact_verified") is False,
                    "NO_VALID_MATERIAL_OR_FAKE_CONTACT")
            for k in ("local_low_m","high_m","p50_all_foot_material_xy_speed_mps"):
                number(d[k])
            require(d["high_m"]>=d["local_low_m"] and
                    d["p50_all_foot_material_xy_speed_mps"]>=0,"SKIN_MOVEMENT_UNREALISTIC")
            for name in ("p50_native_material_in_controller_declared_nonswing_mps",
                         "p50_material_near_own_low_height_mps"):
                if d.get(name) is not None:number(d[name])
            m=miss[side]
            require(m.get("coordinate_frame")==
                    "THREE_Y_UP_VS_BLENDER_Z_UP_CALIBRATED_BY_FIRST_FRAME_TRANSLATION_ONLY",
                    "NO_TRUSTWORTHY_POSE_REFERENCE")
            number(m["p50_joint_displacement_error_m"]);number(m["max_joint_displacement_error_m"])
    return "HOLD"
