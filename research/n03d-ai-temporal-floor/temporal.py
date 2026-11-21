"""N03D-AI minimal Lipschitz continuous root-Z lift on genuine native shoe trace.

Exact analytic pointwise least nonnegative L-Lipschitz majorant for required
Z lifts d[t]=max(0,-left_min_z,-right_min_z), in scene reference Z=0.
This tests feasibility of root-only floor clearance, not balance, source force,
leg anatomy, material skate, or physical contact.
"""
import hashlib,json,math
from statistics import median

SIDES=("rest_local_x_negative","rest_local_x_positive")
ACTORS=("AsterOriginal","JuniperOriginal")
LIMITS=(.04,.08,.12)
SPEED_LIMITS=(.25,.75)
N=143
HZ=24
TRACE_SCHEMA="scp.n03d-g.evaluated-foot-contact-observer.v1"
SOURCE_SCHEMA="scp.n03d-ac.matched-source-to-bone-60hz.v1"

def require(ok,code):
    if not ok:raise ValueError(code)

def numeric(x):
    require(type(x) in (int,float) and math.isfinite(x) and abs(x)<100,"INVALID_NONFINITE_NUMBER")
    return float(x)

def samples(trace_actor):
    require(trace_actor.get("actor") in ACTORS and trace_actor.get("native_bones")==163 and
            set(trace_actor.get("sides",{}))==set(SIDES),"SHOE_ACTOR_OR_SIDE")
    output={}
    for side in SIDES:
        v=trace_actor["sides"][side].get("samples")
        require(isinstance(v,list) and len(v)==N,"SOURCE_SHOE_LENGTH")
        for i,row in enumerate(v):
            require(set(row)=={"t_s","xy_m","z_m"} and abs(numeric(row["t_s"])-i/HZ)<1e-7 and
                    isinstance(row["xy_m"],list) and len(row["xy_m"])==2 and
                    all(math.isfinite(numeric(z)) for z in row["xy_m"]),
                    "SOURCE_SHOE_TIMEBASE")
        output[side]=[numeric(x["z_m"]) for x in v]
    return output

def minimum_lipschitz_majorant(deficits,speed):
    """Exact smallest nonnegative L-Lipschitz sequence dominating all deficits.

    Need r_i >= d_i and |r_i-r_j| <= speed*|i-j|/HZ.
    Necessary: r_i >= d_j - speed*|i-j|/HZ for every j.
    Sufficiency: max of inverted cones is L-Lipschitz and dominates d.
    """
    require(isinstance(deficits,list) and len(deficits)==N and
            all(numeric(x)>=0 for x in deficits),"NEGATIVE_OR_MISSING_DEFICIT")
    require(speed in SPEED_LIMITS,"SPEED_NOT_PREDECLARED")
    return [max(0.,max(d-speed*abs(i-j)/HZ for j,d in enumerate(deficits))) for i in range(N)]

