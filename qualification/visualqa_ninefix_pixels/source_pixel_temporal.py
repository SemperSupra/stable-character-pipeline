#!/usr/bin/env python3
"""Source-3D vs actual decoded H.264 luma-temporal witnesses, no learned oracle.

This read-only research audit analyzes the SOURCE 3D joint-frame displacement
and grayscale (64x64 downsampled) H264 frame differences for 22 original-rights
synthetic cases in the independently qualified nine-fix candidate. It emits
candidate review rankings, NOT physics, video realism or identity judgements.
All original/negative-control media bytes remain unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

FAMILIES={"locomotion":8,"exercise_pose":7,"dance_combat":5,"aquatic":2}
FRAMES=40
FPS=20
IMAGE_SIDE=64
PIXELS=IMAGE_SIDE*IMAGE_SIDE
SCHEMA="scp.visualqa.ninefix-source-to-decoded-h264-luma.v1"

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def safe_json(path:Path):
    if path.stat().st_size>5_000_000:raise ValueError("UNTRUSTWORTHY_JSON_SIZE")
    return json.loads(path.read_text())

def verify_assets(folder:Path,item:dict):
    case=item["case"]
    if not isinstance(case,str) or not case or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in case):
        raise ValueError("UNTRUSTWORTHY_SOURCE_CASE")
    if len(item.get("videos",[]))!=1:
        raise ValueError("VIDEO_COUNT_MISMATCH")
    for meta,suffix in ((item["model"],".glb"),(item["ground_truth"],"_ground_truth.json"),(item["videos"][0],"_side.mp4")):
        filename=case+suffix
        if meta.get("file")!=filename or sha(folder/filename)!=meta.get("sha256"):
            raise ValueError("NINEFIX_MEDIA_SHA_OR_PATH_CHANGED")
    return folder/(case+"_ground_truth.json"),folder/(case+"_side.mp4")

def joint_velocity_series(doc:dict,case:str):
    frames=doc.get("frames")
    if (doc.get("schema")!="scp.expanded-original-3d-motion-labels.v1"
        or doc.get("case")!=case or doc.get("fps")!=FPS
        or not isinstance(frames,list) or len(frames)!=FRAMES):
        raise ValueError("GT_SCHEMA_CLOCK_CASE_MISMATCH")
    keys=None
    prior=None
    rates=[]
    for i,fr in enumerate(frames):
        if fr.get("frame")!=i or abs(fr.get("time_s",-99)-i/FPS)>1e-6:
            raise ValueError("GT_FRAME_INDEX_OR_TIME_DRIFT")
        joints=fr.get("joints")
        if not isinstance(joints,dict) or not joints:
            raise ValueError("SOURCE_JOINTS_ABSENT")
        if keys is None:
            keys=set(joints)
            if len(keys)>256:raise ValueError("JOINT_COUNT_UNBOUNDED")
        if set(joints)!=keys:raise ValueError("JOINT_SET_CHANGED")
        for p in joints.values():
            if len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in p):
                raise ValueError("NONFINITE_SOURCE_POSITION")
        if prior is not None:
            avg=sum(math.dist(joints[j],prior[j]) for j in keys)/len(keys)
            rates.append(FPS*avg)
        prior=joints
    if len(rates)!=FRAMES-1:raise AssertionError("SOURCE_TRANSITION_COUNT")
    return rates,len(keys)

def pixel_delta(a:bytes,b:bytes):
    if len(a)!=len(b) or not a:raise ValueError("BAD_DECODED_FRAME_PAIR")
    return sum(abs(x-y) for x,y in zip(a,b))/(len(a)*255.)

def pearson(a:list[float],b:list[float]):
    if len(a)!=len(b) or not a:raise ValueError("SERIES_LENGTH_MISMATCH")
    ma=sum(a)/len(a);mb=sum(b)/len(b)
    x=[z-ma for z in a];y=[z-mb for z in b]
    sx=sum(z*z for z in x);sy=sum(z*z for z in y)
    if sx<1e-16 or sy<1e-16:return None
    return max(-1.,min(1.,sum(p*q for p,q in zip(x,y))/math.sqrt(sx*sy)))

def decoded_luma_series(video:Path):
    probe=subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=codec_name,avg_frame_rate,nb_frames,width,height",
        "-of","json",str(video)],capture_output=True,text=True,timeout=20,check=True)
    streams=json.loads(probe.stdout)["streams"]
    if len(streams)!=1:raise ValueError("NOT_ONE_H264_STREAM")
    stream=streams[0]
    if (stream.get("codec_name")!="h264" or stream.get("avg_frame_rate")!="20/1"
        or stream.get("nb_frames")!="40" or stream.get("width")!=320 or stream.get("height")!=320):
        raise ValueError("NINEFIX_DECODED_VIDEO_IDENTITY_OR_CLOCK_WRONG")
    decoded=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
        "-i",str(video),"-vf",f"scale={IMAGE_SIDE}:{IMAGE_SIDE}:flags=area,format=gray",
        "-vsync","0","-an","-f","rawvideo","-pix_fmt","gray","-"],
        capture_output=True,timeout=35,check=True)
    raw=decoded.stdout
    if len(raw)!=FRAMES*PIXELS:
        raise ValueError("NOT_40_ACTUALLY_DECODED_LUMA_FRAMES")
    frames=[raw[i*PIXELS:(i+1)*PIXELS] for i in range(FRAMES)]
    changes=[pixel_delta(frames[i-1],frames[i]) for i in range(1,FRAMES)]
    return changes,hashlib.sha256(raw).hexdigest(),len(set(frames))

def rank_reviews(source_rates:list[float],luma_deltas:list[float],top:int=5):
    if len(source_rates)!=len(luma_deltas) or not source_rates:raise ValueError("MISSING_PAIRED_SOURCE_VIDEO")
    smax=max(source_rates);pmax=max(luma_deltas)
    # Dimensionless qualitative review ordering only. Neither modality is a
    # calibrated physical/pixel oracle; do not call high value an actual defect.
    results=[]
    for i,(s,p) in enumerate(zip(source_rates,luma_deltas),start=1):
        normalized_source=s/smax if smax>0 else 0.
        normalized_video=p/pmax if pmax>0 else 0.
        results.append({"transition_end_frame":i,
                       "source_mean_joint_speed_m_s":round(s,8),
                       "decoded_mean_abs_gray_delta_fraction":round(p,8),
                       "uncalibrated_source_minus_video_rank":round(normalized_source-normalized_video,8)})
    return sorted(results,key=lambda r:(-r["uncalibrated_source_minus_video_rank"],r["transition_end_frame"]))[:top]

def evaluate(root:Path,family:str):
    if family not in FAMILIES:raise ValueError("UNADMITTED_FAMILY")
    folder=Path(root)/family
    manifest=safe_json(folder/"manifest.json")
    if (manifest.get("schema")!="scp.expanded-original-3d-motion-corpus.v1"
        or manifest.get("batch")!=family
        or manifest.get("rights")!="CC0-1.0 for original generated files"
        or manifest.get("frames")!=FRAMES or manifest.get("fps")!=FPS
        or len(manifest.get("cases",[]))!=FAMILIES[family]):
        raise ValueError("NINEFIX_SOURCE_MANIFEST_DRIFT")
    out=[]
    for item in manifest["cases"]:
        gt,mp4=verify_assets(folder,item)
        velocities,joint_count=joint_velocity_series(safe_json(gt),item["case"])
        pixels,decoded_sha,unique=decoded_luma_series(mp4)
        if len(velocities)!=len(pixels)!=39:raise AssertionError("BAD_TIME_COUPLING")
        out.append({"case":item["case"],
                    "source_ground_truth_sha256":item["ground_truth"]["sha256"],
                    "source_glb_sha256":item["model"]["sha256"],
                    "source_h264_sha256":item["videos"][0]["sha256"],
                    "decoded_64px_luma_sha256":decoded_sha,
                    "source_joint_count":joint_count,
                    "actual_decoded_frames":FRAMES,
                    "unique_decoded_64px_grayscale_frames":unique,
                    "source_mean_joint_velocity_m_s":{"max":round(max(velocities),8),
                         "mean":round(sum(velocities)/len(velocities),8)},
                    "decoded_mean_abs_luma_delta_fraction":{"max":round(max(pixels),8),
                         "mean":round(sum(pixels)/len(pixels),8)},
                    "source_video_transition_pearson_r":pearson(velocities,pixels),
                    "identical_downsampled_adjacent_frames":sum(x==0 for x in pixels),
                    "top_uncalibrated_temporal_review_frames":rank_reviews(velocities,pixels),
                    "verdict":"NUMERIC_DIAGNOSTIC_NOT_REALISM_ACCEPTANCE"})
    if len({x["case"] for x in out})!=len(out):raise ValueError("DUPLICATE_CASES")
    return {"schema":SCHEMA,"family":family,"case_count":len(out),
            "manifest_sha256":sha(folder/"manifest.json"),"cases":out,
            "measurement":{"render_luma_resolution":"64x64 gray","frames":FRAMES,
                           "sample_rate_fps":FPS,"unit":"mean absolute 8-bit gray/255"},
            "disposition":"RESEARCH_TRIAGE_ONLY",
            "limitations":["8-bit gray downsample does not diagnose fine texture, frame artifacts, human motion or anatomy",
                           "Source mean-joint motion differs from visible projected pixel motion due to camera, occlusion and styling",
                           "Correlation and review rank are descriptive not scientific pass/fail; static intentionally posed scenes may be correct",
                           "No source media modification, original controls remain unchanged"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--family",required=True,choices=FAMILIES)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    d=evaluate(Path(a.root),a.family)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
    print("ACTUAL_H264_SOURCE_TO_LUMA_REVIEW",a.family,len(d["cases"]),
          [(x["case"],x["identical_downsampled_adjacent_frames"],
            x["source_video_transition_pearson_r"]) for x in d["cases"]])

if __name__=="__main__":
    main()
