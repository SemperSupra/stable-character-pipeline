"""N03D-AH bounded vertical root and bilateral foot-ground actuator proposal.

Source physical contact and anatomical sole not verified. The reference plane
is only the prior Blender world Z=0 diagnostic reference, not a measured floor.
"""
import math

MODES=("original","root_z","legs_z","joint_z")
BOUNDS=(.04,.08)
SIDES=("L","R")
ACTORS=("AsterOriginal","JuniperOriginal")

def require(x,code):
    if not x:raise ValueError(code)

def number(x):
    require(type(x) in (float,int) and math.isfinite(x) and abs(x)<100,"NONFINITE_MEASUREMENT")
    return float(x)

def proposal(min_z,bound,mode):
    """Root and two legs capped separately, with no positive lift if no penetration."""
    require(isinstance(min_z,dict) and set(min_z)==set(SIDES),"BILATERAL_SOURCE_REQUIRED")
    require(mode in MODES and bound in BOUNDS,"MODE_OR_BUDGET")
    deficit={s:max(0.,-number(min_z[s])) for s in SIDES}
    maximum=max(deficit.values())
    root=0.
    legs={s:0. for s in SIDES}
    if mode=="root_z":
        root=min(bound,maximum)
    elif mode=="legs_z":
        legs={s:min(bound,deficit[s]) for s in SIDES}
    elif mode=="joint_z":
        root=min(bound,maximum*.5)
        legs={s:min(bound,max(0.,deficit[s]-root)) for s in SIDES}
    return {"mode":mode,"bound_m":bound,"source_min_z_m":{s:number(min_z[s]) for s in SIDES},
            "root_z_m":root,"leg_z_m":legs,
            "predicted_residual_penetration_m":{s:max(0.,deficit[s]-root-legs[s]) for s in SIDES},
            "predicted_source_contact":False,"anatomical_support_proven":False}

def check_plan(plan):
    require(plan.get("mode") in MODES and plan.get("bound_m") in BOUNDS,"MODE_OR_BUDGET")
    bound=plan["bound_m"]
    z=number(plan["root_z_m"])
    require(0<=z<=bound+1e-9,"ROOT_BUDGET")
    require(set(plan.get("leg_z_m",{}))==set(SIDES),"BILATERAL_LEGS")
    for side in SIDES:
        v=number(plan["leg_z_m"][side])
        require(0<=v<=bound+1e-9,"LEG_BUDGET")
    if plan["mode"] in ("original","legs_z"):require(z==0,"FORBIDDEN_ROOT")
    if plan["mode"] in ("original","root_z"):require(all(plan["leg_z_m"][s]==0 for s in SIDES),"FORBIDDEN_LEG")
    require(plan.get("predicted_source_contact") is False and plan.get("anatomical_support_proven") is False,"FORGED_CONTACT")
    return True

def temporal_metrics(rows):
    """60Hz plan continuity test: velocity and acceleration, no smoothing claim."""
    require(isinstance(rows,list) and len(rows)==6,"SIX_FRAME_WINDOW")
    z=[]
    for i,r in enumerate(rows):
        require(r.get("source_index")==rows[0]["source_index"]+i,"NONCONTIGUOUS_TIMEBASE")
        z.append(number(r["plan"]["root_z_m"]))
    speed=[abs(z[i]-z[i-1])*60 for i in range(1,len(z))]
    accel=[abs(z[i]-2*z[i-1]+z[i-2])*3600 for i in range(2,len(z))]
    return {"max_root_speed_mps":round(max(speed),6),
            "max_root_acceleration_mps2":round(max(accel),6)}
