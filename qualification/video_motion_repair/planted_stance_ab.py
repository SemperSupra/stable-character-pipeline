#!/usr/bin/env python3
"""Render real original-vs-repaired GLB/H264 pairs with independent contact audit.

This experiment repairs only planted foot world-space anchoring in standing and
the deliberately planted judo-gesture pose. It does NOT certify full-body gait.
The upstream generator remains unmodified so the original negative controls
and their first-party source SHA are preserved for falsification.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1] / "expanded_motion_corpus"
sys.path.insert(0, str(ROOT))
import build_motion_batches as gen
import motion_math as audit

CASES = ("male_stand_barefoot", "female_judo_kata_barefoot")
LIMBS = {"male": (.54, .53), "female": (.52, .51)}

def patched_stand(t, body, shoe):
    root, feet, contacts = ORIGINAL_STAND(t, body, shoe)
    # Do not follow the pelvis sway with a stance ankle in world coordinates.
    feet["left"] = np.array([0.15, -body.hip_half, shoe.heel_height])
    feet["right"] = np.array([0.25, body.hip_half, shoe.heel_height])
    return root, feet, contacts

def patched_judo(t, body, shoe):
    root, feet, contacts, mode = ORIGINAL_JUDO(t, body, shoe)
    # Fix the planted ankles; the torso gesture remains a local approximation.
    feet["left"] = np.array([0.20, -body.hip_half - 0.05, shoe.heel_height])
    feet["right"] = np.array([0.34, body.hip_half + 0.05, shoe.heel_height])
    return root, feet, contacts, mode

ORIGINAL_STAND = gen.stand_motion
ORIGINAL_JUDO = gen.judo_motion

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_actual_media(folder, case):
    video = folder / (case + "_side.mp4")
    model = folder / (case + ".glb")
    import subprocess
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,nb_frames,width,height",
        "-of", "json", str(video)], timeout=20))["streams"][0]
    if probe["codec_name"] != "h264" or int(probe["nb_frames"]) != 40 or int(probe["width"]) != 320:
        raise ValueError("ENCODED_VIDEO_PROVENANCE_FAILURE")
    if model.read_bytes()[:4] != b"glTF":
        raise ValueError("ANIMATED_GLB_NOT_PRESENT")
    return {"h264_sha256": sha(video), "glb_sha256": sha(model), "frames": 40}

def evaluate(output):
    output = Path(output)
    results = []
    for case in CASES:
        baseline_dir, corrected_dir = output / "baseline" / case, output / "candidate" / case
        baseline_dir.mkdir(parents=True, exist_ok=True)
        corrected_dir.mkdir(parents=True, exist_ok=True)
        gen.stand_motion, gen.judo_motion = ORIGINAL_STAND, ORIGINAL_JUDO
        gen.build_case(case, baseline_dir)
        original = audit.audit_case(baseline_dir/(case+"_ground_truth.json"), LIMBS)
        old_media = check_actual_media(baseline_dir, case)
        try:
            gen.stand_motion, gen.judo_motion = patched_stand, patched_judo
            gen.build_case(case, corrected_dir)
        finally:
            gen.stand_motion, gen.judo_motion = ORIGINAL_STAND, ORIGINAL_JUDO
        new = audit.audit_case(corrected_dir/(case+"_ground_truth.json"), LIMBS)
        new_media = check_actual_media(corrected_dir, case)
        # Real source data changed; preserves original and never rewrites the gold oracle.
        if original["status"] != "FAIL" or new["status"] != "PASS":
            raise ValueError("BASELINE_REPAIR_STATUS_FAILED:" + case)
        if original["defect_count"] <= 0 or new["defect_count"] != 0:
            raise ValueError("DOES_NOT_CORRECT_SOURCE_CONTACT:" + case)
        if original["source_sha256"] == new["source_sha256"]:
            raise ValueError("UNMODIFIED_SOURCE_MASQUERADES_AS_REPAIR")
        if old_media["glb_sha256"] == new_media["glb_sha256"] or old_media["h264_sha256"] == new_media["h264_sha256"]:
            raise ValueError("MODEL_OR_VIDEO_WAS_NOT_REGENERATED")
        before=json.loads((baseline_dir/(case+"_ground_truth.json")).read_text())
        after=json.loads((corrected_dir/(case+"_ground_truth.json")).read_text())
        for i,(a,b) in enumerate(zip(before["frames"],after["frames"])):
            if a["contact"] != b["contact"]:
                raise ValueError("CONTACT_RELABEL_ONLY_REPAIR_PROHIBITED")
            for side in ("left","right"):
                if not b["contact"][side]:
                    raise ValueError("EXPERIMENT_CASE_EXPECTS_PLANTED_ANKLES")
                j=b["joints"][side+"_ankle"]
                if math.dist(j,after["frames"][0]["joints"][side+"_ankle"]) > 1e-7:
                    raise ValueError("REPAIRED_FOOT_NOT_WORLD_FIXED")
        results.append({
            "case":case, "baseline":original, "candidate":new,
            "baseline_media":old_media,"candidate_media":new_media,
            "ground_truth_unchanged_contact_labels": True,
            "note": "Targeted world-space stance correction; not natural biomechanics or judo proof"})
    return {"schema":"scp.motion-planted-stance-original-ab.v1",
            "case_count":len(results),"cases":results,
            "candidate_targeted_source_passes":sum(x["candidate"]["status"]=="PASS" for x in results),
            "science":"RDT_E_TARGETED_CONTACT_AND_LENGTH_ONLY",
            "limits":[
                "Original 22-case corpus remains separate and unmodified",
                "No measured forces, ground reaction, joint torque, balance, or physical footwear",
                "Judo pose is a stylized gesture, not a validated throw",
                "Each candidate must survive human frame and contact review before adoption",
            ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    report=evaluate(args.out)
    (args.out/"ab-receipt.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("REAL_GLTF_H264_PLANTED_REPAIR_AB", [(c["case"],c["baseline"]["defect_count"],
          c["candidate"]["defect_count"]) for c in report["cases"]])

if __name__=="__main__":
    main()
