"""N03D-AF shoe plantar cohort geometry and fail-closed independent trace critic.

An actual foot->toe BONE-head projection provides a longitudinal *proxy*, not
true anatomical heel, metatarsal ball, pressure sensor or accepted contact.
Never label geometry/velocity as actual gait acceptance without source proof.
"""
import math
from statistics import median

ACTORS=("AsterOriginal","JuniperOriginal")
SIDES=("L","R")
STARTS=(24,48)

def require(ok,code):
    if not ok:raise ValueError(code)

def finite(x):
    return type(x) in (int,float) and math.isfinite(x) and abs(x)<100

def location(p):
    require(isinstance(p,(list,tuple)) and len(p)==3 and all(finite(x) for x in p),"INVALID_WORLD_VERTEX")
    return tuple(float(x) for x in p)

def project(points, ids, forward, bottom_fraction=.25, end_fraction=.2):
    """Source-preserving fixed material IDs, selected ONCE at calibration time."""
    require(isinstance(points,list) and len(points)>100 and isinstance(ids,list) and len(ids)>30,"COHORT_SIZE")
    require(len(set(ids))==len(ids) and all(type(i) is int and 0<=i<len(points) for i in ids),"VERTEX_ID_DUPLICATE_OR_RANGE")
    require(isinstance(forward,(list,tuple)) and len(forward)==2 and all(finite(x) for x in forward),"FOOT_FORWARD_INVALID")
    n=math.hypot(*forward)
    require(n>.02,"FOOT_AXIS_TOO_SHORT")
    require(.05<=bottom_fraction<=.5 and .05<=end_fraction<=.4,"SELECTION_PARAM")
    uv=(forward[0]/n,forward[1]/n)
    candidates=sorted(ids,key=lambda i:(location(points[i])[2],i))
    sole=candidates[:max(24,math.ceil(len(ids)*bottom_fraction))]
    ordered=sorted(sole,key=lambda i:(points[i][0]*uv[0]+points[i][1]*uv[1],i))
    k=max(8,math.ceil(len(ordered)*end_fraction))
    heel,fore=ordered[:k],ordered[-k:]
    require(not set(heel)&set(fore),"HEELED_COHORT_OVERLAP")
    def scalar(c):
        return sum(points[i][0]*uv[0]+points[i][1]*uv[1] for i in c)/len(c)
    gap=scalar(fore)-scalar(heel)
    require(gap>.025,"LONGITUDINAL_EXTENT_UNRESOLVED")
    return {"heel_proxy_vertex_ids":sorted(heel),"toe_proxy_vertex_ids":sorted(fore),
            "source_sole_candidate_count":len(sole),"proxy_heel_to_toe_separation_m":round(gap,6),
            "forward_xy_unit":list(uv),"actual_anatomical_heel_ball_toe_verified":False}

def snapshot(points,ids):
    require(isinstance(ids,list) and len(ids)>=8,"COHORT_EMPTY")
    selection=[location(points[i]) for i in ids]
    return {"xy_m":[round(sum(p[k] for p in selection)/len(selection),9) for k in (0,1)],
            "min_z_m":round(min(p[2] for p in selection),9)}

def metric(samples,hz=24):
    require(len(samples)==12 and hz==24,"CLOCK_OR_WINDOW")
    for j,v in enumerate(samples):
        require(isinstance(v,dict) and set(v)=={"t_s","xy_m","min_z_m"} and
                finite(v["t_s"]) and abs(v["t_s"]-samples[0]["t_s"]-j/hz)<1e-7 and
                len(v["xy_m"])==2 and all(finite(x) for x in v["xy_m"]) and finite(v["min_z_m"]),
                "SAMPLE_FORMAT")
    speeds=[]
    near=[]
    for i in range(1,len(samples)):
        a,b=samples[i-1],samples[i]
        vel=math.dist(a["xy_m"],b["xy_m"])*hz
        speeds.append(vel)
        if abs(a["min_z_m"])<=.012 and abs(b["min_z_m"])<=.012:near.append(vel)
    return {"p50_all_mps":round(median(speeds),6),
            "max_all_mps":round(max(speeds),6),
            "p50_near_mps":round(median(near),6) if near else None,
            "near_ground_adjacent_pairs":len(near),
            "max_penetration_m":round(max(0,-min(x["min_z_m"] for x in samples)),6)}

def assess(doc):
    require(doc.get("schema")=="scp.n03d-af.real-shoe-plantar-proxy.v1" and
            doc.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
            doc.get("source_scene_unchanged") is True and
            doc.get("actual_anatomy_accepted") is False and
            doc.get("mvp_accepted") is False,"SOURCE_OR_FALSE_ACCEPTANCE")
    records=doc.get("windows")
    require(isinstance(records,list) and len(records)==8,"WINDOW_FACTORIAL_COUNT")
    seen=set(); results=[]
    for w in records:
        key=(w.get("actor"),w.get("side"),w.get("start_24hz"))
        require(key[0] in ACTORS and key[1] in SIDES and key[2] in STARTS and key not in seen,"DUPLICATE_OR_INVALID_WINDOW")
        seen.add(key)
        cohort=w.get("cohort")
        require(cohort.get("actual_anatomical_heel_ball_toe_verified") is False and
                cohort.get("proxy_heel_to_toe_separation_m",0)>.025 and
                set(cohort["heel_proxy_vertex_ids"]).isdisjoint(cohort["toe_proxy_vertex_ids"]),
                "COHORT_UNQUALIFIED")
        checks={}
        for label in ("heel","toe"):
            ids=cohort[label+"_proxy_vertex_ids"]
            require(isinstance(ids,list) and len(ids)>=8 and len(ids)==len(set(ids)),"IDS_INVALID")
            checks[label]=metric(w[label+"_samples"])
            require(abs(w[label+"_samples"][0]["t_s"]-key[2]/24)<1e-7,"SAMPLE_WINDOW_DRIFT")
        results.append({"actor":key[0],"side":key[1],"start":key[2],"metrics":checks,
                        "anatomical_label_status":"PROXY_ONLY","contact_status":"UNKNOWN"})
    require(seen=={(a,s,t) for a in ACTORS for s in SIDES for t in STARTS},"INCOMPLETE_FACTORIAL")
    return {"schema":"scp.n03d-af.independent-sole-cohort-critic.v1","status":"HOLD",
            "anatomical_heel_ball_toe_verified":False,"actual_contact_proven":False,
            "mvp_accepted":False,"windows":results}
