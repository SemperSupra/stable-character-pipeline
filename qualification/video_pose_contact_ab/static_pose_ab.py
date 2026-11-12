#!/usr/bin/env python3
"""Original rights-only karate and photoshoot world-fixed stance A/B tests.

No source gold-label changes, frame removal or camera/codec substitutions. This
only proves targeted contact/leg-length invariants on source-math and actual
H264/GLB hashes, not believable fighting or photographic pose dynamics.
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
import build_motion_batches as gen
import motion_math as audit

CASES={
    "female_photoshoot_high_heels":("photoshoot_motion","photoshoot"),
    "male_karate_kata_barefoot":("karate_motion","karate_kata"),
}
LIMBS={"male":(.54,.53),"female":(.52,.51)}
ORIGINAL_PHOTO=gen.photoshoot_motion
ORIGINAL_KARATE=gen.karate_motion

def patched_photoshoot(t,body,shoe):
    root,_feet,contact,mode=ORIGINAL_PHOTO(t,body,shoe)
    # Preserve upper-body poses but keep planted high-heel anchors fixed.
    feet={"left":np.array([.20,-body.hip_half,shoe.heel_height]),
          "right":np.array([.31,body.hip_half*.6,shoe.heel_height+.03])}
    return root,feet,contact,mode

def patched_karate(t,body,shoe):
    root,_feet,contact,mode=ORIGINAL_KARATE(t,body,shoe)
    # A fixed supporting stance while upper-body guard/block/strike changes;
    # no abrupt foot teleportation under a CONTIGUOUS stance label.
    feet={"left":np.array([.18,-body.hip_half-.06,shoe.heel_height]),
          "right":np.array([.34,body.hip_half+.04,shoe.heel_height])}
    return root,feet,contact,mode

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def checked_media(folder,case):
    import subprocess
    video=folder/(case+"_side.mp4")
    glb=folder/(case+".glb")
    v=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=codec_name,nb_frames,width,height,pix_fmt",
        "-of","json",str(video)],timeout=20))["streams"][0]
    if (v.get("codec_name")!="h264" or v.get("pix_fmt")!="yuv420p" or
        int(v["nb_frames"])!=40 or int(v["width"])!=320 or int(v["height"])!=320):
        raise ValueError("NOT_ORIGINAL_40_FRAME_H264")
    if glb.read_bytes()[:4]!=b"glTF":
        raise ValueError("ANIMATED_GLB_FORMAT_MISSING")
    return {"h264_sha256":sha(video),"animated_glb_sha256":sha(glb)}

def evaluate(case,out):
    if case not in CASES: raise ValueError("CASE_NOT_ADMITTED")
    out=Path(out); before=out/"before"; after=out/"after"
    before.mkdir(parents=True,exist_ok=True);after.mkdir(parents=True,exist_ok=True)
    try:
        gen.photoshoot_motion=ORIGINAL_PHOTO
        gen.karate_motion=ORIGINAL_KARATE
        gen.build_case(case,before)
        a=audit.audit_case(before/(case+"_ground_truth.json"),LIMBS)
        ma=checked_media(before,case)
        gen.photoshoot_motion=patched_photoshoot
        gen.karate_motion=patched_karate
        gen.build_case(case,after)
        b=audit.audit_case(after/(case+"_ground_truth.json"),LIMBS)
        mb=checked_media(after,case)
    finally:
        gen.photoshoot_motion=ORIGINAL_PHOTO
        gen.karate_motion=ORIGINAL_KARATE
    if a["status"]!="FAIL" or a["defect_count"]<1 or b["status"]!="PASS" or b["defect_count"]!=0:
        raise ValueError("TARGETED_CONTACT_SOURCE_AUDIT_FAILED")
    if ma["h264_sha256"]==mb["h264_sha256"] or ma["animated_glb_sha256"]==mb["animated_glb_sha256"]:
        raise ValueError("NO_ACTUAL_REPAIRED_MODEL_OR_VIDEO_DELTA")
    old=json.loads((before/(case+"_ground_truth.json")).read_text())
    new=json.loads((after/(case+"_ground_truth.json")).read_text())
    for i,(x,y) in enumerate(zip(old["frames"],new["frames"])):
        if x["contact"]!=y["contact"]:
            raise ValueError("CONTACT_RELABELLING_NOT_AUTHORIZED")
        for side in ("left","right"):
            if not y["contact"][side]:
                raise ValueError("NOT_THE_STATIC_STANCE_HYPOTHESIS")
            fixed=new["frames"][0]["joints"][side+"_ankle"]
            current=y["joints"][side+"_ankle"]
            if math.dist(fixed,current)>1e-8:
                raise ValueError("PLANTED_WORLD_ANKLE_NOT_STATIONARY")
    return {
        "schema":"scp.original-two-anchored-poses-source-ab.v1",
        "case":case,"original":a,"candidate":b,
        "before_media":ma,"after_media":mb,
        "source_contact_flags_unchanged":True,
        "source_original_22_baseline_unchanged":True,
        "scientific_status":"TARGETED_SOURCE_KINEMATIC_A_B_ONLY",
        "holds":[
            "Judo/karate/photoshoot body mechanics not human-reviewed or physically simulated",
            "Heel pressure, balance, footwear, inertia and human joint constraints not validated",
            "Candidate needs independent source/video physics judge and full 22-case regression",
        ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",required=True,choices=CASES)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    r=evaluate(args.case,Path(args.out)/args.case)
    (Path(args.out)/args.case/"pose-contact-ab.json").write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("ORIGINAL_STATIC_STANCE_REPAIR",args.case,r["original"]["defect_count"],r["candidate"]["defect_count"])

if __name__=="__main__":
    main()
