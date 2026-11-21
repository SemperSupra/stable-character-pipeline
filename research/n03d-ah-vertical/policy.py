"""N03D-AH independent geometry, per-parameter budget and temporal critic.

Reference plane Z=0, NOT source-recorded terrain. ALWAYS physical HOLD.
"""
import math
from statistics import median
from vertical import MODES,BOUNDS,SIDES,ACTORS,check_plan,temporal_metrics

def req(x,why):
    if not x:raise ValueError(why)

def finite(x):
    req(type(x) in (float,int) and math.isfinite(x) and abs(x)<100,"FINITE_NUMBERS")
    return float(x)

def point(x):
    req(isinstance(x,(list,tuple)) and len(x)==2,"POINT_DIM")
    return tuple(finite(t) for t in x)

def measure(rows,side,label):
    xy=[];foot=[];z=[]
    for row in rows:
        v=row[label][side]
        req(set(v)=={"bone_head_xy_m","material_xy_m","min_z_m"},"REAL_SHOE_WITNESS")
        xy.append(point(v["material_xy_m"]))
        foot.append(point(v["bone_head_xy_m"]))
        z.append(finite(v["min_z_m"]))
    speeds=[math.dist(xy[i],xy[i-1])*60 for i in range(1,len(xy))]
    near=[speeds[i-1] for i in range(1,len(z)) if abs(z[i-1])<=.012 and abs(z[i])<=.012]
    return {"max_ground_penetration_m":round(max(0.,-min(z)),6),
            "p50_material_speed_mps":round(median(speeds),6),
            "max_material_speed_mps":round(max(speeds),6),
            "max_material_near_ground_speed_mps":round(max(near),6) if near else None,
            "near_ground_pairs":len(near),
            "max_reference_plane_hover_m":round(max(z),6)}

def assess(report):
    req(report.get("schema")=="scp.n03d-ah.vertical-shoe-actual-native.v1" and
        report.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
        report.get("scene_source_unchanged") is True and
        report.get("corrected_animation_saved") is False and
        report.get("true_native_dual_leg_ik_executed") is True and
        report.get("floor_reference_calibrated") is False and
        report.get("physical_stance_proven") is False and
        report.get("anatomical_heel_ball_toe_verified") is False and
        report.get("independent_visual_review") is False and
        report.get("mvp_accepted") is False,"PROVENANCE_OR_FORGED_PHYSICAL_ADMISSION")
    actors=report.get("actors")
    req(isinstance(actors,list) and len(actors)==2,"ACTOR_COUNT")
    seen=set();out=[]
    for actor in actors:
        name=actor.get("actor")
        req(name in ACTORS and isinstance(actor.get("windows"),list) and len(actor["windows"])==16,"ACTOR_OR_WINDOWS")
        for w in actor["windows"]:
            key=(name,w.get("source_selected_side"),w.get("mode"),w.get("bound_m"))
            req(key[1] in SIDES and key[2] in MODES and key[3] in BOUNDS and key not in seen,
                "DUPLICATE_OR_BAD_FACTORIAL")
            seen.add(key)
            index=w.get("first_source_sample")
            req(type(index) is int and 180<=index<=353 and w.get("physical_stance_proven") is False
                and w.get("actual_anatomical_support_proven") is False and
                w.get("reference_ground_z_m")==0.0,"CONTACT_OR_GROUND")
            rows=w.get("samples")
            req(isinstance(rows,list) and len(rows)==6,"SAMPLE_COUNT")
            max_root=max_leg=max_error=max_pose=0.
            for j,row in enumerate(rows):
                req(row.get("source_index")==index+j and abs(finite(row.get("source_time_s"))-(index+j)/60)<1e-7,
                    "TIMEBASE")
                plan=row.get("plan")
                check_plan(plan)
                req(plan["mode"]==w["mode"] and plan["bound_m"]==w["bound_m"],"PLAN_CONFIG")
                max_root=max(max_root,plan["root_z_m"])
                max_leg=max(max_leg,*[plan["leg_z_m"][s] for s in SIDES])
                req(set(row["source"])==set(SIDES) and set(row["candidate"])==set(SIDES),"BILATERAL_SHOE")
                req(set(row["source_foot_bone_head_z_m"])==set(SIDES) and
                    set(row["candidate_foot_bone_head_z_m"])==set(SIDES) and
                    set(row["actual_target_bone_vertical_residual_m"])==set(SIDES),"BONE_Z_MISSING")
                for s in SIDES:
                    src=finite(row["source_foot_bone_head_z_m"][s])
                    after=finite(row["candidate_foot_bone_head_z_m"][s])
                    error=finite(row["actual_target_bone_vertical_residual_m"][s])
                    req(error>=0 and abs(error-abs(after-src-plan["root_z_m"]-plan["leg_z_m"][s]))<1e-5,
                        "VERTICAL_TARGET_RESIDUAL_WRONG")
                    max_error=max(max_error,error)
                max_pose=max(max_pose,finite(row["max_fivebone_pose_rotation_rad"]))
                if w["mode"]=="original":
                    for s in SIDES:
                        req(abs(row["candidate"][s]["min_z_m"]-row["source"][s]["min_z_m"])<.002,"BASELINE_NULL_DRIFT")
            temporal=temporal_metrics(rows)
            req(temporal==w["temporal_source_plan"],"TEMPORAL_METRIC_NOT_REPLAYABLE")
            metrics={s:{"source":measure(rows,s,"source"),
                        "candidate":measure(rows,s,"candidate")} for s in SIDES}
            flags=["UNKNOWN_SOURCE_PLANT","UNVERIFIED_FLOOR_Z",
                   "NO_ANATOMICAL_HEEL_BALL_TOE","NO_NATIVE_VISUAL_CRITIC"]
            for s in SIDES:
                m=metrics[s]["candidate"]
                if m["max_ground_penetration_m"]>.01:flags.append(s+"_PENETRATION_GT_10MM")
                if m["near_ground_pairs"]<3:flags.append(s+"_INSUFFICIENT_CONTACT")
                if m["max_material_near_ground_speed_mps"] is None or m["max_material_near_ground_speed_mps"]>.08:
                    flags.append(s+"_CONTACT_SLIDE_UNQUALIFIED")
            if max_error>.02:flags.append("NATIVE_VERTICAL_TARGET_RESIDUAL_GT_20MM")
            if max_pose>.35:flags.append("FIVEBONE_POSE_GT_0P35RAD")
            if temporal["max_root_speed_mps"]>1:flags.append("ROOT_LIFT_UNSMOOTHED")
            out.append({"actor":name,"selected_side":key[1],"source_start_index":index,
                        "mode":key[2],"bound_m":key[3],
                        "actual_max_root_lift_m":round(max_root,6),
                        "actual_max_leg_lift_m":round(max_leg,6),
                        "max_realized_bone_vertical_target_error_m":round(max_error,6),
                        "max_pose_change_rad":round(max_pose,6),
                        "temporal":temporal,"sides":metrics,
                        "rejections":sorted(set(flags)),"physical_contact_accepted":False})
    req(seen=={(a,s,m,b) for a in ACTORS for s in SIDES for m in MODES for b in BOUNDS},"FACTORIAL_INCOMPLETE")
    return {"schema":"scp.n03d-ah.vertical-native-independent-critic.v1",
            "status":"HOLD","mvp_accepted":False,
            "source_contact_proven":False,"physical_gait_accepted":False,"windows":out}
