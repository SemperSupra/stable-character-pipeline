#!/usr/bin/env python3
"""Independently observe original rendered ankle fiducial pixels, not model self-belief.

Consumes rights-original exact-sha source H264 and previously measured pretrained
CoTracker source-projected joint receipt. Pixel signature is an experimental
observation of the artificial ankle ring, never a human-pose/physics oracle.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

CASES = ("male_walk_barefoot","female_walk_high_heels",
         "male_jump_slippers","female_judo_kata_barefoot")
DIM = 128
SAMPLES = 12
def sha(data):
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    data = Path(path).read_bytes()
    if len(data)>4_000_000:
        raise ValueError("INPUT_TOO_LARGE")
    return json.loads(data)

def marker_signature(rgb, frame_i, xy):
    """11x11 window around source-projected ankle, independent decoded RGB."""
    if len(rgb)!=SAMPLES*DIM*DIM*3:
        raise ValueError("INVALID_DECODED_RGB")
    x,y=xy
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y)):
        raise ValueError("INVALID_PROJECTION")
    cx,cy=round(x),round(y)
    if not (5<=cx<DIM-5 and 5<=cy<DIM-5):
        raise ValueError("OUT_OF_FRAME")
    pale=0
    peak=0
    for dy in range(-5,6):
        for dx in range(-5,6):
            i=(frame_i*DIM*DIM + (cy+dy)*DIM + cx+dx)*3
            trip=rgb[i:i+3]
            r,g,b=trip
            peak=max(peak,int(r)+int(g)+int(b))
            if min(trip)>185 and max(trip)-min(trip)<45:
                pale+=1
    # Falsifiable signature of a pale overlay stroke rendered after body.
    return {"pale_pixels":pale, "max_rgb_sum":peak,
            "fiducial_observed":pale>=20 and peak>=630}

def decode_video(path):
    command=("ffmpeg","-nostdin","-hide_banner","-loglevel","error","-i",str(path),
             "-map","0:v:0","-vf",r"select=not(mod(n\,3))*lt(n\,36),scale=128:128",
             "-fps_mode","passthrough","-pix_fmt","rgb24","-f","rawvideo","pipe:1")
    res=subprocess.run(command,capture_output=True,check=True,timeout=60)
    if len(res.stdout)!=SAMPLES*DIM*DIM*3:
        raise ValueError("DECODED_FRAME_COUNT_MISMATCH")
    return res.stdout

def observe(root, learned):
    if learned.get("schema")!="scp.cotracker3.original-character-joint-projection.v1" or learned.get("pretrained_inference")!="REAL_CHECKPOINT_EXECUTED":
        raise ValueError("UNRECOGNIZED_LEARNED_RECEIPT")
    observations=learned.get("observations",[])
    if len(observations)!=4 or set(x.get("case") for x in observations)!=set(CASES):
        raise ValueError("CASE_CUSTODY_MISMATCH")
    rows=[]
    for name in CASES:
        item=next(x for x in observations if x["case"]==name)
        batch="dance_combat" if "judo" in name else "locomotion"
        folder=Path(root)/batch
        manifest=read_json(folder/"manifest.json")
        if manifest.get("schema")!="scp.expanded-original-3d-motion-corpus.v1" or manifest.get("rights")!="CC0-1.0 for original generated files":
            raise ValueError("ORIGINAL_RIGHTS_OR_SCHEMA")
        selected=[v for v in manifest["cases"] if v["case"]==name]
        if len(selected)!=1:
            raise ValueError("DUPLICATE_OR_MISSING_CASE")
        src=selected[0]
        path=folder/(name+"_side.mp4")
        clip=path.read_bytes()
        if sha(clip)!=src["videos"][0]["sha256"] or sha(clip)!=item["original_h264_sha256"]:
            raise ValueError("ACTUAL_VIDEO_SHA_CUSTODY_MISMATCH")
        rgb=decode_video(path)
        if sha(rgb)!=item["decoded_selected_rgb_sha256"]:
            raise ValueError("INDEPENDENT_DECODE_DISAGREES_WITH_LEARNED_INPUT")
        xy=item["source_projected_left_ankle_xy"]
        visible=item["pretrained_predicted_visible"]
        if len(xy)!=SAMPLES or len(visible)!=SAMPLES or not all(type(x) is bool for x in visible):
            raise ValueError("TRACK_OR_PROJECTION_LENGTH")
        scores=[marker_signature(rgb,i,xy[i]) for i in range(SAMPLES)]
        marker_obs=[s["fiducial_observed"] for s in scores]
        misses=sum(m and not v for m,v in zip(marker_obs,visible))
        rows.append({
            "case":name,"video_h264_sha256":sha(clip),"decoded_rgb_sha256":sha(rgb),
            "landmark_model_visible_frames":sum(visible),"pixel_fiducial_observed_frames":sum(marker_obs),
            "model_false_invisible_when_fiducial_observed":misses,
            "per_frame_pixel_signature":scores,
            "status":"RESEARCH_FIDUCIAL_OBSERVATION_NOT_HUMAN_GAIT_ACCEPTANCE",
        })
    return {
        "schema":"scp.original-h264-fiducial-observed-v1",
        "source":"independent_ffmpeg_decoded_rgb_near_source_projected_ankle",
        "method":"pale ring pixel signature with fail-closed threshold, not segmentation proof of anatomy",
        "case_count":len(rows),"samples_per_case":SAMPLES,"observations":rows,
        "total_predicted_visible":sum(x["landmark_model_visible_frames"] for x in rows),
        "total_pixel_fiducial_observed":sum(x["pixel_fiducial_observed_frames"] for x in rows),
        "total_model_false_invisible_when_fiducial_observed":sum(x["model_false_invisible_when_fiducial_observed"] for x in rows),
        "qualification":"DIAGNOSTIC_NOT_PHYSICS_OR_HUMAN_REALISM",
        "limitations":[
            "Pixel signature is for deliberately painted ring fiducials, not unmarked organic anatomy",
            "Marker presence is an image-derived heuristic with explicitly reported pale counts, not an independently learned anatomy oracle",
            "Model visibility is not a calibrated confidence and may decline on large true motions",
            "Reference projected joint comes from potentially invalid original 3D source motion",
        ],
    }

def main():
    a=argparse.ArgumentParser()
    for key in ("root","learned","out","markdown"):a.add_argument("--"+key,required=True)
    p=a.parse_args()
    learned=read_json(p.learned)
    result=observe(p.root,learned)
    Path(p.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    lines=["# Actual H264 fiducial visibility against pretrained CoTracker",
           "",
           "Experimental pixel observation of **artificial source-drawn ankle markers**, not human realism or physics acceptance.",
           "",
           "| Original synthetic case | Pale ankle marker observed | Learned predicted visible | Missed despite marker |",
           "|---|---:|---:|---:|"]
    for v in result["observations"]:
        lines.append("| "+v["case"]+" | "+str(v["pixel_fiducial_observed_frames"])+"/12 | "+
                     str(v["landmark_model_visible_frames"])+"/12 | "+
                     str(v["model_false_invisible_when_fiducial_observed"])+" |")
    lines.extend(["","Pixel signature and source/decoded input hashes are in the accompanying JSON. No production or biomechanical verdict."])
    Path(p.markdown).write_text("\n".join(lines)+"\n")
    print("ACTUAL_PIXEL_MARKER_VS_COTRACKER",result["total_pixel_fiducial_observed"],
          result["total_predicted_visible"],result["total_model_false_invisible_when_fiducial_observed"])

if __name__=="__main__":
    main()
