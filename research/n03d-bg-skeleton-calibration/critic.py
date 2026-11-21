"""N03D-BG independent provenance, no train/test leakage and actual native geometry critic."""
import math
PIN="3f5b4896f1b28501b40aa9c408e47dba51322443"
EXPECTED={"rigify":("d3327b94c302278b5471c24d712ef5dc49f0d682",161),
          "named":("2f86c50b2938f0f7d78df7ff9835864d6af0fd4a",65)}
TRAIN={"Hips","LeftHip","RightHip","LeftKnee","RightKnee"}
HOLD={"LeftAnkle","RightAnkle","LeftToe","RightToe"}
MODES={"fixed_yup_to_zup_axis_only","five_landmark_rest_similarity"}
def need(ok,code):
    if not ok:raise ValueError(code)
def scalar(s):
    need(type(s) in (float,int) and math.isfinite(s) and abs(s)<10000,"NOT_FINITE_NATIVE_WORLD_MEASUREMENT")
    return float(s)
def check(doc):
    need(doc.get("schema")=="scp.n03d-bg.world-similarity-source-to-native-360-v1"
         and doc.get("source_class")=="PUBLIC_ORIGINAL_CC0_THREE_CONTROLLER"
         and doc.get("original_three_commit")==PIN
         and doc.get("source_and_native_same_public_GLBFIle") is True
         and doc.get("calibration_orthogonal_no_reflection") is True
         and doc.get("measured_ground_force") is False
         and doc.get("body_style_or_actor_identity_accepted") is False
         and doc.get("true_sole_contact_accepted") is False
         and doc.get("mvp_accepted") is False
         and doc.get("status")=="PASS_NARROW_SOURCE_TO_NATIVE_WORLD_MATCH_HOLD_PHYSICS",
         "FORGED_SOURCE_OR_PHYSICAL_ACCEPTANCE")
    need(doc.get("rig") in EXPECTED and
         doc.get("source_model_git_blob")==EXPECTED[doc["rig"]][0] and
         doc.get("blender_native_bones")==EXPECTED[doc["rig"]][1] and
         len(doc.get("source_pose_sha256",""))==64 and
         len(doc.get("source_model_sha256",""))==64,"WRONG_ORIGINAL_MODEL_OR_TRACE")
    need(set(doc.get("calibration_fitted_using_only_original_rest_bone_centres",[]))==TRAIN and
         set(doc.get("out_of_sample_calibration_joints",[]))==HOLD and
         set(doc.get("calibration_fitted_using_only_original_rest_bone_centres",[])).isdisjoint(HOLD),
         "TRAIN_HOLDOUT_INFORMATION_LEAKAGE")
    fit=doc.get("calibration_rest_landmark_results",{})
    need(set(fit)==MODES,"MISSING_AXIS_CONTROL_OR_TRAINED_CALIBRATION")
    for method in fit.values():
        need(len(method.get("matrix_source_world_to_native_world_colmajor",[]))==16 and
             all(type(x) in (int,float) and math.isfinite(x) for x in
                 method["matrix_source_world_to_native_world_colmajor"]),
             "SIM3_MATRIX_MISSING_OR_NAN")
        for label,joints in (("train",TRAIN),("heldout",HOLD)):
            d=method[label]
            need(set(d["by_joint_m"])==joints,"TRAIN_TEST_SET_CHANGED")
            scalar(d["rms_m"]);scalar(d["max_m"])
            need(d["rms_m"]>=0 and d["max_m"]>=d["rms_m"]-1e-5,
                 "NEGATIVE_OR_MISLABELED_CALIBRATION")
    need(fit["five_landmark_rest_similarity"]["train"]["rms_m"]<=
         fit["fixed_yup_to_zup_axis_only"]["train"]["rms_m"]+1e-4,
         "TRAIN_FIT_IS_NOT_OPTIMAL")
    trials=doc.get("retarget_models",[])
    need(len(trials)==2 and set(q["mode"] for q in trials)==MODES,"NOT_TWO_NATIVE_REPLAY_METHODS")
    for q in trials:
        need(q.get("actual_native_blender_frames")==360 and
             q.get("actual_native_skin_mesh_count",0)>0 and
             q.get("source_controller_phases_are_not_true_contact") is True and
             q.get("physical_contact_accepted") is False,
             "FAKE_SOURCE_CONTACT_OR_BAD_60HZ_SAMPLING")
        material=q.get("real_native_foot_material",{})
        errors=q.get("world_ankle_and_toe_delta_errors",{})
        need(set(material)=={"L","R"} and set(errors)==HOLD,
             "NO_INDEPENDENT_BILATERAL_NATIVE_FOOT")
        for s in ("L","R"):
            m=material[s]
            need(m.get("samples")==360 and m.get("stable_material_count",0)>=5 and
                 m.get("nonswing_adjacent_pairs",0)>20 and
                 m.get("source_nonswing_is_not_force_verified") is True and
                 m.get("actual_sole_and_ground_unverified") is True,"FALSE_SOLE_CONTACT")
            for k in ("fullclip_p50_xy_speed_mps","nonswing_p50_xy_speed_mps",
                      "own_min_z_m","own_max_z_m"):
                scalar(m[k])
            need(m["fullclip_p50_xy_speed_mps"]>=0 and
                 m["nonswing_p50_xy_speed_mps"]>=0 and
                 m["own_max_z_m"]>=m["own_min_z_m"],"BAD_NATIVE_SKIN_GEOMETRY")
        for key,d in errors.items():
            scalar(d["p50_m"]);scalar(d["max_m"])
            need(d["p50_m"]>=0 and d["max_m"]>=d["p50_m"],
                 "INVALID_SOURCE_ANATOMICAL_CORRESPONDENCE")
    return "HOLD"
