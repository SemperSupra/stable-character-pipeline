#!/usr/bin/env python3
"""Actual original-clip decoded video static/hold vs source-joint-motion diagnosis.

This independently decomposes the A/B video frames into gray pixel differences
and source pose motion at matching 20fps frame transitions. It does not decide
human gait realism, physical forces or general motion correctness; uncertain
regions remain explicitly uncertain.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

CASES=("male_karate_kata_barefoot","female_photoshoot_high_heels")
W=H=320
N=40

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def decode(path):
    out=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
      "-i",str(path),"-map","0:v:0","-vsync","0","-pix_fmt","gray",
      "-f","rawvideo","pipe:1"],capture_output=True,timeout=60,check=True)
    block=W*H
    if len(out.stdout)!=N*block:
        raise ValueError("VIDEO_NOT_40_320x320_DECODED_FRAMES")
    return [out.stdout[i*block:(i+1)*block] for i in range(N)]

def source_motion(frame_a,frame_b):
    ja=frame_a["joints"];jb=frame_b["joints"]
    if set(ja)!=set(jb) or not ja:
        raise ValueError("JOINT_SCHEMA_CHANGED")
    values=[]
    for name in sorted(ja):
        a,b=ja[name],jb[name]
        if len(a)!=3 or len(b)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in (*a,*b)):
            raise ValueError("NONFINITE_SOURCE_JOINT")
        values.append(math.dist(a,b))
    return max(values),sum(values)/len(values)

def classify(max_source_m,mean_abs_gray,changed_fraction):
    if not all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in (max_source_m,mean_abs_gray,changed_fraction)):
        raise ValueError("INVALID_OBSERVATION")
    if changed_fraction>1:
        raise ValueError("INVALID_PIXEL_FRACTION")
    near_static_source=max_source_m<.00001
    near_static_image=mean_abs_gray<.01 or changed_fraction<.0001
    if near_static_source and near_static_image: return "STATIONARY_SOURCE_AND_VIDEO"
    if not near_static_source and near_static_image: return "SOURCE_MOTION_NOT_OBSERVED_IN_VIDEO"
    if near_static_source and not near_static_image: return "VIDEO_CHANGED_WITHOUT_SOURCE_JOINT_MOTION"
    return "BOTH_MOVING"

def analyze(case,root):
    if case not in CASES:
        raise ValueError("UNADMITTED_CASE")
    root=Path(root)
    receipt=json.loads((root/"pose-contact-ab.json").read_text())
    if receipt.get("schema")!="scp.original-two-anchored-poses-source-ab.v1" or receipt.get("case")!=case:
        raise ValueError("UNTRUSTED_AB_RECEIPT")
    results={}
    for kind,prefix in (("original","before"),("candidate","after")):
        video=root/prefix/(case+"_side.mp4")
        label=root/prefix/(case+"_ground_truth.json")
        media=receipt["before_media" if kind=="original" else "after_media"]
        if sha(video)!=media["h264_sha256"]:
            raise ValueError("H264_CUSTODY_MISMATCH")
        doc=json.loads(label.read_text())
        if doc.get("case")!=case or doc.get("fps")!=20 or len(doc.get("frames",[]))!=N:
            raise ValueError("SOURCE_LABEL_SCOPE_OR_FRAME_COUNT")
        images=decode(video)
        transitions=[]
        for i in range(1,N):
            a,b=images[i-1],images[i]
            total_abs=sum(abs(x-y) for x,y in zip(a,b))
            changed=sum(abs(x-y)>3 for x,y in zip(a,b))
            mad=total_abs/len(a)
            frac=changed/len(a)
            largest,mean=source_motion(doc["frames"][i-1],doc["frames"][i])
            transitions.append({
                "to_frame":i,"time_s":i/20,
                "decoded_video_mae_grayscale":round(mad,7),
                "decoded_pixels_changed_fraction_gt3":round(frac,7),
                "source_max_joint_displacement_m":round(largest,7),
                "source_mean_joint_displacement_m":round(mean,7),
                "class":classify(largest,mad,frac)})
        results[kind]={
            "h264_sha256":sha(video),"source_labels_sha256":sha(label),
            "total_transitions":len(transitions),
            "counts":{key:sum(t["class"]==key for t in transitions) for key in
                 ("STATIONARY_SOURCE_AND_VIDEO","SOURCE_MOTION_NOT_OBSERVED_IN_VIDEO",
                  "VIDEO_CHANGED_WITHOUT_SOURCE_JOINT_MOTION","BOTH_MOVING")},
            "transitions":transitions}
    return {
        "schema":"scp.original-ab-h264-frame-motion-custody.v1",
        "case":case,"original":results["original"],"candidate":results["candidate"],
        "science":"PIXEL_TO_SOURCE_TRAJECTORY_CORRELATION_NOT_A_HUMAN_MOTION_VERDICT",
        "limits":[
            "A single static decoded frame can be a deliberate pose hold, renderer problem, or frame/encoding granularity",
            "Source joint movement is not human motion ground truth or visible-pixel physical realism",
            "Thresholds are diagnostic; Go evaluator freeze thresholds independently authoritative for its own gate",
            "No identity, anatomy, skin, soft tissue, forces, balance, footwear dynamics or production claims",
        ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",required=True,choices=CASES)
    p.add_argument("--root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    result=analyze(a.case,a.root)
    Path(a.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("ACTUAL_SOURCE_TO_VIDEO_FREEZE_FORENSICS",a.case,
          result["original"]["counts"],result["candidate"]["counts"])

if __name__=="__main__":
    main()
