"""Independent N03D-AG full factorial actual native skinned shoe critic.

Fail closed. Native execution success != stance or visual acceptance.
"""
import math
from statistics import median

ACTORS=("AsterOriginal","JuniperOriginal")
SIDES=("L","R")
MODES=("original","root_only","leg_only","joint")
BOUNDS=(.04,.08)

def check(ok,code):
    if not ok:raise ValueError(code)

def num(x):
    check(type(x) in (int,float) and math.isfinite(x) and abs(x)<100,"NONFINITE_OR_ABSURD")
    return float(x)

def vec(p,n=2):
    check(isinstance(p,(list,tuple)) and len(p)==n,"POINT_DIM")
    return tuple(num(v) for v in p)

def kinematics(samples,side,label):
    pts=[]
    for s in samples:
        item=s[label][side]
        check(set(item)=={"bone_head_xy_m","material_xy_m","min_z_m"},"NATIVE_OBSERVABLES_MISSING")
        pts.append((vec(item["bone_head_xy_m"]),vec(item["material_xy_m"]),num(item["min_z_m"])))
    vel=[math.dist(a[1],b[1])*60 for a,b in zip(pts,pts[1:])]
    bone=[math.dist(a[0],b[0])*60 for a,b in zip(pts,pts[1:])]
    near=[v for i,v in enumerate(vel) if abs(pts[i][2])<=.012 and abs(pts[i+1][2])<=.012]
    return {
        "max_shoe_material_speed_mps":round(max(vel),6),
        "p50_shoe_material_speed_mps":round(median(vel),6),
        "max_bone_head_speed_mps":round(max(bone),6),
        "max_ground_penetration_m":round(max(0,-min(v[2] for v in pts)),6),
        "near_ground_pair_count":len(near),
        "max_near_ground_shoe_material_speed_mps":round(max(near),6) if near else None,
    }

