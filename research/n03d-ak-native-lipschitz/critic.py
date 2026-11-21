"""N03D-AK independent actual 24Hz and 60Hz dual-shoe native world-root lift critic.

No corrected Blender saved, no anatomical planted-foot or floor acceptance.
"""
import math,statistics

ACTORS=("AsterOriginal","JuniperOriginal")
SIDES=("rest_local_x_negative","rest_local_x_positive")
CHOSEN=((.08,.25),(.08,.75),(.12,.25),(.12,.75))
N24=143;N60=356
def require(ok,code):
    if not ok:raise ValueError(code)
def numeric(x):
    require(type(x) in (float,int) and math.isfinite(x) and abs(x)<100,"NONFINITE")
    return float(x)
def xy(v):
    require(isinstance(v,(list,tuple)) and len(v)==2,"XY_DIM")
    return tuple(numeric(z) for z in v)
def lerp(values,t):
    """Source 24Hz schedule, evaluate strictly within available [0,142] timeline."""
    require(len(values)==N24 and 0<=t<=142/24+1e-9,"OUT_OF_SCENE")
    x=t*24;i=min(142,int(math.floor(x+1e-9)))
    if i==142:return numeric(values[i])
    f=x-i
    return numeric(values[i])*(1-f)+numeric(values[i+1])*f
def summary(rows,rate):
    require(len(rows)==(N24 if rate==24 else N60),"FULL_CLIP_SHOE_ROWS")
    z=[numeric(s["candidate_z_m"]) for s in rows]
    pts=[xy(s["candidate_xy_m"]) for s in rows]
    speeds=[math.dist(pts[i],pts[i-1])*rate for i in range(1,len(rows))]
    near=[speeds[i-1] for i in range(1,len(rows)) if abs(z[i-1])<=.012 and abs(z[i])<=.012]
    return {
        "min_candidate_z_m":round(min(z),6),
        "max_candidate_z_m":round(max(z),6),
        "max_reference_penetration_m":round(max(0.,-min(z)),6),
        "max_horizontal_material_speed_mps":round(max(speeds),6),
        "p50_horizontal_material_speed_mps":round(statistics.median(speeds),6),
        "near_reference_adjacent_pair_count":len(near),
        "max_near_reference_material_speed_mps":round(max(near),6) if near else None,
        "over_reference_30mm_frame_count":sum(v>.03 for v in z),
    }
def assess(doc):
    require(doc.get("schema")=="scp.n03d-ak.native-lipschitz-root-z.v1" and
            doc.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            doc.get("source_scene_unchanged") is True and
            doc.get("actual_native_root_world_actuated") is True and
            doc.get("root_curve_saved") is False and
            doc.get("independent_floor_calibration_done") is False and
            doc.get("anatomical_contact_verified") is False and
            doc.get("source_force_proven") is False and
            doc.get("independent_visual_review") is False and
            doc.get("mvp_accepted") is False,"FORGED_RIGHTS_OR_MVP_ACCEPTANCE")
    actors=doc.get("actors")
    require(isinstance(actors,list) and len(actors)==2 and
            set(a["actor"] for a in actors)==set(ACTORS),"ACTOR_SET")
    output=[]
    for actor in actors:
        require(actor.get("actor") in ACTORS and actor.get("rig_bones")==163,"ACTUAL_RIG")
        trials=actor.get("trials")
        require(isinstance(trials,list) and len(trials)==4 and
                set((t["budget_m"],t["slew_mps"]) for t in trials)==set(CHOSEN),"TRIAL_SET")
        for trial in trials:
            cap,speed=trial["budget_m"],trial["slew_mps"]
            require(trial.get("shoe_partitions_are_anatomical") is False and
                    trial.get("root_only_no_leg_ik") is True and
                    trial.get("source_ground_is_scene_Z0_only") is True,
                    "FALSE_ANATOMY_OR_NATIVE_MODE")
            samples=trial.get("samples")
            require(isinstance(samples,dict) and set(samples)=={"24hz","60hz"},"TIMELINE_SET")
            measures={}
            root_peak=0.;root_speeds=[];max_mismatch=0.
            for clock,rate,num in (("24hz",24,N24),("60hz",60,N60)):
                rows=samples[clock]
                require(isinstance(rows,list) and len(rows)==num,"SAMPLE_COUNT")
                for i,row in enumerate(rows):
                    require(row.get("index")==i and abs(numeric(row["time_s"])-i/rate)<1e-7 and
                            set(row["shoes"])==set(SIDES),"TIMEBASE_OR_SIDE")
                    z=numeric(row["root_world_lift_m"])
                    require(0<=z<=cap+1e-6,"ROOT_LIFT_BUDGET")
                    root_peak=max(root_peak,z)
                    if i>0:
                        v=abs(z-numeric(rows[i-1]["root_world_lift_m"]))*rate
                        root_speeds.append(v)
                        require(v<=speed+2e-5,"ROOT_SLEW_LIMIT")
                    for side in SIDES:
                        s=row["shoes"][side]
                        require(set(s)=={"source_z_m","candidate_z_m","source_xy_m","candidate_xy_m"},
                                "ACTUAL_SHOE_MEASUREMENT")
                        a=numeric(s["source_z_m"]);b=numeric(s["candidate_z_m"])
                        u=xy(s["source_xy_m"]);v=xy(s["candidate_xy_m"])
                        mismatch=abs((b-a)-z)
                        max_mismatch=max(max_mismatch,mismatch)
                        require(mismatch<.002,"NATIVE_RIGID_Z_DRIFT")
                        require(math.dist(u,v)<.002,"NATIVE_HORIZONTAL_SOURCE_LEAKAGE")
                measures[clock]={s:summary([
                    {"candidate_z_m":r["shoes"][s]["candidate_z_m"],
                     "candidate_xy_m":r["shoes"][s]["candidate_xy_m"]} for r in rows],rate) for s in SIDES}
            reasons=["SOURCE_STANCE_UNKNOWN","REAL_FLOOR_UNVERIFIED",
                     "HEEL_BALL_TOE_AND_BODY_UNVERIFIED","INDEPENDENT_VISUAL_NOT_DONE"]
            for rate in measures:
                for side,m in measures[rate].items():
                    if m["max_reference_penetration_m"]>.010:reasons.append(rate+"_"+side+"_PENETRATION")
                    if m["near_reference_adjacent_pair_count"]<3:reasons.append(rate+"_"+side+"_NO_CONTACT_SEQUENCE")
                    if m["max_near_reference_material_speed_mps"] is None or m["max_near_reference_material_speed_mps"]>.08:
                        reasons.append(rate+"_"+side+"_SKATING")
            output.append({"actor":actor["actor"],"budget_m":cap,"slew_mps":speed,
                           "max_actual_root_lift_m":round(root_peak,6),
                           "max_root_vertical_speed_mps":round(max(root_speeds),6),
                           "max_actual_vertical_rigid_translation_mismatch_m":round(max_mismatch,6),
                           "actual_24_and_offgrid_60hz_shoes":measures,
                           "physical_gait_accepted":False,"rejections":sorted(set(reasons))})
    return {"schema":"scp.n03d-ak.native-root-z-independent-critic.v1",
            "status":"HOLD","physical_contact_accepted":False,"mvp_accepted":False,
            "actual_native_root_qualified_narrow":True,"trials":output}
