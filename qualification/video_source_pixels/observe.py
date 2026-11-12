#!/usr/bin/env python3
"""Independent source->decoded-H264 original ankle fiducial alignment witness.

Reads previously generated CC0-rights original corpus; never synthesizes its
own "ground truth" from the video. Measures the *deliberately drawn* pale ankle
ring in 320x320 H264 frames against calibrated source 3D projections. Ankle
markers are not evidence of human anatomy, physics or identity fidelity.
Python stdlib and FFmpeg only; report original source SHA and decoded RGB SHA.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

BATCH_COUNTS={"locomotion":8,"exercise_pose":7,"dance_combat":5,"aquatic":2}
FRAME_IDS=tuple(range(0,40,5))
D=320
EXPECTED=(210,207,199)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def dot(a,b):
    return sum(x*y for x,y in zip(a,b))

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def normalize(a):
    s=math.sqrt(dot(a,a))
    if s<=0 or not math.isfinite(s):
        raise ValueError("DEGENERATE_CAMERA")
    return tuple(x/s for x in a)

def project(pt):
    if len(pt)!=3 or any(type(v) not in (float,int) or not math.isfinite(v) for v in pt):
        raise ValueError("BAD_SOURCE_POINT")
    eye=(.6,-4.8,1.95)
    target=(.50,0.,1.)
    forward=normalize(tuple(t-e for t,e in zip(target,eye)))
    right=normalize(cross(forward,(0.,0.,1.)))
    up=normalize(cross(right,forward))
    rel=tuple(p-e for p,e in zip(pt,eye))
    dep=dot(rel,forward)
    if dep<=.05:
        raise ValueError("BEHIND_CAMERA")
    return (D/2+520*dot(rel,right)/dep,D/2-520*dot(rel,up)/dep)

def marker_signature(frame,x,y):
    """Measure source-renderer pale ring at 24 perimeter angles with radial slack."""
    if len(frame)!=D*D*3:
        raise ValueError("BAD_DECODED_FRAME_SHAPE")
    if not all(math.isfinite(v) for v in (x,y)):
        raise ValueError("BAD_PROJECTED_POINT")
    if not (13<=x<D-13 and 13<=y<D-13):
        return {"verdict":"UNKNOWN","reason":"MARKER_OFFFRAME","angular_hits":0}
    angular_hits=0
    for i in range(24):
        angle=2*math.pi*i/24
        match=False
        for radius in (9,10,11):
            px=int(round(x+radius*math.cos(angle)))
            py=int(round(y+radius*math.sin(angle)))
            k=3*(py*D+px)
            color=frame[k:k+3]
            if max(abs(int(a)-int(b)) for a,b in zip(color,EXPECTED))<=38:
                match=True
                break
        angular_hits+=int(match)
    return {"verdict":"DETECTED" if angular_hits>=7 else "NOT_DETECTED",
            "angular_hits":angular_hits, "angular_samples":24}

def bounded_read(path,limit=5_000_000):
    p=Path(path)
    if not p.is_file() or p.stat().st_size>limit:
        raise ValueError("MISSING_OR_OVERSIZE_FILE")
    return p.read_bytes()

def decode_sampled(video):
    proc=subprocess.run([
       "ffmpeg","-nostdin","-hide_banner","-loglevel","error","-i",str(video),
       "-map","0:v:0","-vf",r"select=not(mod(n\,5))","-fps_mode","passthrough",
       "-f","rawvideo","-pix_fmt","rgb24","pipe:1"],
       stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60,check=True)
    raw=proc.stdout
    if len(raw)!=len(FRAME_IDS)*D*D*3:
        raise ValueError("INVALID_DECODED_FRAME_COUNT")
    return raw

def evaluate_batch(root,batch):
    if batch not in BATCH_COUNTS:raise ValueError("UNKNOWN_ADMITTED_BATCH")
    root=Path(root)
    folder=(root/batch).resolve(strict=True)
    if not folder.is_relative_to(root.resolve(strict=True)):
        raise ValueError("PATH_ESCAPES_ROOT")
    manifest=json.loads(bounded_read(folder/"manifest.json"))
    if manifest.get("schema")!="scp.expanded-original-3d-motion-corpus.v1" or manifest.get("batch")!=batch:
        raise ValueError("MANIFEST_SCHEMA_OR_BATCH_MISMATCH")
    if manifest.get("rights")!="CC0-1.0 for original generated files" or len(manifest.get("cases",[]))!=BATCH_COUNTS[batch]:
        raise ValueError("RIGHTS_OR_CASE_COUNT_FAILURE")
    observations=[]
    for item in manifest["cases"]:
        name=item["case"]
        if type(name) is not str or not name or any(z not in "abcdefghijklmnopqrstuvwxyz0123456789_" for z in name):
            raise ValueError("INVALID_CASE_NAME")
        video=folder/(name+"_side.mp4")
        labels=folder/(name+"_ground_truth.json")
        glb=folder/(name+".glb")
        if item["videos"][0]["file"]!=video.name or item["ground_truth"]["file"]!=labels.name or item["model"]["file"]!=glb.name:
            raise ValueError("SOURCE_MANIFEST_PATH_MISMATCH")
        data=bounded_read(labels); video_bytes=bounded_read(video); model_bytes=bounded_read(glb)
        if sha(data)!=item["ground_truth"]["sha256"] or sha(video_bytes)!=item["videos"][0]["sha256"] or sha(model_bytes)!=item["model"]["sha256"]:
            raise ValueError("SOURCE_SHA256_CUSTODY_FAILURE")
        doc=json.loads(data)
        if doc.get("case")!=name or doc.get("fps")!=20 or len(doc.get("frames",[]))!=40:
            raise ValueError("FRAME_SOURCE_CUSTODY_FAILURE")
        raw=decode_sampled(video)
        seen=[]
        for idx,fid in enumerate(FRAME_IDS):
            sample=raw[idx*D*D*3:(idx+1)*D*D*3]
            row={"frame":fid,"time_s":fid/20.0}
            for side in ("left","right"):
                xyz=doc["frames"][fid]["joints"][side+"_ankle"].copy()
                xyz[2]=max(xyz[2],.005)  # original ring renderer does the same
                x,y=project(xyz)
                row[side]={"projected_xy":[round(x,5),round(y,5)],
                           **marker_signature(sample,x,y)}
            seen.append(row)
        observations.append({
           "case":name, "source_labels_sha256":sha(data),
           "animated_glb_sha256":sha(model_bytes),"h264_sha256":sha(video_bytes),
           "decoded_sampled_rgb_sha256":sha(raw),
           "sampled":seen,
           "detected":sum(r[s]["verdict"]=="DETECTED" for r in seen for s in ("left","right")),
           "unknown":sum(r[s]["verdict"]=="UNKNOWN" for r in seen for s in ("left","right")),
           "not_detected":sum(r[s]["verdict"]=="NOT_DETECTED" for r in seen for s in ("left","right")),
        })
    return {"schema":"scp.original-3d-decoded-pixel-fiducial-custody.v1","batch":batch,
            "case_count":len(observations),"case_ids":sorted(x["case"] for x in observations),
            "frames_per_case":len(FRAME_IDS),"observations":observations,
            "counts":{k:sum(x[k] for x in observations) for k in ("detected","unknown","not_detected")},
            "science":"FIDUCIAL_CUSTODY_ONLY_NO_BIOMECHANICS_ACCEPTANCE",
            "limitations":["Marker deliberately painted after body rendering; detection does not prove anatomically correct ankle",
                           "Occluded/offframe projected source joints may be UNKNOWN; do not silently relabel",
                           "H264 compression and anti-aliasing can produce false negative or false positive pale rings",
                           "Source projected joints may violate anatomical constraints"]}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--root",required=True)
    a.add_argument("--batch",required=True,choices=BATCH_COUNTS.keys())
    a.add_argument("--out",required=True)
    v=a.parse_args()
    report=evaluate_batch(v.root,v.batch)
    Path(v.out).write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("ACTUAL_H264_SOURCE_PIXELS",v.batch,report["case_count"],report["counts"])

if __name__=="__main__":
    main()
