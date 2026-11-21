"""N03D-AJ/F1 cross-source weight-side authority (source original only).

F1 actual MPFB CC0 vertex-group masses override *named rig-side* classifier.
AJ heldout toe-Y -> shoe-min-Z residual is not a side/ground/force classifier.
"""
import hashlib,json,math
ACTORS=("AsterOriginal","JuniperOriginal")
PARTS=("rest_local_x_negative","rest_local_x_positive")
def require(ok,why):
    if not ok:raise ValueError(why)
def number(x):
    require(type(x) in (float,int) and math.isfinite(x),"NONFINITE_F1_WEIGHT")
    return float(x)
def join(aj,f1,f1_sha):
    require(aj.get("schema")=="scp.n03d-aj.source-to-shoe-ground-bias-control.v1" and
            aj.get("status")=="HOLD" and aj.get("source_floor_calibrated") is False and
            aj.get("mvp_accepted") is False,
            "AJ_EXPLICIT_HOLD")
    require(f1.get("schema")=="scp.n03d-f1.native-shoe-foot-weights.v1" and
            f1.get("source_scene_sha256")==aj.get("source_scene_sha256") and
            f1.get("source_trace_sha256")==aj.get("source_shoe_trace_sha256") and
            f1.get("anatomical_side_verified") is False and
            f1.get("gait_contact_accepted") is False and
            f1.get("mvp_accepted") is False,"F1_SOURCE_OR_ACCEPTANCE")
    require(isinstance(f1_sha,str) and len(f1_sha)==64 and
            all(c in "0123456789abcdef" for c in f1_sha),"F1_SHA")
    actors={a["actor"]:a for a in f1.get("actors",[])}
    require(len(f1.get("actors",[]))==2 and set(actors)==set(ACTORS),"F1_ACTORS")
    output=[]
    for ajactor in aj.get("actors",[]):
        actor=actors[ajactor["actor"]]
        partitions=actor.get("partitions")
        require(isinstance(partitions,list) and len(partitions)==2,"F1_PARTITION_COUNT")
        assignments={}
        for part in partitions:
            name=part.get("rest_local_partition")
            require(name in PARTS and name not in assignments,"F1_PARTITION_ID")
            choice=part.get("candidate_rig_side")
            side=choice.get("label")
            dominance=number(choice.get("dominance"))
            require(side in ("L","R") and dominance>=.85 and dominance<=1.+1e-8 and
                    part.get("anatomical_foot_side_accepted") is False,
                    "F1_RIG_LABEL_NOT_PROVEN")
            assignments[name]={"named_rig_side":side,"actual_vertex_weight_dominance":dominance}
        require(set(assignments)==set(PARTS) and
                set(v["named_rig_side"] for v in assignments.values())=={"L","R"},
                "F1_UNIQUE_NAMED_RIG_SIDES")
        weight_named=("REST_X_POS_IS_LEFT" if assignments[PARTS[1]]["named_rig_side"]=="L"
                      else "REST_X_NEG_IS_LEFT")
        variants=ajactor.get("comparisons")
        require(len(variants)==2 and
                set(v["mapping"] for v in variants)=={"REST_X_POS_IS_LEFT","REST_X_NEG_IS_LEFT"},
                "AJ_VARIANTS")
        errors={v["mapping"]:number(v["mean_heldout_abs_p95_m"]) for v in variants}
        require(all(v>=0 for v in errors.values()),"AJ_RESIDUAL")
        numerical_best=min(errors,key=errors.get)
        output.append({"actor":ajactor["actor"],"f1_sole_vertex_group_side_proven":True,
                       "f1_anatomical_side_proven":False,
                       "source_joint_to_sole_correspondence_proven":False,
                       "f1_source_rest_side_weights":assignments,
                       "weight_based_named_rig_mapping":weight_named,
                       "aj_height_residual_numerical_winner_NOT_FOR_SIDE_ADOPTION":numerical_best,
                       "aj_height_residual_agrees_with_vertex_weights":numerical_best==weight_named,
                       "actual_f1_mapping_heldout_mean_abs_p95_m":errors[weight_named],
                       "alternate_mapping_heldout_mean_abs_p95_m":errors[
                            "REST_X_POS_IS_LEFT" if weight_named=="REST_X_NEG_IS_LEFT"
                            else "REST_X_NEG_IS_LEFT"],
                       "physical_contact_accepted":False})
    require(len(output)==2 and set(o["actor"] for o in output)==set(ACTORS),"AJ_ACTOR_SET")
    return {"schema":"scp.n03d-aj-f1.actual-shoe-weight-prior-reconciliation.v1",
            "source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_scene_sha256":aj["source_scene_sha256"],
            "source_f1_report_sha256":f1_sha,
            "source_aj_report_sha256":hashlib.sha256(json.dumps(aj,sort_keys=True).encode()).hexdigest(),
            "named_rig_side_source":"TRUE_CC0_VERTEX_GROUP_WEIGHTS_NOT_HEIGHT_RESIDUAL",
            "anatomical_ground_or_contact_proven":False,
            "mvp_accepted":False,"status":"HOLD","actors":output}
def independent(out):
    require(out.get("schema")=="scp.n03d-aj-f1.actual-shoe-weight-prior-reconciliation.v1" and
            out.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            out.get("status")=="HOLD" and
            out.get("named_rig_side_source")=="TRUE_CC0_VERTEX_GROUP_WEIGHTS_NOT_HEIGHT_RESIDUAL" and
            out.get("anatomical_ground_or_contact_proven") is False and
            out.get("mvp_accepted") is False,"FORGED_RIG_OR_CONTACT_ADMISSION")
    a=out.get("actors")
    require(isinstance(a,list) and len(a)==2 and set(x["actor"] for x in a)==set(ACTORS),"SOURCE_ACTORS")
    for actor in a:
        require(actor.get("f1_sole_vertex_group_side_proven") is True and
                actor.get("f1_anatomical_side_proven") is False and
                actor.get("source_joint_to_sole_correspondence_proven") is False and
                actor.get("physical_contact_accepted") is False,
                "RIG_WEIGHTS_NOT_GROUND_ANATOMY")
        assignment=actor.get("f1_source_rest_side_weights")
        require(set(assignment)==set(PARTS) and
                set(x["named_rig_side"] for x in assignment.values())=={"L","R"} and
                all(.85<=number(x["actual_vertex_weight_dominance"])<=1 for x in assignment.values()),
                "F1_SIDE_DISTRIBUTION")
        expected="REST_X_POS_IS_LEFT" if assignment[PARTS[1]]["named_rig_side"]=="L" else "REST_X_NEG_IS_LEFT"
        require(actor["weight_based_named_rig_mapping"]==expected,"F1_MAPPING_SUBSTITUTION")
        require(actor["aj_height_residual_agrees_with_vertex_weights"] == (
            actor["aj_height_residual_numerical_winner_NOT_FOR_SIDE_ADOPTION"]==expected
        ),"FALSE_AJ_AGREEMENT")
    return "HOLD"
