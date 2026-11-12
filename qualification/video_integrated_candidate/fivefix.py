#!/usr/bin/env python3
"""Integrate fifth separately qualified full-3D pinup knee into original 22-case corpus.

Composition is scoped to one case and one transient worker: 4 pre-existing
contact fixes + 1 verified pinup knee fix. The 17 remaining original cases must
have byte-identical source labels and animated glTF models, while the five
target cases must produce new source, GLB and encoded H264. No oracle relabels.
"""
from pathlib import Path
import argparse
import json
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"video_integrated_candidate"))
sys.path.insert(0,str(HERE/"video_pinup_3d_fix"))
import generate_integrated as integration
import pinup_ab as pinup

gen=integration.gen
PINUP=pinup.CASE
TARGETS=integration.TARGETS | frozenset((PINUP,))
OLD_BUILD_CASE=gen.build_case
OLD_KNEE=gen.knee_ik

def scoped_build_case(case,out):
    if case != PINUP:
        if gen.knee_ik is not OLD_KNEE:
            raise ValueError("UNSAFE_GLOBAL_KNEE_PATCH_LEAK")
        return OLD_BUILD_CASE(case,out)
    if gen.knee_ik is not OLD_KNEE:
        raise ValueError("UNSAFE_PINUP_PATCH_NESTED")
    try:
        gen.knee_ik=pinup.corrected
        return OLD_BUILD_CASE(case,out)
    finally:
        gen.knee_ik=OLD_KNEE

def evaluate(batch,root,original_root):
    if batch not in integration.COUNTS:
        raise ValueError("INVALID_BATCH")
    if gen.build_case is not OLD_BUILD_CASE:
        raise ValueError("GENERATOR_ALREADY_PATCHED")
    try:
        # The existing strict integration performs original manifest/rights SHA
        # custody checks, verifies every target's original FAIL and candidate
        # PASS, and proves unchanged source/GLB SHA on every non-target case.
        integration.TARGETS=TARGETS
        gen.build_case=scoped_build_case
        report=integration.check_batch(batch,root,original_root)
    finally:
        gen.build_case=OLD_BUILD_CASE
        gen.knee_ik=OLD_KNEE
        integration.TARGETS=TARGETS-frozenset((PINUP,))
    if report["schema"]!="scp.integrated-original-22-4fix-candidate-batch.v1":
        raise ValueError("ORIGINAL_INTEGRATION_RECEIPT_SHAPE_DRIFT")
    expected={"locomotion":set(),"exercise_pose":{PINUP,"male_stand_barefoot"},
              "dance_combat":{"female_judo_kata_barefoot","male_dance_boots","female_dance_high_heels"},
              "aquatic":set()}[batch]
    actual=set(report["improved_cases"])
    if actual!=expected:
        raise ValueError("CHANGED_CASE_SCOPE_NOT_AS_ADMITTED")
    # Catch encode/transcode drift and cross-case contamination independently;
    # unchanged cases must retain exact original encoded video bits, too.
    for row in report["cases"]:
        if not row["repair_target"] and row["original_h264_sha256"]!=row["candidate_h264_sha256"]:
            raise ValueError("NON_TARGET_H264_BIT_CUSTODY_REGRESSION")
    if batch=="exercise_pose":
        name=PINUP+"_ground_truth.json"
        before=json.loads((Path(original_root)/batch/name).read_text())
        after=json.loads((Path(root)/batch/name).read_text())
        if len(before["frames"])!=len(after["frames"]) or len(after["frames"])!=40:
            raise ValueError("PINUP_FRAME_COUNT_CHANGED")
        for a,b in zip(before["frames"],after["frames"]):
            if a["contact"]!=b["contact"]:
                raise ValueError("PINUP_CONTACT_RELABELLING_PROHIBITED")
            allowed={"left_knee","right_knee"}
            aj=a["joints"];bj=b["joints"]
            if set(aj)!=set(bj):
                raise ValueError("PINUP_JOINT_SCHEMA_CHANGED")
            if any(aj[k]!=bj[k] for k in aj if k not in allowed):
                raise ValueError("PINUP_UNRELATED_SOURCE_JOINT_CHANGED")
    report["schema"]="scp.integrated-original-22-5fix-candidate-batch.v1"
    report["science"]="TARGETED_SOURCE_MATH_AND_TRUE_3D_BONE_LENGTH_ONLY"
    report["candidate_required_changed_ids"]=sorted(actual)
    report["cases_checked_without_changes"]=sum(not item["repair_target"] for item in report["cases"])
    report["limits"]=[
      "Source-only kinematic contact and exact 3D bone lengths are not a human biomechanics/soft-tissue/realism proof",
      "The altered pinup knee branch is the closest mathematical branch to an original possibly invalid knee",
      "Pre-existing original 22-case negative controls and all original model/video SHA are immutable",
      "Only four planted contact trajectories and one female pinup knee are under this research scope",
    ]
    (Path(root)/batch/"integration-receipt.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--batch",required=True,choices=integration.COUNTS)
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--original-root",required=True,type=Path)
    args=p.parse_args()
    result=evaluate(args.batch,args.root,args.original_root)
    print("ORIGINAL_22_FIVE_SOURCE_KINEMATIC_FIXES",args.batch,
          result["improved_cases"],result["cases_checked_without_changes"],
          result["original_counts"],result["candidate_counts"])

if __name__=="__main__":
    main()