def assess(report):
    check(report.get("schema")=="scp.n03d-ag.actual-dual-leg-native-factorial.v1" and
          report.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
          report.get("source_motion_changed") is False and report.get("corrected_blend_saved") is False and
          report.get("native_5bone_and_root_actuators_executed") is True and
          report.get("source_stance_proven") is False and
          report.get("anatomical_foot_correspondence_proven") is False and
          report.get("independent_visual_review_completed") is False and
          report.get("mvp_accepted") is False,"SOURCE_RIGHTS_OR_FALSE_PROMOTION")
    actors=report.get("actors")
    check(isinstance(actors,list) and len(actors)==2,"ACTOR_COUNT")
    observed=set();output=[]
    for a in actors:
        actor=a.get("actor")
        check(actor in ACTORS and isinstance(a.get("windows"),list) and len(a["windows"])==16,"ACTOR_WINDOWS")
        for w in a["windows"]:
            key=(actor,w.get("source_selected_side"),w.get("mode"),w.get("bound_m"))
            check(key[1] in SIDES and key[2] in MODES and key[3] in BOUNDS and key not in observed,"WINDOW_KEY")
            observed.add(key)
            check(w.get("source_contact_proven") is False and w.get("heel_toe_anatomy_verified") is False and
                  w.get("real_native_both_legs_installed") is True,"FALSE_CONTACT_OR_RIG")
            base=w.get("first_source_sample")
            check(type(base) is int and 180<=base<=353,"SOURCE_SAMPLE_WINDOW")
            samples=w.get("samples")
            check(isinstance(samples,list) and len(samples)==6,"SOURCE_SAMPLES")
            source_ref={}
            max_root=max_leg=max_res=max_pose=0.
            for j,row in enumerate(samples):
                n=base+j
                check(row.get("source_index")==n and abs(num(row.get("source_time_s"))-n/60)<1e-7,"CLOCK")
                check(set(row.get("source",{}))==set(SIDES) and set(row.get("candidate",{}))==set(SIDES),"SHOE_SIDES")
                plan=row.get("plan")
                check(plan.get("mode")==w["mode"] and plan.get("bound_m")==w["bound_m"] and
                      plan.get("source_physical_plant_proven") is False and
                      plan.get("target_source_index")==n and abs(num(plan["target_source_t_s"])-n/60)<1e-7,
                      "PLAN_TIME_CONFIG")
                root=vec(plan["root_delta_xy_m"])
                max_root=max(max_root,math.hypot(*root))
                check(math.hypot(*root)<=w["bound_m"]+1e-6,"ROOT_BUDGET")
                check(set(plan["leg"])==set(SIDES),"DUAL_LEG_MISSING")
                if w["mode"] in ("original","leg_only"):check(math.hypot(*root)<=1e-7,"FORBIDDEN_ROOT")
                if w["mode"] in ("original","root_only"):
                    check(all(math.hypot(*vec(plan["leg"][s]["delta_xy_m"]))<=1e-7 for s in SIDES),"FORBIDDEN_LEG")
                for side in SIDES:
                    leg=vec(plan["leg"][side]["delta_xy_m"])
                    max_leg=max(max_leg,math.hypot(*leg))
                    check(math.hypot(*leg)<=w["bound_m"]+1e-6,"LEG_BUDGET")
                    max_res=max(max_res,num(row["actual_target_foot_head_residual_xy_m"][side]))
                max_pose=max(max_pose,num(row["max_native_five_bone_pose_delta_rad"]))
                for side in SIDES:
                    src=row["source"][side]
                    check(set(src)=={"bone_head_xy_m","material_xy_m","min_z_m"},"SOURCE_SHOE_OBSERVABLE")
                    vec(src["bone_head_xy_m"]);vec(src["material_xy_m"]);num(src["min_z_m"])
                    if side in source_ref:
                        pass
                if w["mode"]=="original":
                    for side in SIDES:
                        check(math.dist(vec(row["source"][side]["bone_head_xy_m"]),vec(row["candidate"][side]["bone_head_xy_m"]))<.002,
                              "ORIGINAL_NULL_DISAGREEMENT")
            m={side:{"source":kinematics(samples,side,"source"),
                     "candidate":kinematics(samples,side,"candidate")} for side in SIDES}
            reasons=[]
            for side in SIDES:
                c=m[side]["candidate"]
                if c["max_ground_penetration_m"]>.010:reasons.append(side+"_SHOE_PENETRATION")
                if c["near_ground_pair_count"]<3:reasons.append(side+"_UNKNOWN_CONSECUTIVE_CONTACT")
                if c["max_near_ground_shoe_material_speed_mps"] is None or c["max_near_ground_shoe_material_speed_mps"]>.08:
                    reasons.append(side+"_UNQUALIFIED_MATERIAL_SLIDING")
            if max_pose>.35:reasons.append("JOINT_POSE_DELTA_GT_0P35RAD")
            if max_res>.02:reasons.append("UNREALIZED_FOOT_BONE_TARGET_GT_20MM")
            reasons.extend(["SOURCE_STANCE_UNKNOWN","HEEL_BALL_TOE_UNVERIFIED","INDEPENDENT_VISUAL_MISSING"])
            output.append({"actor":actor,"source_selected_side":w["source_selected_side"],
                           "first_source_sample":base,"mode":w["mode"],"bound_m":w["bound_m"],
                           "max_root_actuation_m":round(max_root,6),"max_leg_actuation_m":round(max_leg,6),
                           "max_realized_foot_target_error_m":round(max_res,6),
                           "max_fivebone_pose_rotation_rad":round(max_pose,6),
                           "sides":m,"physical_rejections":sorted(set(reasons)),
                           "physical_contact_accepted":False})
    check(observed=={(a,s,m,b) for a in ACTORS for s in SIDES for m in MODES for b in BOUNDS},"INCOMPLETE_FACTORIAL")
    return {"schema":"scp.n03d-ag.native-dual-leg-independent-critic.v1","status":"HOLD",
            "physical_contact_accepted":False,"natural_gait_accepted":False,
            "mvp_accepted":False,"windows":output}
