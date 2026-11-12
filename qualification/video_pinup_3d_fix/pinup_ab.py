#!/usr/bin/env python3
"""Test the direct consequence of measured 3D IK feasibility on one case.

Source-original source labels, generated 40-frame GLBs and real H264s are
preserved. Only an independently feasible 3D knee solving implementation is
substituted, for the single designated female pinup pose; no joint-motion,
contact-label, render filter, or result-oracle manipulation.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"expanded_motion_corpus"))
sys.path.insert(0,str(ROOT/"video_ik_science"))
import build_motion_batches as gen
import motion_math as audit
from audit_3d_feasibility import solve_3d
CASE="female_pinup_stiletto"
ORIGINAL=gen.knee_ik
LIMBS={"male":(.54,.53),"female":(.52,.51)}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def corrected(hip, ankle, thigh, shin, bend_sign=1):
    candidate=ORIGINAL(hip,ankle,thigh,shin,bend_sign=bend_sign)
    row=solve_3d(list(hip),list(ankle),thigh,shin,list(candidate))
    if row["status"]!="FEASIBLE" or row["candidate_knee_bone_error_m"]>1e-7:
        raise ValueError("ORIGINAL_3D_POSE_NOT_FEASIBLE")
    return np.asarray(row["candidate_knee_xyz"],dtype=float)

def observed_media(folder):
    import subprocess
    path=folder/(CASE+"_side.mp4")
    model=folder/(CASE+".glb")
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error",
        "-select_streams","v:0","-show_entries",
        "stream=codec_name,nb_frames,width,height","-of","json",str(path)],timeout=20))["streams"][0]
    if probe["codec_name"]!="h264" or int(probe["nb_frames"])!=40 or int(probe["width"])!=320 or int(probe["height"])!=320:
        raise ValueError("SOURCE_REAL_VIDEO_INVALID")
    if model.read_bytes()[:4]!=b"glTF":
        raise ValueError("SOURCE_REAL_MODEL_INVALID")
    return {"source_glb_sha256":sha(model),"actual_h264_sha256":sha(path)}

def evaluate(root):
    root=Path(root)
    before=root/"before"; after=root/"after"
    before.mkdir(parents=True,exist_ok=True); after.mkdir(parents=True,exist_ok=True)
    try:
        gen.knee_ik=ORIGINAL
        gen.build_case(CASE,before)
        source_before=audit.audit_case(before/(CASE+"_ground_truth.json"),LIMBS)
        media_before=observed_media(before)
        gen.knee_ik=corrected
        gen.build_case(CASE,after)
        source_after=audit.audit_case(after/(CASE+"_ground_truth.json"),LIMBS)
        media_after=observed_media(after)
    finally:
        gen.knee_ik=ORIGINAL
    if source_before["status"]!="FAIL" or source_before["defect_count"]!=40:
        raise ValueError("ORIGINAL_SCIENCE_BASELINE_NOT_PRESERVED")
    if source_after["status"]!="PASS" or source_after["defect_count"]!=0:
        raise ValueError("EXACT_3D_SOURCE_CANDIDATE_FAILED")
    if media_before["source_glb_sha256"]==media_after["source_glb_sha256"] or media_before["actual_h264_sha256"]==media_after["actual_h264_sha256"]:
        raise ValueError("NO_ACTUAL_MODEL_OR_H264_CHANGE")
    old=json.loads((before/(CASE+"_ground_truth.json")).read_text())
    new=json.loads((after/(CASE+"_ground_truth.json")).read_text())
    if len(old["frames"])!=40 or len(new["frames"])!=40:
        raise ValueError("FRAME_COUNT_CHANGED")
    for original_frame,candidate_frame in zip(old["frames"],new["frames"]):
        if original_frame["contact"]!=candidate_frame["contact"]:
            raise ValueError("CONTACT_RELABELLING_FORBIDDEN")
        for side in ("left","right"):
            oj=original_frame["joints"];nj=candidate_frame["joints"]
            for suffix in ("hip","ankle"):
                key=side+"_"+suffix
                if oj[key]!=nj[key]:
                    raise ValueError("HIP_OR_ANKLE_MOTION_EDIT_NOT_PERMITTED")
            h,k,a=(nj[side+"_"+name] for name in ("hip","knee","ankle"))
            if abs(math.dist(h,k)-.52)>1e-6 or abs(math.dist(k,a)-.51)>1e-6:
                raise ValueError("THREED_BONE_LENGTH_INVARIANT_FAILED")
    return {
        "schema":"scp.pinup-original-full-3d-ik-corrective-ab.v1",
        "case":CASE,
        "original":source_before,"candidate":source_after,
        "before_media":media_before,"after_media":media_after,
        "changed_source_labels_sha256":(source_before["source_sha256"],source_after["source_sha256"]),
        "unchanged_original_hips_ankles_and_contact_labels":True,
        "original_artifacts_preserved":True,
        "scientific_status":"TARGETED_MATHEMATICAL_BONE_LENGTH_ONLY",
        "limits":[
            "Knee pole is chosen nearest original erroneous planar knee, not by physiological joint limits",
            "No balance, material, inertia, contact patch, constraint solver, realistic posture, naturalness or human identity acceptance",
            "Original 22-case baseline and other integrated source cases remain unchanged",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=evaluate(args.out)
    (args.out/"full3d-pinup-ab.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("ORIGINAL_FULL_3D_KNEE_A_B",result["case"],
        result["original"]["defect_count"],result["candidate"]["defect_count"])

if __name__=="__main__":
    main()
