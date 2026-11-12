#!/usr/bin/env python3
"""Compose two independently tested static stance fixes with five-source candidate.

The exact-source composer is retained unchanged except for a strict dynamic
target-ID allowlist. Source original baseline is immutable; all 15 non-target
rights-original GLBs/H264/labels are copied exactly after SHA validation.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"video_integrated_candidate"))
sys.path.insert(0,str(ROOT/"video_pose_contact_ab"))
import fivefix
import static_pose_ab as poses

TWO=frozenset(("female_photoshoot_high_heels","male_karate_kata_barefoot"))
SEVEN=fivefix.TARGETS | TWO
GEN=fivefix.gen
BASE_SCOPED=fivefix.scoped_build_case
BASE_TARGETS=fivefix.TARGETS

def extended_scope(case,out):
    if case=="female_photoshoot_high_heels":
        if GEN.photoshoot_motion is not poses.ORIGINAL_PHOTO:
            raise ValueError("PHOTOGRAPHIC_POSE_PATCH_LEAKAGE")
        try:
            GEN.photoshoot_motion=poses.patched_photoshoot
            return BASE_SCOPED(case,out)
        finally:
            GEN.photoshoot_motion=poses.ORIGINAL_PHOTO
    if case=="male_karate_kata_barefoot":
        if GEN.karate_motion is not poses.ORIGINAL_KARATE:
            raise ValueError("KARATE_POSE_PATCH_LEAKAGE")
        try:
            GEN.karate_motion=poses.patched_karate
            return BASE_SCOPED(case,out)
        finally:
            GEN.karate_motion=poses.ORIGINAL_KARATE
    return BASE_SCOPED(case,out)

def evaluate(batch,root,original):
    if batch not in fivefix.integration.COUNTS:
        raise ValueError("UNKNOWN_BATCH")
    if fivefix.TARGETS!=BASE_TARGETS or fivefix.scoped_build_case is not BASE_SCOPED:
        raise ValueError("UNSAFE_MUTABLE_GENERATOR_STATE")
    try:
        fivefix.TARGETS=SEVEN
        fivefix.scoped_build_case=extended_scope
        report=fivefix.evaluate(batch,root,original)
    finally:
        fivefix.TARGETS=BASE_TARGETS
        fivefix.scoped_build_case=BASE_SCOPED
        fivefix.integration.TARGETS=BASE_TARGETS-frozenset((fivefix.PINUP,))
        GEN.photoshoot_motion=poses.ORIGINAL_PHOTO
        GEN.karate_motion=poses.ORIGINAL_KARATE
    expected={x for x in SEVEN if x in GEN.BATCHES[batch]}
    if set(report["improved_cases"])!=expected:
        raise ValueError("INCORRECT_SEVEN_CASE_PROMOTION")
    if report["cases_checked_without_changes"]!=len(GEN.BATCHES[batch])-len(expected):
        raise ValueError("UNCHANGED_CASE_COUNT_FAILED")
    if not all(item["original_h264_sha256"]==item["candidate_h264_sha256"]
               and item["original_glb_sha256"]==item["candidate_glb_sha256"]
               and item["original_joint_labels_sha256"]==item["candidate_joint_labels_sha256"]
               for item in report["cases"] if not item["repair_target"]):
        raise ValueError("IMMUTABLE_UNCHANGED_SOURCE_BYTES_FAILED")
    report["schema"]="scp.original-22-exact-source-7fix-candidate-batch.v1"
    report["science"]="SEVEN_TARGETED_KINEMATIC_CONTACT_AND_BONE_LENGTH_FIXES_NOT_HUMAN_REALISM"
    report["limits"]+=[
        "Two new source-target cases use world-fixed feet and unchanged contact labels; cinematic upper-body poses remain stylized",
        "All 15 unaffected source originals pass through as exact immutable verified GLB/H264 source bytes",
        "Jump and cartwheel unreachable geometry, other gait physics and soft tissue remain unresolved",
    ]
    (Path(root)/batch/"integration-receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--batch",required=True,choices=fivefix.integration.COUNTS)
    p.add_argument("--root",required=True)
    p.add_argument("--original-root",required=True)
    a=p.parse_args()
    result=evaluate(a.batch,a.root,a.original_root)
    print("ORIGINAL_SEVEN_SOURCE_CANDIDATE",a.batch,result["case_count"],
          result["improved_cases"],result["original_counts"],result["candidate_counts"])

if __name__=="__main__":
    main()
