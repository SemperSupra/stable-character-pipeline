#!/usr/bin/env python3
"""Fail-closed 72f baseline-vs-ablation R009 observer comparison.

A garment-geometry tweak is merely a falsifiable experiment. Even zero
reported surface crossings + low strain does not prove good body clearance,
garment ease/fit, dynamic cloth, safe human anatomy or visual acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from fit_radial_ablations_v1 import CANDIDATES,SCHEMA as SOURCE_SCHEMA

SCHEMA="scp.r009.original_mage_72f_fit_comparison.v1"
ACTORS=("AsterOriginal","JuniperOriginal")
SLOTS=("style_top","style_bottom")
OBS_SCHEMA="scp.r009.adventure_body_surface_crossings.v1"


def load(path):
    raw=Path(path).read_bytes()
    record=json.loads(raw)
    if record.get("schema")!=OBS_SCHEMA or record.get("frame_count")!=72 or (
            record.get("garment_clearance_accepted") is not False) or (
            record.get("owner_rights_custody_merge_release_cpe_held") is not True):
        raise ValueError("FIT_COMPARATOR_UNKNOWN_OBSERVER_CONTRACT")
    if set(record.get("observations",{}))!=set(ACTORS):
        raise ValueError("FIT_COMPARATOR_ACTOR_SET")
    for actor in ACTORS:
        if set(record["observations"][actor])!=set(SLOTS):
            raise ValueError("FIT_COMPARATOR_SLOT_SET")
        for slot in SLOTS:
            o=record["observations"][actor][slot]
            if o.get("frames_checked")!=72 or len(o.get("per_frame",[]))!=72 or (
                    set(x.get("frame") for x in o["per_frame"])!=set(range(1,73))) or (
                    o.get("volumetric_containment")!="UNKNOWN_NOT_TESTED"):
                raise ValueError("FIT_COMPARATOR_INCOMPLETE_72F")
            if not all(type(o.get(k)) in (int,float) and math.isfinite(o[k])
                       for k in ("p99_edge_relative_strain",
                                 "total_body_garment_triangle_pairs")):
                raise ValueError("FIT_COMPARATOR_NONFINITE_OBSERVATIONS")
            count=sum(x["body_garment_surface_triangle_pairs"] for x in o["per_frame"])
            if count!=o["total_body_garment_triangle_pairs"] or (
                    count!=sum(o["crossing_height_bins_blender_world_z_m"].values())):
                raise ValueError("FIT_COMPARATOR_COUNT_OR_HEIGHT_BINS")
    return record,hashlib.sha256(raw).hexdigest()


def classify_proxy(old_pairs,new_pairs,old_strain,new_strain):
    """Track orthogonal surface vs edge-strain evidence; never disguise a mixed result.

    No weighted sum or score can turn these proxies into human cloth-fitness.
    A small extra p99 strain cannot erase a large crossing reduction, but
    neither can an intersection reduction excuse a strain regression.
    """
    if any(type(v) not in (int,float) or not math.isfinite(v)
           for v in (old_pairs,new_pairs,old_strain,new_strain)) or (
           min(old_pairs,new_pairs,old_strain,new_strain)<0) or (
           int(old_pairs)!=old_pairs or int(new_pairs)!=new_pairs):
        raise ValueError("FIT_COMPARATOR_BAD_PROXY_NUMBER")
    dx=new_pairs-old_pairs
    ds=new_strain-old_strain
    if abs(ds)<=1e-5:ds=0.
    crossing=("FEWER_PAIRS_UNQUALIFIED" if dx<0 else
              "MORE_PAIRS_FAIL_PROXY" if dx>0 else "UNCHANGED")
    strain=("LOWER_P99_STRAIN_UNQUALIFIED" if ds<0 else
            "HIGHER_P99_STRAIN" if ds>0 else "UNCHANGED")
    if dx==0 and ds==0:
        aggregate="NO_MEASURABLE_PROXY_CHANGE"
    elif dx<=0 and ds<=0:
        aggregate="DIRECTIONAL_PROXY_IMPROVEMENT_UNQUALIFIED"
    elif dx>=0 and ds>=0:
        aggregate="DIRECTIONAL_PROXY_REGRESSION"
    else:
        aggregate="MIXED_SURFACE_AND_STRAIN_EVIDENCE_UNQUALIFIED"
    return crossing,strain,aggregate


def compare(baseline_path,variants,source_receipts,out):
    path=Path(out).resolve()
    if path.exists():raise FileExistsError("FIT_COMPARATOR_REFUSE_OVERWRITE")
    baseline,base_sha=load(baseline_path)
    if set(variants)!=set(CANDIDATES) or set(source_receipts)!=set(CANDIDATES):
        raise ValueError("FIT_COMPARATOR_EXPECTS_EXACT_ABLATIONS")
    results={}
    for variant in sorted(CANDIDATES):
        record,receipt_sha=load(variants[variant])
        source_meta=json.loads(Path(source_receipts[variant]).read_text())
        if source_meta.get("schema")!=SOURCE_SCHEMA+".receipt" or (
                source_meta.get("variant")!=variant) or (
                source_meta.get("derived_sha256")!=record.get("source_sha256")) or (
                source_meta.get("source_sha256")!=baseline.get("source_sha256")) or (
                source_meta.get("garment_clearance_accepted") is not False):
            raise ValueError("FIT_COMPARATOR_SOURCE_OR_ABLATION_SHA_MISMATCH")
        rows={}
        for actor in ACTORS:
            rows[actor]={}
            for slot in SLOTS:
                before=baseline["observations"][actor][slot]
                after=record["observations"][actor][slot]
                old=before["total_body_garment_triangle_pairs"]
                new=after["total_body_garment_triangle_pairs"]
                strain0=before["p99_edge_relative_strain"]
                strain1=after["p99_edge_relative_strain"]
                crossing,edge_strain,disposition=classify_proxy(
                    old,new,strain0,strain1)
                rows[actor][slot]={
                    "surface_pair_disposition":crossing,
                    "edge_strain_disposition":edge_strain,
                    "baseline_surface_pairs":old,
                    "ablation_surface_pairs":new,
                    "delta_surface_pairs":new-old,
                    "baseline_p99_strain":strain0,
                    "ablation_p99_strain":strain1,
                    "delta_p99_strain":round(strain1-strain0,7),
                    "ablation_frames_with_surface_crossings":
                        after["frames_with_surface_crossings"],
                    "ablation_height_bins_blender_world_z_m":
                        after["crossing_height_bins_blender_world_z_m"],
                    "scientific_proxy_disposition":disposition,
                    "full_body_appearance_accepted":False,
                    "body_cloth_clearance_accepted":False,
                }
        results[variant]={
            "source_glb_sha256":record["source_sha256"],
            "source_receipt_sha256":hashlib.sha256(
                Path(source_receipts[variant]).read_bytes()).hexdigest(),
            "observer_receipt_sha256":receipt_sha,
            "by_actor":rows,
            "eligible_for_automatic_promotion":False,
        }
    out_record={
        "schema":SCHEMA,"baseline_72f_receipt_sha256":base_sha,
        "baseline_glb_sha256":baseline["source_sha256"],
        "source_kind":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
        "measure":"full_resolution_surface_crossings_plus_sampled_edge_strain_72f",
        "variants":results,
        "appearance_accepted":False,"garment_clearance_accepted":False,
        "physics_accepted":False,"owner_review_required":True,
        "merge_release_cpe_held":True,
    }
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf8") as f:
        f.write(json.dumps(out_record,indent=2,sort_keys=True)+"\n")
    return out_record


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--baseline",required=True)
    parser.add_argument("--experiment-root",required=True)
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    root=Path(a.experiment_root)
    result=compare(a.baseline,
        {v:root/(v+"-72f.json") for v in CANDIDATES},
        {v:root/(v+"-ablation.json") for v in CANDIDATES},
        a.out)
    print(json.dumps({
        "schema":result["schema"],
        "baseline_glb_sha256":result["baseline_glb_sha256"],
        "experimental_results":{
            k:{a:{s:r["scientific_proxy_disposition"]
                  for s,r in v["by_actor"][a].items()} for a in ACTORS}
            for k,v in result["variants"].items()},
        "garment_clearance_accepted":False
    },sort_keys=True))
