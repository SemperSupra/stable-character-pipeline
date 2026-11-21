"""BF independent true source CC0 worn shoe 60Hz material cohort and false-contact gate."""
import math
ACTORS=("AsterOriginal","JuniperOriginal")
RIGS=("default","game_engine")
MODES=("direct_canonical","rest_frame_conjugated")
REGIONS=("heel_proxy","toe_proxy","full_low_cohort")
def need(x,code):
    if not x:raise ValueError(code)
def n(x):
    need(type(x) in (float,int) and math.isfinite(x) and abs(x)<10000,"NONFINITE_MATERIAL")
    return float(x)
def assess(doc):
    need(doc.get("schema")=="scp.n03d-bf.identical-morphology-real-cc0-worn-footwear.v1" and
         doc.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         doc.get("MPFB_upstream_commit")=="9de0707fdc88438d7c53a1a2ac7937d9221e2431" and
         doc.get("source_original_100style_blob")=="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61" and
         doc.get("original_cc0_shoe_pack_sha256")=="ded3f70428505eabbf1f6d7b5f61196a7366ef20757103d276ad0ed336c35ada" and
         doc.get("official_Blender_version")==[5,2,4] and doc.get("source_original_rate_hz")==60 and
         doc.get("source_frames")==[120,479] and
         doc.get("source_body_cloth_or_shoe_saved") is False and
         doc.get("raw_100style_media_published") is False and
         doc.get("true_contact_force_measured") is False and
         doc.get("true_anatomical_heel_toe_verified") is False and
         doc.get("source_floor_measured") is False and
         doc.get("independent_visual_accepted") is False and
         doc.get("physical_gait_accepted") is False and
         doc.get("mvp_accepted") is False and
         doc.get("status")=="HOLD_PHYSICAL_CONTACT_AND_VISUAL",
         "SOURCE_RIGHTS_OR_FORGED_RELEASE")
    people=doc.get("true_skin_model_actors")
    need(len(people)==2 and set(a["name"] for a in people)==set(ACTORS),
         "WRONG_ACTORS_OR_MORPHS")
    for a in people:
        need(a["default_bones"]==163 and a["game_engine_bones"]==53,
             "NOT_OFFICIAL_PAIR_RIG")
        diff=a["body_rest_vertex_delta"]
        need(diff["count"]>10000 and n(diff["max_rest_vertex_deviation_m"])>=0 and
             diff["same_morphology_max_1mm"]==(diff["max_rest_vertex_deviation_m"]<=.001),
             "FORGED_SAME_BODY")
    shoes=doc.get("actual_shoe_sources")
    need(set(shoes)=={f"{a}:{r}" for a in ACTORS for r in RIGS},"NOT_TWO_BY_TWO_TRUE_SHOES")
    for a in shoes.values():
        need(a["shoe_total_vertices"]>100 and a["actual_skin"] is True,
             "NO_REAL_SKINNED_CC0_SHOE")
    trials=doc.get("actual_native_360x60hz_trials")
    need(len(trials)==8 and set((x["actor"],x["rig"],x["mode"]) for x in trials)==
         {(a,r,m) for a in ACTORS for r in RIGS for m in MODES},"UNBALANCED_REAL_DOE")
    out=[]
    for t in trials:
        need(t["source_frames"]==[120,479] and t["native_source_fps"]==60 and
             t["rig_bones"]==(163 if t["rig"]=="default" else 53) and
             t["actual_original_CC0_shoe_skinned"] is True and
             t["ground_contact_true"] is False and
             t["anatomical_sole_verified"] is False and t["visual_accepted"] is False and
             t["physical_gait_accepted"] is False,
             "FALSE_MATERIAL_OR_NATIVE_ADMISSION")
        need(t["actual_mesh_source_asset"] in ("toigo_stiletto_booties","toigo_ballet_flats"),
             "NO_FOOTWEAR_LICENSE")
        a=t.get("original_rig_rest_toe_proxy")
        m=t.get("native_60hz_shoe_material")
        need(set(a)=={"L","R"} and set(m)=={"L","R"},"NO_BILATERAL_CC0_SHOE")
        for side in ("L","R"):
            s=a[side]
            need(s["weighted_shoe_vertices"]>=24 and
                 s["persistent_low_vertices"]>=12 and
                 s["heel_proxy_vertices"]>=5 and s["toe_proxy_vertices"]>=5 and
                 s["actual_anatomical_sole_heel_toe_verified"] is False and
                 s["side_assigned_from_real_source_skin_weights"] is True,
                 "FALSE_TOE_AUTHORITY")
            need(set(m[side])==set(REGIONS),"MISSING_HEEL_TOE_MATERIAL_COHORT")
            for region,vals in m[side].items():
                need(vals["samples_60hz"]==360 and
                     vals["max_reference_penetration_known"] is False and
                     vals["sole_labeled_anatomically"] is False and
                     vals["physical_contact_accepted"] is False and
                     type(vals["low_relative_adjacent_pairs"])==int,
                     "FALSE_PLANTED_GROUND_ACCEPTANCE")
                for key in ("min_native_mesh_z_m","max_native_mesh_z_m",
                            "fullclip_p50_persistent_material_xy_speed_mps",
                            "fullclip_max_persistent_material_xy_speed_mps"):
                    n(vals[key])
                need(vals["max_native_mesh_z_m"]>=vals["min_native_mesh_z_m"] and
                     vals["fullclip_p50_persistent_material_xy_speed_mps"]>=0 and
                     vals["fullclip_max_persistent_material_xy_speed_mps"]>=
                     vals["fullclip_p50_persistent_material_xy_speed_mps"],
                     "MATERIAL_PHYSICS_UNSOUND")
        out.append({"actor":t["actor"],"rig":t["rig"],"mode":t["mode"],
                    "shoe":t["actual_mesh_source_asset"],
                    "both_named_foot_material_cohorts":{k:{
                         region:{"p50_speed_mps":m[k][region]["fullclip_p50_persistent_material_xy_speed_mps"],
                                 "low_p50_speed_mps":m[k][region]["low_relative_p50_persistent_material_xy_speed_mps"],
                                 "low_pairs":m[k][region]["low_relative_adjacent_pairs"]}
                         for region in REGIONS} for k in ("L","R")},
                    "natural_gait_accepted":False})
    return {"schema":"scp.n03d-bf.independent-real-shoe-evidence.v1",
            "true_morphology_match_both_1mm":all(a["body_rest_vertex_delta"]["same_morphology_max_1mm"] for a in people),
            "source_exact":True,"all_actually_skinned_shoes":True,
            "physical_gait_accepted":False,"mvp_accepted":False,
            "status":"HOLD_PHYSICAL_AND_VISUAL","trials":out}