def evaluate(trace,ac):
    require(trace.get("schema")==TRACE_SCHEMA and
            trace.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            trace.get("frame_rate_hz")==HZ and trace.get("sample_count_per_side")==N and
            trace.get("heel_toe_anatomy_verified") is False and
            trace.get("mvp_accepted") is False,"SOURCE_TRACE_RIGHTS")
    require(ac.get("schema")==SOURCE_SCHEMA and ac.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            ac.get("source_scene_sha256")==trace.get("source_scene_sha256") and
            ac.get("source_shoe_trace_sha256")==hashlib.sha256(
                (json.dumps(trace,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()).hexdigest() or False,
            "SOURCE_AC_JOIN") # checked again against file hash outside if formatting differs
    require(ac.get("source_motion_changed") is False and ac.get("mvp_accepted") is False,
            "MUTATED_SOURCE_OR_FALSE_MVP")
    actual=trace["actors"]
    require(isinstance(actual,list) and len(actual)==2 and
            sorted(a["actor"] for a in actual)==sorted(ACTORS),"ACTOR_COUNT")
    result=[]
    for actor in actual:
        z=samples(actor)
        deficits=[max(0.,-z[SIDES[0]][i],-z[SIDES[1]][i]) for i in range(N)]
        trials=[]
        for speed in SPEED_LIMITS:
            base=minimum_lipschitz_majorant(deficits,speed)
            peak=max(base)
            # Cone-majorant proof witness checked independently on full timeline.
            require(all(base[i]>=deficits[i]-1e-10 and
                        (i==0 or abs(base[i]-base[i-1])<=speed/HZ+1e-10) for i in range(N)),
                    "ANALYTIC_MAJORIZATION_PROOF")
            for budget in LIMITS:
                r=[min(budget,v) for v in base]
                residual={s:[z[s][i]+r[i] for i in range(N)] for s in SIDES}
                violations={s:sum(v<-.01 for v in residual[s]) for s in SIDES}
                # Neither source nor candidate soles are anatomical; "above Z"
                # is not literal hover unless planted contact has been proved.
                high={s:sum(v>.03 for v in residual[s]) for s in SIDES}
                delta=[r[i]-r[i-1] for i in range(1,N)]
                jerk=[r[i]-2*r[i-1]+r[i-2] for i in range(2,N)]
                trials.append({
                    "root_budget_m":budget,"root_vertical_slew_mps":speed,
                    "minimum_uncapped_peak_lift_m":round(peak,6),
                    "full_plane_nonpenetration_feasible_with_budget":peak<=budget+1e-10,
                    "max_actual_root_lift_m":round(max(r),6),
                    "max_root_vertical_speed_mps":round(max(abs(v) for v in delta)*HZ,6),
                    "max_root_vertical_acceleration_mps2":round(max(abs(v) for v in jerk)*HZ*HZ,6),
                    "max_reference_plane_penetration_m":round(max(0.,-min(v for s in SIDES for v in residual[s])),6),
                    "per_side_penetration_gt_10mm_frame_counts":violations,
                    "per_side_above_reference_30mm_frame_counts":high,
                    "predicted_root_lift_m":[round(v,9) for v in r],
                    "native_root_or_leg_actuated":False,
                    "physical_support_contact_verified":False,
                })
        result.append({"actor":actor["actor"],"required_uncapped_peak_lift_m":round(max(deficits),6),
                       "timebase_hz":HZ,"sample_count":N,"scene_reference_z_m":0.,
                       "source_floor_verified":False,"trials":trials})
    return {"schema":"scp.n03d-ai.actual-source-temporal-root-floor-feasibility.v1",
            "source_class":"ORIGINAL_FICTIONAL_CC0",
            "source_scene_sha256":trace["source_scene_sha256"],
            "source_trace_sha256":hashlib.sha256(json.dumps(trace,sort_keys=True).encode()).hexdigest(),
            "source_ac_sha256":hashlib.sha256(json.dumps(ac,sort_keys=True).encode()).hexdigest(),
            "source_motion_changed":False,"native_motion_actuated":False,
            "gait_accepted":False,"mvp_accepted":False,
            "reference_ground_calibrated":False,"source_contact_proven":False,
            "anatomical_marker_proven":False,"status":"HOLD","actors":result}

def independent(summary):
    require(summary.get("schema")=="scp.n03d-ai.actual-source-temporal-root-floor-feasibility.v1" and
            summary.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            summary.get("native_motion_actuated") is False and
            summary.get("source_motion_changed") is False and
            summary.get("gait_accepted") is False and
            summary.get("mvp_accepted") is False and
            summary.get("reference_ground_calibrated") is False and
            summary.get("source_contact_proven") is False and
            summary.get("anatomical_marker_proven") is False and
            summary.get("status")=="HOLD","FORGED_PHYSICAL_ACCEPTANCE")
    seen=set()
    for actor in summary.get("actors",[]):
        require(actor.get("actor") in ACTORS and actor["actor"] not in seen,"ACTOR_SET")
        seen.add(actor["actor"])
        require(actor.get("sample_count")==N and actor.get("timebase_hz")==HZ and
                actor.get("source_floor_verified") is False and
                len(actor.get("trials",[]))==len(LIMITS)*len(SPEED_LIMITS),"FACTORIAL_COUNT")
        pairs=set()
        for trial in actor["trials"]:
            pair=(trial["root_budget_m"],trial["root_vertical_slew_mps"])
            require(pair[0] in LIMITS and pair[1] in SPEED_LIMITS and pair not in pairs,"FACTORIAL_KEY")
            pairs.add(pair)
            require(trial.get("native_root_or_leg_actuated") is False and
                    trial.get("physical_support_contact_verified") is False,"SPOOFED_NATIVE_OR_CONTACT")
            data=trial["predicted_root_lift_m"]
            require(len(data)==N and all(0<=numeric(x)<=pair[0]+1e-7 for x in data),"LIFT_BUDGET")
            require(all(abs(data[i]-data[i-1])*HZ<=pair[1]+1e-5 for i in range(1,N)),"SLEW_BUDGET")
            require(trial["minimum_uncapped_peak_lift_m"]>=0 and
                    trial["full_plane_nonpenetration_feasible_with_budget"] == (trial["minimum_uncapped_peak_lift_m"]<=pair[0]+2e-6),
                    "FALSIFIED_FEASIBILITY")
        require(pairs=={(b,v) for b in LIMITS for v in SPEED_LIMITS},"MISSING_FACTORIAL")
    require(seen==set(ACTORS),"MISSING_ACTOR")
    return "HOLD"
