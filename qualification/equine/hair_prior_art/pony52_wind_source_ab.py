"""Controlled source-exact 5.2 original wind-morph A/B.

The original 4.5 source capsule deliberately DISABLES the nine baked wind
morphs when measuring skin-only motion. Compare 5.2 attached-curve rigid and
physics outputs when the reopened original source is animated normally vs
the same source with *only* its wind morph weights held at zero in memory.
Do not assert a cause until native source-key readback and motion are checked.
"""
import json
import math
from pony52_actual_surface_native import evaluate_pair,REGION_TARGETS,point,d
from pony_source_trajectory import classify as source_gate

SCHEMA="equine.pony52.source_wind_morph_ab.v1"
def percentile(values,p):
    v=sorted(values)
    if not v or any(not math.isfinite(float(x)) or float(x)<0 for x in v):
        raise ValueError("invalid source-to-rigid motion")
    return round(v[math.ceil(len(v)*p)-1],8)
def quality(source,baseline_physics,baseline_animation,trial_physics,trial_animation):
    contract=source_gate(source)
    results={}
    for name,physics,animation in (("animated",baseline_physics,baseline_animation),
                                   ("disabled",trial_physics,trial_animation)):
        verified=evaluate_pair(source,physics,animation)
        for mode,data in (("physics",physics),("animation",animation)):
            if data.get("source_wind_morph_mode")!=name or data.get("source_wind_morphs_detected")!=9:
                raise ValueError("native wind A/B source configuration not observed")
            if data.get("wind_keys_disabled_in_memory_only") is not (name=="disabled"):
                raise ValueError("source wind key mutation flag malformed")
            if data.get("source_blend_sha256")!=source["source_blend_sha256"] or data.get("source_capsule_sha256")!=contract["source_capsule_sha256"]:
                raise ValueError("source motion SHA mismatched")
            raw,applied=data.get("source_wind_max_raw_activity_per_frame"),data.get("source_wind_max_activity_per_frame")
            if type(raw)!=list or type(applied)!=list or len(raw)!=48 or len(applied)!=48:
                raise ValueError("missing per-frame source wind policy readback")
            for r,a in zip(raw,applied):
                if type(r) not in (float,int) or type(a) not in (float,int) or not math.isfinite(r) or not math.isfinite(a) or not 0<=r<=1.00001 or not 0<=a<=1.00001:
                    raise ValueError("invalid/missing native wind weights")
                if (name=="disabled" and abs(a)>1e-7) or (name=="animated" and abs(a-r)>1e-7):
                    raise ValueError("native wind control did not apply as requested")
            if type(data.get("source_wind_f1_raw_before_override")) not in (float,int) or not math.isfinite(data["source_wind_f1_raw_before_override"]):
                raise ValueError("invalid initial source wind readback")
        # Raw animation of the original source is the independent
        # treatment variable; physics/rigid runs must start at same keys.
        for field in ("source_wind_max_raw_activity_per_frame","source_wind_max_activity_per_frame"):
            p=physics[field];a=animation[field]
            if max(abs(x-y) for x,y in zip(p,a))>1e-5:
                raise ValueError("Physics and Animation did not see the same wind treatment")
        all_regions={name:[] for name in REGION_TARGETS}
        max_root={name:0. for name in REGION_TARGETS}
        by_id={g["card_id"]:g for g in source["guides"]}
        for index,frame in enumerate(animation["frames"]):
            for observation in frame["guides"]:
                card=observation["card_id"];g=by_id[card]
                rest=g["samples"][index]
                original=tuple(rest["tip_m"][k]-rest["root_m"][k] for k in range(3))
                actual=point(observation["tip_minus_root_m"])
                all_regions[g["region"]].append(d(actual,original))
                max_root[g["region"]]=max(max_root[g["region"]],float(observation["root_error_m"]))
        results[name]={
            "per_region_rigid_vs_skin_only_source_max_m":{k:round(max(v),8) for k,v in all_regions.items()},
            "per_region_rigid_vs_skin_only_source_p95_m":{k:percentile(v,.95) for k,v in all_regions.items()},
            "rigid_vs_skin_only_source_all_p95_m":percentile([v for group in all_regions.values() for v in group],.95),
            "max_root_error_m_by_region":{k:round(v,8) for k,v in max_root.items()},
            "potential_body_segment_ray_hits_by_region":verified["potential_body_segment_ray_hits_by_region"],
            "physics_vs_animation_tip_m_by_region":verified["max_same_frame_physics_minus_animation_relative_tip_m_by_region"],
            "maximum_source_raw_wind_activity":max(animation["source_wind_max_raw_activity_per_frame"]),
            "maximum_source_effective_wind_activity":max(animation["source_wind_max_activity_per_frame"]),
        }
    raw_base=baseline_animation["source_wind_max_raw_activity_per_frame"]
    raw_trial=trial_animation["source_wind_max_raw_activity_per_frame"]
    same_raw=max(abs(a-b) for a,b in zip(raw_base,raw_trial))<=1e-5
    source_excited=max(raw_base)>.01
    baseline=results["animated"];trial=results["disabled"]
    diff=baseline["rigid_vs_skin_only_source_all_p95_m"]-trial["rigid_vs_skin_only_source_all_p95_m"]
    improvement_fraction=diff/max(baseline["rigid_vs_skin_only_source_all_p95_m"],1e-10)
    root_ok=all(trial["max_root_error_m_by_region"][r]<=baseline["max_root_error_m_by_region"][r]+.0005 for r in REGION_TARGETS)
    body_ok=all(trial["potential_body_segment_ray_hits_by_region"][r]<=baseline["potential_body_segment_ray_hits_by_region"][r] for r in REGION_TARGETS)
    region_ok=all(trial["per_region_rigid_vs_skin_only_source_p95_m"][r]<=baseline["per_region_rigid_vs_skin_only_source_p95_m"][r]+.001 for r in REGION_TARGETS)
    # Source-frame admission is SEPARATE from contact-science admission.
    # Body ray-count increases cannot invalidate a correctly matched
    # original 4.5 source-state but DO block promoting the native 5.2 hair.
    source_state_corrected=(same_raw and source_excited and root_ok and region_ok
        and improvement_fraction>=.95 and
        trial["rigid_vs_skin_only_source_all_p95_m"]<=.0001)
    delta_hits={r:trial["potential_body_segment_ray_hits_by_region"][r]-
                baseline["potential_body_segment_ray_hits_by_region"][r] for r in REGION_TARGETS}
    if not same_raw:
        verdict="INVALID_SOURCE_EXCITATION_DIFFERENT_NATIVE_INPUTS"
    elif not source_excited:
        verdict="INCONCLUSIVE_NO_SOURCE_WIND_ACTIVITY"
    elif source_state_corrected and body_ok:
        verdict="SOURCE_WIND_MORPH_CONFOUND_BOUNDED_CONFIRMED_NO_NEW_RAY_CANDIDATES"
    elif source_state_corrected:
        verdict="SOURCE_WIND_MORPH_CONFOUND_BOUNDED_CONFIRMED_COLLISION_HOLD"
    elif improvement_fraction>=.1 and root_ok and region_ok and body_ok:
        verdict="PARTIAL_MORPH_STATE_IMPROVEMENT_SOURCE_NOT_CALIBRATED"
    else:
        verdict="NO_ELIGIBLE_IMPROVEMENT_KEEP_ORIGINAL_WORKCELL"
    return {"schema":SCHEMA,
        "source_blend_sha256":source["source_blend_sha256"],
        "source_capsule_sha256":contract["source_capsule_sha256"],
        "frames":48,"guides":6,
        "rigid_52_wind_source_variants":results,
        "source_wind_control_raw_input_equivalent":same_raw,
        "original_4_5_source_wind_morphs_actively_animated":source_excited,
        "rigid_p95_absolute_improvement_m":round(diff,8),
        "rigid_p95_relative_improvement_fraction":round(improvement_fraction,8),
        "source_root_tracking_not_worse":root_ok,
        "body_ray_candidates_not_increased":body_ok,
        "body_ray_candidate_delta_by_region":delta_hits,
        "source_wind_confound_corrected_to_skin_only_reference":source_state_corrected,
        "source_consistency_separate_from_collision_admission":True,
        "regional_rigid_source_errors_not_worse":region_ok,
        "verdict":verdict,
        "original_source_mutated_on_disk":False,
        "blender_52_production_upgrade_approved":False,
        "body_fur_contact_material_visual":"UNKNOWN",
        "scientific_hold":"KEEP","merge_release_CPE":False}
def main():
    import sys
    from pathlib import Path
    if len(sys.argv)!=7:
        raise SystemExit("usage: pony52_wind_source_ab.py capsule baseline_physics baseline_animation trial_physics trial_animation output")
    source,bp,ba,tp,ta=[json.loads(Path(p).read_text()) for p in sys.argv[1:-1]]
    result=quality(source,bp,ba,tp,ta)
    out=Path(sys.argv[-1])
    if out.exists():raise ValueError("refuse overwrite witness")
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("ORIGINAL_SKIN_ONLY_SOURCE_VS_52_WIND_MORPH_AB",json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
