"""Source-only controlled reversible Capture Rest/Armature modifier order A/B.

Measure true original skinned source card centerline agreement at all 48
frames, plus attached follicle root errors and candidate ray-contact warnings.
A better rigid control is a research direction, NOT physical material approval.
"""
import hashlib
import json
import math
from pony52_actual_surface_native import evaluate_pair,REGION_TARGETS,point,d

SCHEMA="equine.pony52.rest_order_ab.v1"
ORDERS=("armature_then_capture","capture_then_armature")
def pct(values,p):
    v=sorted(values)
    if not v or any(not math.isfinite(x) or x<0 for x in v):
        raise ValueError("invalid measured distribution")
    return round(v[math.ceil(len(v)*p)-1],8)
def analyze(source,baseline_physics,baseline_animation,candidate_physics,candidate_animation):
    variants=[(ORDERS[0],baseline_physics,baseline_animation),
              (ORDERS[1],candidate_physics,candidate_animation)]
    source_index={g["card_id"]:g for g in source["guides"]}
    comparisons={}
    for order,physics,animation in variants:
        for mode,receipt in (("physics",physics),("animation",animation)):
            if receipt.get("rest_capture_order")!=order or receipt.get("mode")!=mode:
                raise ValueError("invalid experimental variant or swapped mode")
            if receipt.get("source_rest_order_experiment") is not True:
                raise ValueError("not a native rest-order experiment")
            ai=receipt.get("armature_index")
            ci=receipt.get("rest_capture_index")
            if (type(ai) is not int or type(ci) is not int or
                ai<0 or ci<0 or ai==ci or ai>64 or ci>64 or
                (ai<ci)!=(order=="armature_then_capture")):
                raise ValueError("native modifier stack index/order not observed")
            if receipt.get("source_blend_sha256")!=source.get("source_blend_sha256"):
                raise ValueError("source original .blend mismatch")
        quality=evaluate_pair(source,physics,animation)
        rigid_errors={r:[] for r in REGION_TARGETS}
        root_errors={r:[] for r in REGION_TARGETS}
        for fi,frame in enumerate(animation["frames"]):
            for row in frame["guides"]:
                id=row["card_id"];prior=source_index[id]["samples"][fi]
                src=[prior["tip_m"][k]-prior["root_m"][k] for k in range(3)]
                rel=point(row["tip_minus_root_m"])
                rigid_errors[row["region"]].append(d(src,rel))
        for mode,receipt in (("physics",physics),("animation",animation)):
            for frame in receipt["frames"]:
                for row in frame["guides"]:
                    root_errors[row["region"]].append(float(row["root_error_m"]))
        comparisons[order]={
            "rigid_vs_original_p95_m":{k:pct(v,.95) for k,v in rigid_errors.items()},
            "rigid_vs_original_max_m":{k:round(max(v),8) for k,v in rigid_errors.items()},
            "rigid_vs_original_p95_all_m":pct([x for a in rigid_errors.values() for x in a],.95),
            "root_tracking_max_m":{k:round(max(v),8) for k,v in root_errors.items()},
            "ray_hit_candidates_by_region":quality["potential_body_segment_ray_hits_by_region"],
            "max_same_frame_secondary_motion_m_by_region":quality["max_same_frame_physics_minus_animation_relative_tip_m_by_region"],
            "min_body_unsigned_distance_m_by_region":quality["min_tip_body_unsigned_distance_m_by_region"],
            "physics_runtime_s":float(physics.get("elapsed_s",0)),
            "animation_runtime_s":float(animation.get("elapsed_s",0)),
        }
    base=comparisons[ORDERS[0]]
    trial=comparisons[ORDERS[1]]
    improvement=base["rigid_vs_original_p95_all_m"]-trial["rigid_vs_original_p95_all_m"]
    relative=improvement/max(base["rigid_vs_original_p95_all_m"],1e-10)
    no_worse_roots=all(trial["root_tracking_max_m"][r]<=base["root_tracking_max_m"][r]+.0005 for r in REGION_TARGETS)
    no_increased_rays=all(trial["ray_hit_candidates_by_region"][r]<=base["ray_hit_candidates_by_region"][r] for r in REGION_TARGETS)
    no_worse_region=all(trial["rigid_vs_original_p95_m"][r]<=base["rigid_vs_original_p95_m"][r]+.001 for r in REGION_TARGETS)
    candidate_better=relative>=.05 and no_worse_roots and no_increased_rays and no_worse_region
    verdict="POTENTIAL_SOURCE_RIGID_FIDELITY_IMPROVEMENT_NEEDS_SCIENCE" if candidate_better else "REJECT_CANDIDATE_KEEP_EXISTING_ORDER"
    return {"schema":SCHEMA,
        "source_blend_sha256":source["source_blend_sha256"],
        "source_capsule_sha256":baseline_physics["source_capsule_sha256"],
        "candidate_order":ORDERS[1],"existing_order":ORDERS[0],
        "frames":48,"guides":6,"comparisons":comparisons,
        "rigid_p95_absolute_improvement_m":round(improvement,8),
        "rigid_p95_relative_improvement_fraction":round(relative,8),
        "no_worse_follicle_attachment":no_worse_roots,
        "no_increased_ray_candidates":no_increased_rays,
        "no_worse_regional_rigid_fidelity":no_worse_region,
        "candidate_research_verdict":verdict,
        "original_pony_body_collision_clearance":False,
        "material_and_visual":"UNQUALIFIED",
        "production_groom_pin_changed":False,
        "scientific_hold":"KEEP","release_or_CPE_admission":False}
def main():
    import pathlib,sys
    if len(sys.argv)!=7:
        raise SystemExit("usage: capture_order_ab.py capsule base_physics base_anim trial_physics trial_anim output")
    paths=[pathlib.Path(x) for x in sys.argv[1:]]
    inputs=[json.loads(p.read_text()) for p in paths[:-1]]
    r=analyze(*inputs)
    if paths[-1].exists():raise ValueError("refuse overwrite scientific witness")
    paths[-1].write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("ORIGINAL_GROOM_REST_MODIFIER_ORDER_AB_SCIENCE_HELD",json.dumps(r,sort_keys=True))
if __name__=="__main__":main()
