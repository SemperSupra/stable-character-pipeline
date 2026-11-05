"""Independent before/after 48-frame native hoof-sole gap and swing qualification.

The geometric probe measures sole minimum Z of actual GLB skinned hooves.
Negative result is a science verdict, not a runner infrastructure error.
"""
import json
import math
import sys
from pathlib import Path

FEET = ("front_L_hoof","front_R_hoof","hind_L_hoof","hind_R_hoof")
GROUND=-0.015

def measure(report):
    if report.get("schema")!="equine.foot.science.v1": raise ValueError("wrong source evidence schema")
    trajectories=report.get("evaluated_hoof_trajectories",{})
    if set(trajectories)!=set(FEET):raise ValueError("missing or extra feet")
    byfoot={}
    for name in FEET:
        samples=trajectories[name]
        if len(samples)!=48 or [p["frame"] for p in samples]!=list(range(1,49)):
            raise ValueError("not a true 48-frame continuous source trace")
        gap=[float(x["min_z"])-GROUND for x in samples]
        if any(not math.isfinite(x) for x in gap):
            raise ValueError("nonfinite measured gap")
        byfoot[name]={"min_gap_m":round(min(gap),6),"max_gap_m":round(max(gap),6),
                      "near_ground_frames":sum(-.005<=v<=.01 for v in gap),
                      "swing_frames_above_45mm":sum(v>.045 for v in gap)}
    return byfoot

def compare(before,after):
    a=measure(before);b=measure(after)
    passed_near=all(-.005<=v["min_gap_m"]<=.006 for v in b.values())
    preserved_swing=all(v["swing_frames_above_45mm"]>=4 for v in b.values())
    no_deep_penetration=all(v["min_gap_m"]>-.015 for v in b.values())
    gap_improved=sum(abs(v["min_gap_m"]) for v in b.values())<sum(abs(v["min_gap_m"]) for v in a.values())
    verdict="PROXY_HOOF_HEIGHT_IMPROVED_NOT_BIOLOGICAL_PASS" if (passed_near and preserved_swing and no_deep_penetration and gap_improved) else "PROXY_HOOF_CALIBRATION_NOT_ACCEPTED"
    return {"schema":"equine.shetland.contact_ab.v1",
            "source":"frozen original IK GLB measured 48 frames vs 18mm ankle target correction",
            "ground_plane_m":GROUND,"before":a,"after":b,
            "gates":{"improved_gap":gap_improved,"near_ground":passed_near,
                     "preserved_swing":preserved_swing,"no_deep_penetration":no_deep_penetration},
            "science_verdict":verdict,"biomechanics":"UNKNOWN","visual_approval":False}

def main():
    if len(sys.argv)!=4:raise SystemExit("usage: contact_ab.py before.json after.json out.json")
    before=json.loads(Path(sys.argv[1]).read_text())
    after=json.loads(Path(sys.argv[2]).read_text())
    receipt=compare(before,after)
    Path(sys.argv[3]).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"science_verdict":receipt["science_verdict"],"gates":receipt["gates"]},sort_keys=True))
if __name__=="__main__":main()
