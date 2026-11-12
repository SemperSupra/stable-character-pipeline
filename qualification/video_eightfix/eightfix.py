#!/usr/bin/env python3
"""Compose prior 7 source repairs and isolated cloud-qualified diving takeoff.

The Mac OpenCode actor owns male_jump_slippers and is not touched by this
integrator; all 14 non-target original 22-case meshes/videos/labels must retain
exact prior SHA custody. This is source geometry RDT&E, not cinematic physics.
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"video_integrated_candidate"))
sys.path.insert(0,str(ROOT/"video_dive_takeoff"))
import sevenfix
import dive_ab

CASE=dive_ab.CASE
EIGHT=sevenfix.SEVEN | frozenset((CASE,))
GEN=sevenfix.GEN
BASE_SEVEN=sevenfix.SEVEN
BASE_SCOPE=sevenfix.extended_scope

def extended_scope(name,out):
    if name!=CASE:
        return BASE_SCOPE(name,out)
    if GEN.diving_motion is not dive_ab.ORIGINAL:
        raise ValueError("UNADMITTED_DIVE_SOURCE_PATCH_LEAK")
    try:
        GEN.diving_motion=dive_ab.proposed_dive
        return BASE_SCOPE(name,out)
    finally:
        GEN.diving_motion=dive_ab.ORIGINAL

def check_full_dive_source(original_root,output_root):
    a=json.loads((Path(original_root)/"aquatic"/(CASE+"_ground_truth.json")).read_text())
    b=json.loads((Path(output_root)/"aquatic"/(CASE+"_ground_truth.json")).read_text())
    if len(a["frames"])!=len(b["frames"]) or len(b["frames"])!=40:
        raise ValueError("DIVE_SOURCE_CLOCK_NOT_PRESERVED")
    support=GEN.FOOTWEAR["barefoot"].toe_thickness+.058
    anchors={}
    for old,new in zip(a["frames"],b["frames"]):
        if old["contact"]!=new["contact"]:
            raise ValueError("DIVE_SOURCE_CONTACT_FLAGS_RELABELLED")
        for side in ("left","right"):
            hipkey=side+"_hip"
            hipa,hipb=old["joints"][hipkey],new["joints"][hipkey]
            if math.dist(hipa[:2],hipb[:2])>1e-8:
                raise ValueError("DIVE_HIP_HORIZONTAL_TRAJECTORY_TAMPERED")
            if new["contact"][side]:
                ankle=new["joints"][side+"_ankle"]
                if abs(ankle[2]-support)>1e-8:
                    raise ValueError("DIVE_FOOT_LINK_SUPPORT_ENVELOPE_CHANGED")
                if side not in anchors:anchors[side]=ankle
                if math.dist(ankle,anchors[side])>1e-8:
                    raise ValueError("DIVE_PLANTED_ANKLE_SLIDING")
                if abs((hipa[2]-hipb[2])-.14)>1e-8:
                    raise ValueError("DIVE_REQUIRED_REACHABLE_CROUCH_NOT_PRESERVED")
    if set(anchors)!={"left","right"}:
        raise ValueError("DIVE_NO_ORIGINAL_PLANTED_FOOT_OBSERVED")

def evaluate(batch,root,original_root):
    if batch not in sevenfix.fivefix.integration.COUNTS:
        raise ValueError("UNADMITTED_ORIGINAL_FAMILY")
    if sevenfix.SEVEN!=BASE_SEVEN or sevenfix.extended_scope is not BASE_SCOPE:
        raise ValueError("UNTRUSTWORTHY_ACTOR_SHARED_GENERATOR_STATE")
    try:
        sevenfix.SEVEN=EIGHT
        sevenfix.extended_scope=extended_scope
        report=sevenfix.evaluate(batch,root,original_root)
    finally:
        sevenfix.SEVEN=BASE_SEVEN
        sevenfix.extended_scope=BASE_SCOPE
        sevenfix.GEN.diving_motion=dive_ab.ORIGINAL
    targets={x for x in EIGHT if x in GEN.BATCHES[batch]}
    if set(report["improved_cases"])!=targets:
        raise ValueError("EIGHT_ADMITTED_TARGETS_DRIFT")
    if report["cases_checked_without_changes"]!=len(GEN.BATCHES[batch])-len(targets):
        raise ValueError("ORIGINAL_UNMODIFIED_CASE_COUNT_FAILED")
    if any(
        x["original_joint_labels_sha256"]!=x["candidate_joint_labels_sha256"] or
        x["original_glb_sha256"]!=x["candidate_glb_sha256"] or
        x["original_h264_sha256"]!=x["candidate_h264_sha256"]
        for x in report["cases"] if not x["repair_target"]):
        raise ValueError("NON_TARGET_SHA_CUSTODY_NOT_BYTE_IDENTICAL")
    if batch=="aquatic":
        check_full_dive_source(original_root,root)
    report["schema"]="scp.original-22-exact-source-8fix-candidate-batch.v1"
    report["science"]="EIGHT_TARGETED_SOURCE_KINEMATIC_FIXES_NOT_REALISM"
    report["limits"]=[x for x in report.get("limits",[]) if "All 15 unaffected" not in x]
    report["limits"]+= [
        "All fourteen original non-target GLB/H264/source files are byte-identical SHA-verified original assets",
        "Slipper jump remains exclusively owned by the local Mac actor; cartwheel and jumping jacks remain uncorrected",
        "Diving original crouch and support envelope are experimental kinematic assumptions without fluid/contact-force validation",
        "No realism/identity/joint range/footwear human anatomy admission from a source-only PASS"]
    (Path(root)/batch/"integration-receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--batch",required=True,choices=sevenfix.fivefix.integration.COUNTS)
    p.add_argument("--root",required=True)
    p.add_argument("--original-root",required=True)
    a=p.parse_args()
    r=evaluate(a.batch,a.root,a.original_root)
    print("ORIGINAL_EIGHT_SOURCE_CANDIDATE",a.batch,r["case_count"],
          r["improved_cases"],r["original_counts"],r["candidate_counts"])

if __name__=="__main__":
    main()
