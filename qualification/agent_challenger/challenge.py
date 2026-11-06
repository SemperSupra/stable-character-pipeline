#!/usr/bin/env python3
"""Independent rule-baseline challenger of source-hashed ACTUAL native pixel measurements.

Strict read-only bounded decision on archived original-synthetic #317 image
observations. An LLM/VLM is NOT executed; does not classify living animals,
photographs, protected identities, physical gait, or authorize model promotion.
"""
import argparse
import json
import math
from pathlib import Path

VIEWS=("side","oblique")
FRAMES=(12,24)
CANDIDATES=("m060","zero","p060")
HEX=set("0123456789abcdef")

class EvidenceError(ValueError):
    pass

def require(pred,why):
    if not pred:raise EvidenceError(why)

def digest(v):
    return isinstance(v,str) and len(v)==64 and set(v)<=HEX

def finite_fraction(x):
    return type(x) in (int,float) and math.isfinite(x) and 0<=x<=1

def challenge(source):
    require(isinstance(source,dict) and source.get("schema")=="scp.native_multiview_neckfit.v1","wrong schema")
    require(source.get("reference_kind")=="SYNTHETIC_SELF_RENDER" and
            source.get("external_photo_fit")=="NOT_RUN" and
            source.get("reasoning_model_inference")=="NOT_RUN" and
            source.get("physical_anatomy")=="UNKNOWN","untrusted science claims")
    require(source.get("disposition")=="ENGINEERING_MULTI_VIEW_FIT_PASS_SCIENCE_UNKNOWN","untrusted disposition")
    require(digest(source.get("model_source_sha256")),"missing exact model SHA")
    require(source.get("camera_count")==2 and source.get("frames")==[12,24],"wrong sample basis")
    require(source.get("candidate_angles_radians")=={"m060":-.6,"zero":0.,"p060":.6},"wrong candidate bounds")
    rows=source.get("per_view_frame")
    require(isinstance(rows,list) and len(rows)==12,"missing 12 actual measurement rows")
    metrics={}
    for row in rows:
        require(isinstance(row,dict),"invalid measurement")
        key=(row.get("camera"),row.get("frame"),row.get("candidate"))
        require(key[0] in VIEWS and type(key[1]) is int and key[1] in FRAMES and
                key[2] in CANDIDATES and key not in metrics,"duplicate or unexpected candidate")
        require(digest(row.get("reference_sha256")),"missing reference image hash")
        require(finite_fraction(row.get("baseline_iou")) and
                finite_fraction(row.get("candidate_iou")),"invalid pixel score")
        metrics[key]=row
    require(len(metrics)==len(VIEWS)*len(FRAMES)*len(CANDIDATES),"incomplete multiview matrix")
    for view in VIEWS:
        for frame in FRAMES:
            subset=[metrics[(view,frame,k)] for k in CANDIDATES]
            require(len({x["reference_sha256"] for x in subset})==1,"cross-candidate reference swap")
            require(max(x["baseline_iou"] for x in subset)-
                    min(x["baseline_iou"] for x in subset)<1e-12,"baseline swap or forged aggregate")
    observed={}
    for candidate in CANDIDATES:
        scores=[metrics[(v,f,candidate)]["candidate_iou"] for v in VIEWS for f in FRAMES]
        observed[candidate]=sum(scores)/len(scores)
    means=source.get("mean_iou_by_candidate")
    require(isinstance(means,dict) and set(means)==set(CANDIDATES),"wrong aggregate")
    require(all(finite_fraction(means[k]) and abs(means[k]-observed[k])<1e-10
                for k in CANDIDATES),"aggregate inconsistent with raw pixel observations")
    baseline=sum(metrics[(v,f,"zero")]["baseline_iou"] for v in VIEWS for f in FRAMES)/4
    require(finite_fraction(source.get("baseline_mean_iou")) and
            abs(baseline-source["baseline_mean_iou"])<1e-10,"forged baseline mean")
    require(source.get("best_candidate")==max(observed,key=observed.get),"untrusted winning candidate")
    require(finite_fraction(source.get("measured_gain")) and
            abs(source["measured_gain"]-(observed[source["best_candidate"]]-baseline))<1e-10,
            "forged reported optimizer gain")
    best=source["best_candidate"]
    diffs=[metrics[(v,f,best)]["candidate_iou"]-
           metrics[(v,f,best)]["baseline_iou"] for v in VIEWS for f in FRAMES]
    per_view={v:min(metrics[(v,f,best)]["candidate_iou"]-
                    metrics[(v,f,best)]["baseline_iou"] for f in FRAMES) for v in VIEWS}
    allow=all(d>1e-4 for d in diffs) and observed[best]-baseline>.005
    return {"schema":"scp.actor_challenger_independent_measurements.v1",
            "model_sha256":source["model_source_sha256"],
            "source_observations":12,"source_native_runs":1,
            "candidate_mean_iou":observed,
            "rule_baseline_mean_iou":baseline,
            "challenger_best":best,"minimum_view_frame_gain":min(diffs),
            "worst_gain_by_camera":per_view,"mean_gain":observed[best]-baseline,
            "decision":"RULE_ONLY_SYNTHETIC_IMPROVEMENT_OBSERVED" if allow
                  else "ABSTAIN_NO_CROSS_VIEW_IMPROVEMENT",
            "source": "IMMUTABLE_ARCHIVED_NATIVE_SYNTHETIC_2VIEW_2FRAME",
            "actual_reasoning_actor_inference":"NOT_RUN",
            "independent_external_photo":"NOT_RUN",
            "human_or_equine_anatomy":"UNKNOWN",
            "perceptual_image_quality":"NOT_QUALIFIED",
            "model_promotion":False,"merge_release_CPE_approval":False}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--output",required=True)
    v=ap.parse_args()
    data=json.loads(Path(v.input).read_bytes())
    receipt=challenge(data)
    Path(v.output).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("R009_ACTOR_POLICY_ABLATION_MEASURED_NOT_LLM",receipt["decision"],receipt["mean_gain"])
