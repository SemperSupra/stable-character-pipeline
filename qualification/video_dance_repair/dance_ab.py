#!/usr/bin/env python3
"""Independent two-dance A/B: world-planted stance vs source-drifting feet.

Share existing rights-original generation and contact audit implementation
without modifying the source original controls. Swing is a C1-shaped in-place
foot lift; this does NOT model force, floor friction or professional dance.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

C = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(C/"video_motion_repair"))
from planted_stance_ab import gen, audit, LIMBS, check_actual_media

CASES=("female_dance_high_heels","male_dance_boots")
ORIGINAL=gen.dance_motion

def candidate_dance(t,body,shoe):
    root,_,contact,sway=ORIGINAL(t,body,shoe)
    phase=(t/2.0)%1.0
    q=math.asin(0.7)/(2*math.pi)
    arcs={
        "left":(q,0.5-q),
        "right":(0.5+q,1.0-q)
    }
    anchors={"left":(.17,-body.hip_half),"right":(.27,body.hip_half)}
    feet={}
    for side in ("left","right"):
        lo,hi=arcs[side]
        active=lo<phase<hi
        if bool(not contact[side])!=active:
            # Reject source/contact phase disagreeing with the repaired stance dynamics.
            raise ValueError("SWING_CONTACT_INCONSISTENCY")
        progress=(phase-lo)/(hi-lo) if active else 0.
        lift=math.sin(math.pi*progress)**2 if active else 0.
        x,y=anchors[side]
        feet[side]=np.array([x+0.10*lift,y+(0.02 if side=="right" else -0.02)*lift,
                             shoe.heel_height+0.09*lift])
    return root,feet,contact,sway

def evaluate(out):
    out=Path(out)
    result=[]
    try:
        for case in CASES:
            base,candidate=out/"before"/case,out/"after"/case
            base.mkdir(parents=True,exist_ok=True);candidate.mkdir(parents=True,exist_ok=True)
            gen.dance_motion=ORIGINAL
            gen.build_case(case,base)
            before=audit.audit_case(base/(case+"_ground_truth.json"),LIMBS)
            bmedia=check_actual_media(base,case)
            try:
                gen.dance_motion=candidate_dance
                gen.build_case(case,candidate)
            finally:
                gen.dance_motion=ORIGINAL
            after=audit.audit_case(candidate/(case+"_ground_truth.json"),LIMBS)
            amedia=check_actual_media(candidate,case)
            if before["status"]!="FAIL" or after["status"]!="PASS":
                raise ValueError("TARGETED_AUDIT_NOT_FIXED:"+case)
            if before["defect_count"]<=0 or after["defect_count"]!=0:
                raise ValueError("REPAIRED_SOURCE_NOT_FAIL_CLOSED:"+case)
            if bmedia["glb_sha256"]==amedia["glb_sha256"] or bmedia["h264_sha256"]==amedia["h264_sha256"]:
                raise ValueError("SAME_AS_ORIGINAL_MEDIA")
            first=json.loads((base/(case+"_ground_truth.json")).read_text())
            second=json.loads((candidate/(case+"_ground_truth.json")).read_text())
            if len(first["frames"])!=40 or len(second["frames"])!=40:
                raise ValueError("BAD_FRAME_COUNTS")
            if [f["contact"] for f in first["frames"]] != [f["contact"] for f in second["frames"]]:
                raise ValueError("RELABEL_TO_PASS_NOT_PERMITTED")
            for side in ("left","right"):
                samples=[(i,f) for i,f in enumerate(second["frames"]) if f["contact"][side]]
                if not samples:
                    raise ValueError("NO_VALID_GROUND_CONTACT")
                anchor=samples[0][1]["joints"][side+"_ankle"]
                if any(math.dist(f["joints"][side+"_ankle"],anchor)>1e-7 for i,f in samples):
                    raise ValueError("WORLD_SPACE_ANCHOR_NOT_CONSTANT")
            result.append({"case":case,"original":before,"candidate":after,
                "before_media":bmedia,"after_media":amedia,
                "labels_changed":False,
                "science":"TARGETED_PLANTED_FOOT_NO_BIOMECHANICS"})
    finally:
        gen.dance_motion=ORIGINAL
    return {"schema":"scp.dance-original-anchored-contact-ab.v1",
            "case_count":len(result),"observations":result,
            "scientific_status":"TARGETED_KINEMATIC_CONTACT_ONLY",
            "limits":["In-place choreography is stylized, not expert-validated dance motion",
                      "No friction, forces, dynamics, energy or balance qualification",
                      "Independent source-to-render and frame/pixel reviewers still required",
                      "Original negative controls are separate and preserved"]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    data=evaluate(out)
    (out/"dance-ab.json").write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    print("DANCE_ORIGINAL_VS_CANDIDATE_CONTACT",[(r["case"],r["original"]["defect_count"],
        r["candidate"]["defect_count"]) for r in data["observations"]])

if __name__=="__main__":
    main()
