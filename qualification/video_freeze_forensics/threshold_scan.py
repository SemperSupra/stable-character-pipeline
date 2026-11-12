#!/usr/bin/env python3
"""Research-only actual H264 freeze-threshold/3D-source-motion correlation.

This script invokes unmodified FFmpeg freezedetect thresholds independently
on original and candidate rights-original cases and calculates source motion
in their exact source frame intervals. It never changes the Go evaluator,
removes original failure evidence, or promotes cinematic/biomechanical realism.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

CASES={"male_karate_kata_barefoot","female_photoshoot_high_heels"}
THRESHOLDS=(-50,-45,-40)
START=re.compile(r"freeze_start:\s*([0-9]+(?:\.[0-9]+)?)")
END=re.compile(r"freeze_end:\s*([0-9]+(?:\.[0-9]+)?)")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def spans(log,duration_s=2.0):
    starts=[float(v) for v in START.findall(log)]
    ends=[float(v) for v in END.findall(log)]
    if len(ends)>len(starts):
        raise ValueError("FREEZE_LOG_END_WITHOUT_START")
    results=[]
    for idx,begin in enumerate(starts):
        end=ends[idx] if idx<len(ends) else duration_s
        if not(0<=begin<=end<=duration_s+.001):
            raise ValueError("INVALID_FREEZE_SPAN_CLOCK")
        results.append({"start_s":begin,"end_s":end,"duration_s":round(end-begin,6)})
    return results

def source_motion(frames,begin,end):
    indices=range(max(0,min(39,math.floor(begin*20))),min(39,math.ceil(end*20))+1)
    numbers=list(indices)
    if len(numbers)<2:
        return {"max_joint_displacement_m":0.0,"pairs":0,"joint_data_sufficient":False}
    maximum=0.
    pairs=0
    for a,b in zip(numbers,numbers[1:]):
        x,y=frames[a]["joints"],frames[b]["joints"]
        if set(x)!=set(y) or not x:
            raise ValueError("SOURCE_JOINT_SCHEMA_CHANGED")
        for name in x:
            if len(x[name])!=3 or len(y[name])!=3:
                raise ValueError("INVALID_SOURCE_JOINT")
            if any(not isinstance(t,(int,float)) or isinstance(t,bool) or not math.isfinite(t) for t in x[name]+y[name]):
                raise ValueError("NONFINITE_SOURCE_COORDINATES")
            maximum=max(maximum,math.dist(x[name],y[name]))
        pairs+=1
    return {"max_joint_displacement_m":round(maximum,8),
            "pairs":pairs,"joint_data_sufficient":True}

def measure(root,case):
    if case not in CASES: raise ValueError("CASE_NOT_ADMITTED")
    root=Path(root)
    receipt=json.loads((root/"pose-contact-ab.json").read_text())
    if receipt.get("schema")!="scp.original-two-anchored-poses-source-ab.v1" or receipt.get("case")!=case:
        raise ValueError("WRONG_AB_SOURCE_RECEIPT")
    results={}
    for version,folder,meta in (("original","before","before_media"),("candidate","after","after_media")):
        video=root/folder/(case+"_side.mp4")
        labels=root/folder/(case+"_ground_truth.json")
        if sha(video)!=receipt[meta]["h264_sha256"]:
            raise ValueError("VIDEO_HASH_CUSTODY_FAILURE")
        doc=json.loads(labels.read_text())
        if doc.get("case")!=case or len(doc.get("frames",[]))!=40 or doc.get("fps")!=20:
            raise ValueError("SOURCE_CLOCK_NOT_ADMITTED")
        probes=[]
        for threshold in THRESHOLDS:
            cmd=["ffmpeg","-nostdin","-hide_banner","-loglevel","info",
                 "-i",str(video),
                 "-vf",f"freezedetect=n={threshold}dB:d=0.35",
                 "-an","-f","null","-"]
            process=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,check=False)
            if process.returncode!=0:
                raise ValueError("FFMPEG_FREEZE_DIAGNOSTIC_FAILED")
            raw=process.stderr.decode("utf-8",errors="replace")
            windows=spans(raw)
            for w in windows:
                w["source_motion"]=source_motion(doc["frames"],w["start_s"],w["end_s"])
                w["source_moves_above_0_1mm"]=w["source_motion"]["max_joint_displacement_m"]>.0001
            probes.append({"noise_floor_db":threshold,"minimum_hold_s":.35,
                           "freeze_event_count":len(windows),"windows":windows,
                           "diagnostic_log_sha256":hashlib.sha256(process.stderr).hexdigest()})
        results[version]={"h264_sha256":sha(video),"source_labels_sha256":sha(labels),"actual_ffmpeg_probes":probes}
    return {"schema":"scp.original-h264-freezedetect-vs-source-3d-kinematics.v1","case":case,
            "original":results["original"],"candidate":results["candidate"],
            "status":"THRESHOLD_SENSITIVITY_DIAGNOSTIC_NOT_OVERRIDING_GO_FAIL",
            "science_limits":[
               "A small source 3D joint displacement can be genuine movement without visible luminance impact",
               "FFmpeg near-frozen warning cannot be equated with identical encoded or decoded consecutive frames",
               "Threshold scans are not calibrated to naturalistic human biomechanics or optimal classifier cutoff",
               "Do not promote source PASS to video or product PASS; keep original Go fail until owner review"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",required=True,choices=CASES)
    p.add_argument("--root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    report=measure(a.root,a.case)
    Path(a.out).write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("SAME_H264_FFMPEG_FREEZE_THRESHOLD_SENSITIVITY",
        a.case,[(p["noise_floor_db"],p["freeze_event_count"])
            for p in report["candidate"]["actual_ffmpeg_probes"]])

if __name__=="__main__":
    main()
