"""N03D-AE: 2x2 measured root/leg motion factor isolation, never native correction.

Train-only original BVH Hip to actual MPFB pelvis planar alignment,
then preserve initial source-relative target bone offset, compare original
vs mapped ROOT and LEG trajectory factors on the SAME heldout source-defined
slow-toe intervals. Predictions are not skinned shoes, constraints, contact,
or accepted motion. Identifies sufficiency/interaction hypotheses only.
"""
import hashlib,json,math,sys
from pathlib import Path
from statistics import median

HERE=Path(__file__).parent
sys.path.insert(0,str(HERE.parent/"n03d-ac-causal"))
from trace import assess as check_trace
sys.path.insert(0,str(HERE.parent/"n03d-s-planar-align"))
from planar import fit,transform

MODES=("original","root_only","leg_only","joint")
ACTORS=("AsterOriginal","JuniperOriginal")
SIDES=("L","R")

def require(ok, message):
    if not ok:raise ValueError(message)

def xy(a):
    return tuple(a[:2])

def source_xy(a):
    return (a[0],a[2])

def subtract(a,b):
    return (a[0]-b[0],a[1]-b[1])

def plus(a,b):
    return (a[0]+b[0],a[1]+b[1])

def speed(a,b):
    return math.dist(a,b)*60

def source_eligible(rows):
    # Select original *source* intervals independent of any target/optimizer.
    floor=min(r["source_toe"][1] for r in rows)
    indices=[]
    for i in range(1,len(rows)):
        a,b=rows[i-1],rows[i]
        if (a["source_toe"][1]-floor<=.02 and b["source_toe"][1]-floor<=.02 and
            math.dist(source_xy(a["source_toe"]),source_xy(b["source_toe"]))*60<=.08 and
            math.dist(source_xy(a["source_ankle"]),source_xy(b["source_ankle"]))*60<=.08):
            indices.append(i-1)
    return indices

def summarize(points, indices):
    values=[speed(points[i],points[i+1]) for i in indices]
    if not values:return {"p50_mps":None,"p95_mps":None,"max_mps":None}
    vals=sorted(values)
    return {"p50_mps":round(median(vals),6),
            "p95_mps":round(vals[min(len(vals)-1,math.ceil(.95*len(vals))-1)],6),
            "max_mps":round(max(vals),6)}

def candidate(source_hip,source_ankle,target_hip,target_foot,model):
    # Positional source->target Sim2 fit is TRAIN-only. Retains actual static
    # target foot-vs-pelvis offset, correcting *motion deltas*, not rest anatomy.
    mapped_h=transform(model,source_hip)
    mapped_a=transform(model,source_ankle)
    n=len(mapped_h)
    root_ref=[plus(target_hip[0],subtract(mapped_h[i],mapped_h[0])) for i in range(n)]
    leg0=subtract(target_foot[0],target_hip[0])
    mapped_local0=subtract(mapped_a[0],mapped_h[0])
    leg_ref=[plus(leg0,subtract(subtract(mapped_a[i],mapped_h[i]),mapped_local0)) for i in range(n)]
    original_local=[subtract(target_foot[i],target_hip[i]) for i in range(n)]
    return {
       "original":list(target_foot),
       "root_only":[plus(root_ref[i],original_local[i]) for i in range(n)],
       "leg_only":[plus(target_hip[i],leg_ref[i]) for i in range(n)],
       "joint":[plus(root_ref[i],leg_ref[i]) for i in range(n)],
    }

def evaluate(doc):
    # Strict independent full-60Hz provenance/shape check.
    pre=check_trace(doc)
    require(pre["status"]=="HOLD" and doc.get("mvp_accepted") is False, "FORGED_TRACE_ACCEPTANCE")
    pairs=[]
    for actor in doc["actors"]:
        name=actor["name"];require(name in ACTORS,"ACTOR")
        left=actor["sides"]["L"]
        roots_source=[source_xy(r["source_hip"]) for r in left]
        roots_target=[xy(r["target_hip"]) for r in left]
        fit_model=fit(roots_source[:180],roots_target[:180])
        # No use of 180..359 target positions in fitting; heldout only.
        per_side=[]
        for side in SIDES:
            rows=actor["sides"][side]
            sh=[source_xy(r["source_hip"]) for r in rows]
            sa=[source_xy(r["source_ankle"]) for r in rows]
            th=[xy(r["target_hip"]) for r in rows]
            tf=[xy(r["target_foot"]) for r in rows]
            hypotheses=candidate(sh,sa,th,tf,fit_model)
            eligible=source_eligible(rows)
            heldout=[i for i in eligible if i>=180 and i+1<360]
            train=[i for i in eligible if i<179]
            summaries={m:summarize(hypotheses[m],heldout) for m in MODES}
            per_side.append({
                "side":side,"training_candidate_intervals":len(train),
                "heldout_candidate_intervals":len(heldout),
                "source_original_ankle":summarize(sa,heldout),
                "ablation":summaries,
                "heldout_contact_truth_known":False,
                "root_and_leg_predicted_not_actuated":True,
                "anatomical_joint_mapping_verified":False,
                "diagnosis":"UNRESOLVED" if not heldout else "ABLATION_EVIDENCE_ONLY",
            })
        pairs.append({"actor":name,
                      "training_only_root_fit":{"scale":round(fit_model["scale"],9),
                                               "yaw_rad":round(math.atan2(fit_model["sin"],fit_model["cos"]),9)},
                      "sides":per_side})
    return {"schema":"scp.n03d-ae.source-root-leg-factorial-60hz.v1",
            "trace_sha256":hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest(),
            "source_class":"ORIGINAL_FICTIONAL_CC0","train_samples":[0,179],
            "heldout_samples":[180,359],
            "source_stance_proven":False,"native_actuation_performed":False,
            "mvp_accepted":False,"status":"HOLD","actors":pairs}

def independent(summary):
    require(summary.get("schema")=="scp.n03d-ae.source-root-leg-factorial-60hz.v1" and
            summary.get("status")=="HOLD" and summary.get("mvp_accepted") is False and
            summary.get("native_actuation_performed") is False and
            summary.get("source_stance_proven") is False and
            summary.get("train_samples")==[0,179] and summary.get("heldout_samples")==[180,359],
            "FORGED_ABLATION_PROMOTION")
    for a in summary.get("actors",[]):
        for side in a["sides"]:
            require(set(side["ablation"])==set(MODES),"INCOMPLETE_FACTORIAL")
            require(side["root_and_leg_predicted_not_actuated"] is True and side["heldout_contact_truth_known"] is False,
                    "FALSE_NATIVE_OR_CONTACT_PROOF")
            for metrics in side["ablation"].values():
                require(all(v is None or type(v) in (float,int) and math.isfinite(v) and v>=0 for v in metrics.values()),
                        "NONFINITE_METRICS")
    require(len(summary.get("actors",[]))==2,"ACTOR_COUNT")
    return summary["status"]

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--trace",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    source=json.loads(Path(a.trace).read_text())
    result=evaluate(source)
    independent(result)
    Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
    print("N03D_AE_REAL_SOURCE_ROOT_LEG_HELDOUT_FACTORIAL",json.dumps(result,sort_keys=True),flush=True)
