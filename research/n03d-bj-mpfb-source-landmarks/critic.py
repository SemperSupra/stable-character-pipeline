"""BJ independent original source FK native Blender real 60Hz multiobjective holdout critic."""
import math
SOURCE="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61"
TRAIN={"Hips","LeftHip","RightHip","LeftKnee","RightKnee"}
TEST={"LeftAnkle","RightAnkle","LeftToe","RightToe"}
MORPH={"AsterOriginal":"9156e167a19083500fc5323155166abd3daa2a93510bacb8beeb7de8c83c4a4b",
       "JuniperOriginal":"8dfa35c38f3df7cbff4601232d4a8b7dcc1d0ee74f34ead424c787cf638aa918"}
MODES={"direct_canonical","rest_frame_conjugated"}
def need(x,why):
    if not x:raise ValueError(why)
def num(x):
    need(type(x) in (float,int) and math.isfinite(x) and 0<=x<1e4,
         "INVALID_SOURCE_TRAJECTORY_NUMBER")
def check(x):
    need(x.get("schema")=="scp.n03d-bj.same-morph-source-fk-to-blender-world-joints.v1" and
         x.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         x.get("actor") in MORPH and
         x.get("original_100style_source_git_blob")==SOURCE and
         len(x.get("original_100style_source_sha256",""))==64 and
         x.get("source_100style_frame_window")==[120,479] and
         x.get("true_source_100style_clock_hz")==60 and
         x.get("official_mpfb_source_commit")=="9de0707fdc88438d7c53a1a2ac7937d9221e2431" and
         x.get("source_no_ground_reaction_force_available") is True and
         x.get("source_first_frame_is_walk_not_neutral_rest") is True and
         x.get("fitted_holdout_used_in_training") is False and
         x.get("true_anatomical_side_or_sole_accepted") is False and
         x.get("photo_or_identity_protected_used") is False and
         x.get("mvp_accepted") is False and
         x.get("status")=="PASS_NARROW_MORPH_MATCHED_60HZ_SOURCE_NATIVE_TRAJECTORY_HOLD_GAIT",
         "FALSE_SOURCE_REST_OR_MVP_ADOPTION")
    src=x.get("source_world_fk")
    need(isinstance(src,dict) and set(src)==TRAIN|TEST,"SOURCE_FK_NINE_LANDMARKS_MISSING")
    for row in src.values():
        for k in ("speed_p50_mps","speed_p95_mps","total_displacement_m"):num(row[k])
        need(row["speed_p95_mps"]>=row["speed_p50_mps"],"SOURCE_FK_SPEED_PERCENTILES_REVERSED")
    native=x.get("rigs")
    need(isinstance(native,list) and len(native)==2 and
         {row.get("rig") for row in native}=={"default","game_engine"},
         "NOT_TWO_MORPH_MATCHED_MPF_RIGS")
    for row in native:
        need(row.get("bone_count")=={"default":163,"game_engine":53}[row["rig"]] and
             row.get("actual_same_source_evaluated_shape_sha256")==MORPH[x["actor"]] and
             row.get("actual_native_source_pre_rig_shape_vertices",0)>=10000 and
             row.get("first_recorded_walk_pose_used_not_source_tpose") is True and
             set(row.get("five_training_joints",[]))==TRAIN and
             set(row.get("four_heldout_joints",[]))==TEST and
             set(row["five_training_joints"]).isdisjoint(TEST),
             "SOURCE_MORPHOLOGY_OR_TRAIN_HOLDOUT_LEAK")
        s=row["source_mocap_vs_target_rest_calibration_fit_scale"]
        need(type(s) in (int,float) and math.isfinite(s) and .3<s<3.,
             "PROPER_SIM3_CALIBRATION_MISSING")
        need(set(row.get("source_to_native_walkfirst_rest_alignment_errors_m",{}))==TRAIN|TEST,
             "REST_FITTING_SOURCE_JOINTS_MISSING")
        for residual in row["source_to_native_walkfirst_rest_alignment_errors_m"].values():num(residual)
        modes=row.get("modes")
        need(isinstance(modes,list) and len(modes)==2 and
             {m.get("mode") for m in modes}==MODES,
             "NATIVE_DIRECT_VS_BASIS_ABLATION_MISSING")
        for m in modes:
            need(m.get("rig")==row["rig"] and
                 m.get("actual_native_60hz_frames")==360 and
                 m.get("source_fk_motion_world_samples")==360 and
                 m.get("actual_deformed_skin_verified") is True and
                 m.get("true_ground_or_force_proven") is False and
                 m.get("mvp_accepted") is False,
                 "SOURCE_NATIVE_60HZ_SKIN_OR_PHYSICAL_FALSE_PROMOTION")
            stamps=m.get("native_real_body_local_shape_sha_samples",[])
            need(isinstance(stamps,list) and len(stamps)==5 and
                 len(set(stamps))>=3 and
                 all(isinstance(v,str) and len(v)==64 for v in stamps),
                 "FALSE_RIGID_ROOT_ONLY_GAIT")
            err=m.get("source_fk_to_native_dynamic_residuals")
            need(set(err)==TRAIN|TEST,"SOURCE_DYNAMICS_NINE_BONES_NOT_MEASURED")
            for sample in err.values():
                for key in ("p50_dynamic_displacement_error_m",
                            "p95_dynamic_displacement_error_m",
                            "max_dynamic_displacement_error_m",
                            "target_world_step_speed_p50_mps"):num(sample[key])
                need(sample["p50_dynamic_displacement_error_m"]<=
                     sample["p95_dynamic_displacement_error_m"]<=
                     sample["max_dynamic_displacement_error_m"]+.000002,
                     "SOURCE_TRAJECTORY_RESIDUAL_UNSOUND")
    return "HOLD"
