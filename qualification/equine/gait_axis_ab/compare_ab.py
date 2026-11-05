"""Bounded native A/B proof: source-cold-start corrected hinge must not falsely promote science."""
import hashlib,json,sys
from pathlib import Path

def main(before,after,out):
    a=json.loads(Path(before).read_text())
    b=json.loads(Path(after).read_text())
    assert a["schema"]==b["schema"]=="equine.foot.science.v1"
    assert a["frames"]==b["frames"]==48 and set(a["feet"])==set(b["feet"])
    report={"schema":"equine.hinge.ab.v1",
        "source":"original synthetic Shetland PR #294 local-Y twist baseline",
        "corrective":"same source local-X hinge only",
        "before_verdict":a["scientific_verdict"],
        "after_verdict":b["scientific_verdict"],
        "before_max_clearance_m":max(v["max_clearance_m"] for v in a["feet"].values()),
        "after_max_clearance_m":max(v["max_clearance_m"] for v in b["feet"].values()),
        "before_failing_hooves":a["hooves_without_minimum_swing_clearance"],
        "after_failing_hooves":b["hooves_without_minimum_swing_clearance"],
        "per_foot":{},"native_validation":"RENDERED_SOURCE_A_B_NOT_BIOLOGICAL_ACCEPTANCE"}
    for foot in sorted(a["feet"]):
        v0=a["feet"][foot];v1=b["feet"][foot]
        report["per_foot"][foot]={"before_clearance_m":v0["max_clearance_m"],
                                 "after_clearance_m":v1["max_clearance_m"],
                                 "clearance_delta_m":round(v1["max_clearance_m"]-v0["max_clearance_m"],6),
                                 "after_skate_pairs":v1["skate_pairs_over_3cm"],
                                 "after_penetration_m":v1["max_ground_penetration_m"]}
    if b["hooves_without_minimum_swing_clearance"]==0:
        outcome="SCREEN_SUPPORTS_AXIS_CHANGE_BUT_TRUE_GAIT_UNKNOWN"
    elif b["hooves_without_minimum_swing_clearance"]<a["hooves_without_minimum_swing_clearance"]:
        outcome="PARTIAL_AXIS_CHANGE_NOT_ACCEPTED"
    else:
        outcome="AXIS_HYPOTHESIS_NOT_YET_SUPPORTED"
    report["scientific_outcome"]=outcome
    report["input_sha256"]={"before":hashlib.sha256(Path(before).read_bytes()).hexdigest(),
        "after":hashlib.sha256(Path(after).read_bytes()).hexdigest()}
    Path(out).write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":
    assert len(sys.argv)==4
    main(*sys.argv[1:])
