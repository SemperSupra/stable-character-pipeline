#!/usr/bin/env python3
"""Real original diving takeoff A/B: stance-anchored ankles, non-contact glide.

Restricted source-original body case. Does not alter original 22 negative
controls, contact labels, upstream generator, media oracle or Mac actor's jump.
C1 release blend is a targeted kinematic hypothesis, not physical fluid/force.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"expanded_motion_corpus"))
import build_motion_batches as gen
import motion_math as audit

CASE="male_diving_barefoot"
ORIGINAL=gen.diving_motion
LIMBS={"male":(.54,.53),"female":(.52,.51)}

def proposed_dive(t,body,shoe):
    root,original,contact,phase=ORIGINAL(t,body,shoe)
    anchored={
      "left":np.asarray([.16-.08,-body.hip_half,shoe.heel_height],dtype=float),
      "right":np.asarray([.16+.03,body.hip_half,shoe.heel_height],dtype=float),
    }
    # Original source marks both feet planted until phase=.22. They previously
    # translated vertically with the crouching pelvis (false stance slide).
    # Hold them on their support plane and transition smoothly only after
    # declared toe-off to the original airborne/glide trajectory.
    release=gen.smooth01(max(0.,min(1.,(phase-.22)/.10)))
    feet={side:(1.-release)*anchored[side]+release*np.asarray(original[side],dtype=float)
          for side in ("left","right")}
    return root,feet,contact,phase

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def media(folder):
    folder=Path(folder)
    glb=folder/(CASE+".glb")
    video=folder/(CASE+"_side.mp4")
    if glb.read_bytes()[:4]!=b"glTF":
        raise ValueError("ANIMATED_MODEL_NOT_GLTF_BINARY")
    ff=json.loads(subprocess.check_output([
       "ffprobe","-v","error","-select_streams","v:0",
       "-show_entries","stream=codec_name,nb_frames,width,height",
       "-of","json",str(video)],timeout=30))["streams"][0]
    if ff.get("codec_name")!="h264" or int(ff.get("nb_frames",0))!=40 or int(ff.get("width",0))!=320 or int(ff.get("height",0))!=320:
        raise ValueError("NOT_ACTUAL_40F_H264")
    return {"glb_sha256":sha(glb),"h264_sha256":sha(video)}

def evaluate(out):
    out=Path(out)
    before=out/"original";after=out/"candidate"
    before.mkdir(parents=True,exist_ok=True)
    after.mkdir(parents=True,exist_ok=True)
    try:
        gen.diving_motion=ORIGINAL
        gen.build_case(CASE,before)
        first=audit.audit_case(before/(CASE+"_ground_truth.json"),LIMBS)
        bmedia=media(before)
        gen.diving_motion=proposed_dive
        gen.build_case(CASE,after)
        second=audit.audit_case(after/(CASE+"_ground_truth.json"),LIMBS)
        amedia=media(after)
    finally:
        gen.diving_motion=ORIGINAL
    if first["status"]!="FAIL" or first["defect_count"]!=16:
        raise ValueError("ORIGINAL_DIVE_NEGATIVE_CONTROL_NOT_REPRODUCED")
    if second["status"]!="PASS" or second["defect_count"]!=0:
        print("DIVE_REJECTED_SOURCE_DEFECTS", json.dumps({"status":second["status"],"count":second["defect_count"],"first_findings":second["findings"][:50],"limb_max":second["max_limb_length_error_m"],"stance_peak":second["peak_labeled_stance_speed_m_s"]},sort_keys=True),flush=True)
        raise ValueError("SOURCE_KINEMATIC_REPAIR_NOT_QUALIFIED")
    if bmedia["glb_sha256"]==amedia["glb_sha256"] or bmedia["h264_sha256"]==amedia["h264_sha256"]:
        raise ValueError("NO_ACTUAL_GLTF_OR_H264_DELTA")
    old=json.loads((before/(CASE+"_ground_truth.json")).read_text())
    new=json.loads((after/(CASE+"_ground_truth.json")).read_text())
    if len(old["frames"])!=len(new["frames"]) or len(old["frames"])!=40:
        raise ValueError("SOURCE_FRAME_COUNT_REGRESSION")
    anchored={}
    for idx,(a,b) in enumerate(zip(old["frames"],new["frames"])):
        if a["contact"]!=b["contact"]:
            raise ValueError("SOURCE_CONTACT_RELABEL_PROHIBITED")
        for side in ("left","right"):
            if b["contact"][side]:
                ankle=b["joints"][side+"_ankle"]
                if abs(ankle[2])>1e-8:
                    raise ValueError("PLANTED_BAREFOOT_NOT_ON_GROUND")
                if side not in anchored: anchored[side]=ankle
                if math.dist(ankle,anchored[side])>1e-8:
                    raise ValueError("PLANTED_WORLD_ANKLE_DRIFT")
        for key in ("left_hip","right_hip"):
            if a["joints"][key]!=b["joints"][key]:
                raise ValueError("UNAUTHORIZED_PELVIS_OR_HIP_TRAJECTORY_EDIT")
    return {
       "schema":"scp.original-dive-grounded-takeoff-ab.v1",
       "case":CASE,
       "original":first,"candidate":second,
       "original_media":bmedia,"candidate_media":amedia,
       "contact_labels_unchanged":True,
       "source_hip_trajectories_unchanged":True,
       "source_frame_count":40,
       "science":"TARGETED_SOURCE_CONTACT_AND_BONE_LENGTH_ONLY",
       "limits":[
          "Foot support during crouch is an experimental constraint, not measured ground forces",
          "Airborne transition is C1 blended, not physically simulated contact release or water entry",
          "Actual rendered H264 is not independently judged for human realism or temporal smoothness",
          "Original 22-case negative controls remain immutable; candidate only for separate full regression"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out)
    report=evaluate(out)
    (out/"dive-ab.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("ORIGINAL_DIVE_GROUNDED_TAKEOFF_AB",report["original"]["defect_count"],
          report["candidate"]["defect_count"],report["original"]["status"],report["candidate"]["status"])

if __name__=="__main__":
    main()
