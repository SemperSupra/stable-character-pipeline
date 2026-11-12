"""R014 choose safe GLB actor-export strategy from measured animated parity.
This qualifies *interchange metrics*, never character realism or full rig behavior.
"""
import argparse,json
from pathlib import Path

THRESHOLDS={"rms_m":0.001,"p95_m":0.00005,"max_m":0.01}

def actor_result(data,sex):
    label=sex+"_frame_12"
    metric=data["measurements"][label]["actual_to_native"]
    pose=data["bone_pose_diagnostics"][label]["reimported"]
    reasons=[k+"_above_threshold" for k,limit in THRESHOLDS.items()
             if metric[k]>limit]
    if pose["active_action"] is None:
        reasons.append("missing_active_rig_animation")
    return {"status":"PASS_INTERCHANGE_THRESHOLD_ONLY" if not reasons else "FAIL_INTERCHANGE",
            "metrics":metric,"active_action":pose["active_action"],"reasons":reasons}

def assess(combined,female,male):
    results={"isolated_female":actor_result(female,"female"),
             "isolated_male":actor_result(male,"male"),
             "combined_female":actor_result(combined,"female"),
             "combined_male":actor_result(combined,"male")}
    isolated=all(results["isolated_"+s]["status"]=="PASS_INTERCHANGE_THRESHOLD_ONLY"
                 for s in ("female","male"))
    combined_ok=all(results["combined_"+s]["status"]=="PASS_INTERCHANGE_THRESHOLD_ONLY"
                    for s in ("female","male"))
    return {"status":"PASS_ISOLATED_EXPORT_STRUCTURAL_ONLY" if isolated else "HOLD_ISOLATED_EXPORT",
            "approved_research_export_shape":"one actor per GLB" if isolated else "none",
            "combined_export_status":"PASS_INTERCHANGE_THRESHOLD_ONLY" if combined_ok else "REJECTED_IN_THIS_RUN",
            "measurements":results,"thresholds":THRESHOLDS,
            "limits":["No local contact/volume or anatomical realism tests",
                      "Maximum residual differences require regional visual review",
                      "Not a proof that multi-actor GLB can never be made to work",
                      "Native .blend retains both actor models; export paths remain isolated"]}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--combined",type=Path,required=True)
    p.add_argument("--female",type=Path,required=True)
    p.add_argument("--male",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    r=assess(*(json.loads(x.read_text()) for x in (a.combined,a.female,a.male)))
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("R014_ACTOR_EXPORT_POLICY",json.dumps({k:v for k,v in r.items() if k!="measurements"},sort_keys=True))
    raise SystemExit(r["status"]!="PASS_ISOLATED_EXPORT_STRUCTURAL_ONLY")
