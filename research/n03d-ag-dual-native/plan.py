"""N03D-AG: source-trace-calibrated root and bilateral leg capped actuator plans.

Exact source-selected heldout 60Hz intervals from AE; plan is not anatomical
or force-grounded. Native Blender runner must independently measure realized
foot and shoe motion, not infer native success from this forward kinematic plan.
"""
import math
import sys
from pathlib import Path

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/"n03d-ae-factorial"))
from factorial import candidate,source_eligible,xy,source_xy
sys.path.insert(0,str(HERE.parent/"n03d-s-planar-align"))
from planar import fit

MODES=("original","root_only","leg_only","joint")
BOUNDS=(.04,.08)
SIDES=("L","R")
ACTORS=("AsterOriginal","JuniperOriginal")

def require(ok,code):
    if not ok:raise ValueError(code)

def capxy(x,limit):
    require(type(limit) in (float,int) and math.isfinite(limit) and 0<limit<=.08,"CORRECTION_BUDGET")
    require(isinstance(x,(list,tuple)) and len(x)==2 and all(type(t) in (int,float) and math.isfinite(t) and abs(t)<100 for t in x),"NONFINITE_CORRECTION")
    n=math.hypot(*x)
    f=min(1.,limit/n) if n else 1.
    return (float(x[0]*f),float(x[1]*f))

def first_window(indices,size=6,min_index=180,max_index=353):
    require(isinstance(indices,list) and size>=4 and size<=12 and all(type(i) is int and 0<=i<359 for i in indices),"BAD_CANDIDATE_INDICES")
    arr=set(indices)
    for i in indices:
        if i>=min_index and i<=max_index and all(i+j in arr for j in range(size-1)):
            return i
    return None

def actor_plan(actor):
    require(actor.get("name") in ACTORS and set(actor.get("sides",{}))==set(SIDES),"ACTOR_SIDES")
    left=actor["sides"]["L"]
    require(len(left)==360 and len(actor["sides"]["R"])==360,"TRACE_LENGTH")
    roots_src=[source_xy(r["source_hip"]) for r in left]
    roots_dst=[xy(r["target_hip"]) for r in left]
    model=fit(roots_src[:180],roots_dst[:180])
    paths={}
    for side in SIDES:
        rows=actor["sides"][side]
        paths[side]=candidate([source_xy(r["source_hip"]) for r in rows],
                              [source_xy(r["source_ankle"]) for r in rows],
                              [xy(r["target_hip"]) for r in rows],
                              [xy(r["target_foot"]) for r in rows],model)
    starts={s:first_window(source_eligible(actor["sides"][s])) for s in SIDES}
    return model,paths,starts

def corrections(actor,paths,n,mode,bound):
    require(mode in MODES and n>=180 and n<360,"MODE_OR_TIMEBASE")
    require(all(s in paths and set(paths[s])==set(MODES) for s in SIDES),"FACTORIAL_PATHS")
    root_xy=xy(actor["sides"]["L"][n]["target_hip"])
    foot_xy={s:xy(actor["sides"][s][n]["target_foot"]) for s in SIDES}
    # Root desired from source projection is the same for both sides; derive it
    # from root-only prediction minus actual target foot, avoiding hidden use
    # of heldout target data to fit root.
    root_demand=tuple(paths["L"]["root_only"][n][k]-foot_xy["L"][k] for k in range(2))
    root_demand_r=tuple(paths["R"]["root_only"][n][k]-foot_xy["R"][k] for k in range(2))
    require(math.dist(root_demand,root_demand_r)<1e-5,"SOURCE_ROOT_NOT_SHARED")
    if mode not in ("root_only","joint"):root_demand=(0.,0.)
    root=capxy(root_demand,bound)
    legs={}
    for side in SIDES:
        if mode in ("leg_only","joint"):
            wanted=paths[side][mode][n]
            # Desired offset relative to SOURCE foot HEAD with any actually
            # bounded root shift; do not spend a fictional unlimited root.
            demand=(wanted[0]-foot_xy[side][0]-root[0],wanted[1]-foot_xy[side][1]-root[1])
            leg=capxy(demand,bound)
        else:
            demand=(0.,0.);leg=(0.,0.)
        legs[side]={"demand_xy_m":list(demand),"delta_xy_m":list(leg),"demand_norm_m":round(math.hypot(*demand),6)}
    return {"mode":mode,"bound_m":bound,"root_demand_xy_m":list(root_demand),
            "root_delta_xy_m":list(root),"root_demand_norm_m":round(math.hypot(*root_demand),6),
            "leg":legs,"target_source_t_s":n/60,"target_source_index":n,
            "source_physical_plant_proven":False}

def independent_plan(p):
    require(p.get("mode") in MODES and p.get("bound_m") in BOUNDS,"BAD_PLAN_CONFIG")
    root=p["root_delta_xy_m"]
    require(math.hypot(*root)<=p["bound_m"]+1e-7,"ROOT_BUDGET_EXCEEDED")
    require(set(p.get("leg",{}))==set(SIDES),"MISSING_LEG")
    for side in SIDES:
        d=p["leg"][side]["delta_xy_m"]
        require(math.hypot(*d)<=p["bound_m"]+1e-7,"LEG_BUDGET_EXCEEDED")
    require(p.get("source_physical_plant_proven") is False,"FORGED_CONTACT")
    return True
