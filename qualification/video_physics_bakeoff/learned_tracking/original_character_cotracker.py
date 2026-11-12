#!/usr/bin/env python3
"""Real pretrained CoTracker3 on rights-original Stable Character GLB-derived H264.

Source-projected joint-vs-independently inferred pixel-point comparison.
Science output is explicitly diagnostic, not an acceptance grade or physics model.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

SOURCE_COMMIT = "82e02e8029753ad4ef13cf06be7f4fc5facdda4d"
MODEL_SHA = "2670d4562ed69326dda775a26e54883925cd11b6fc9b24cb7aa9f8078bce7834"
FRAMES = tuple(range(0, 36, 3))
DIM = 128
ALLOWED = (
    "male_walk_barefoot",
    "female_walk_high_heels",
    "male_jump_slippers",
    "female_judo_kata_barefoot",
)

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for part in iter(lambda: fh.read(1024*1024), b""):
            h.update(part)
    return h.hexdigest()

def dot(a, b):
    return sum(x*y for x,y in zip(a,b))

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def unit(v):
    length = math.sqrt(dot(v,v))
    if not (length > 0 and math.isfinite(length)):
        raise ValueError("DEGENERATE_CAMERA")
    return tuple(x/length for x in v)

def original_side_camera_project(point):
    """Read back exact original procedural renderer side-view geometric projection."""
    eye = (.60, -4.8, 1.95)
    target = (.50, 0., 1.)
    forward = unit(tuple(a-b for a,b in zip(target,eye)))
    right = unit(cross(forward,(0.,0.,1.)))
    up = unit(cross(right,forward))
    if len(point)!=3 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in point):
        raise ValueError("NONFINITE_SOURCE_JOINT")
    rel = tuple(a-b for a,b in zip(point,eye))
    depth = dot(rel,forward)
    if depth <= .05:
        raise ValueError("SOURCE_POINT_BEHIND_CAMERA")
    xx = (160. + 520.*dot(rel,right)/depth) * (DIM/320.)
    yy = (160. - 520.*dot(rel,up)/depth) * (DIM/320.)
    if not (0 <= xx < DIM and 0 <= yy < DIM):
        raise ValueError("PROJECTED_JOINT_OUT_OF_FRAME")
    return (xx, yy)

def inspect_case(root, name):
    if name not in ALLOWED:
        raise ValueError("UNADMITTED_CASE")
    batch = "dance_combat" if "judo" in name else "locomotion"
    folder = (Path(root)/batch).resolve(strict=True)
    man = json.loads((folder/"manifest.json").read_text())
    if man.get("schema")!="scp.expanded-original-3d-motion-corpus.v1" or man.get("batch")!=batch:
        raise ValueError("INVALID_ORIGINAL_SOURCE_MANIFEST")
    if man.get("rights")!="CC0-1.0 for original generated files":
        raise ValueError("RIGHTS_NOT_ORIGINAL_PUBLIC")
    matches = [item for item in man["cases"] if item["case"]==name]
    if len(matches)!=1:
        raise ValueError("MISSING_OR_DUPLICATE_CASE")
    case=matches[0]
    videofile=folder/(name+"_side.mp4")
    label=folder/(name+"_ground_truth.json")
    if len(case["videos"])!=1 or case["videos"][0]["file"]!=videofile.name:
        raise ValueError("VIDEO_MANIFEST_DISAGREEMENT")
    if case["ground_truth"]["file"]!=label.name:
        raise ValueError("LABEL_MANIFEST_DISAGREEMENT")
    if digest(videofile)!=case["videos"][0]["sha256"] or digest(label)!=case["ground_truth"]["sha256"]:
        raise ValueError("ORIGINAL_SOURCE_SHA256_MISMATCH")
    data=json.loads(label.read_text())
    if data.get("schema")!="scp.expanded-original-3d-motion-labels.v1" or data.get("fps")!=20:
        raise ValueError("GROUND_TRUTH_SCHEMA_OR_FPS")
    if len(data["frames"])!=40 or data.get("case")!=name or data["spec"]!=case["spec"]:
        raise ValueError("GROUND_TRUTH_FRAME_OR_SPEC_MISMATCH")
    coords=[original_side_camera_project(data["frames"][i]["joints"]["left_ankle"]) for i in FRAMES]
    return videofile,label,coords

def decode_select(video):
    # 0,3,...,33 are known-source frame indices; FFmpeg decodes genuine H264 into RGB.
    args=("ffmpeg","-nostdin","-hide_banner","-loglevel","error","-i",str(video),
          "-map","0:v:0","-vf",r"select=not(mod(n\,3))*lt(n\,36),scale=128:128",
          "-fps_mode","passthrough","-pix_fmt","rgb24","-f","rawvideo","pipe:1")
    raw=subprocess.run(args,check=True,capture_output=True,timeout=60).stdout
    if len(raw)!=len(FRAMES)*DIM*DIM*3:
        raise ValueError("ACTUAL_DECODED_RGB_FRAME_COUNT_INVALID")
    return raw

def run(source, checkpoint, root, out):
    import numpy as np
    import torch
    if torch.cuda.is_available():
        raise ValueError("CPU_ONLY_LANE")
    if digest(checkpoint)!=MODEL_SHA or Path(checkpoint).stat().st_size!=101890938:
        raise ValueError("PINNED_MODEL_BYTES_INVALID")
    if not (Path(source)/"cotracker"/"predictor.py").is_file():
        raise ValueError("PINNED_MODEL_SOURCE_NOT_PRESENT")
    torch.set_num_threads(2)
    sys.path.insert(0,str(Path(source).resolve()))
    from cotracker.predictor import CoTrackerPredictor
    model=CoTrackerPredictor(checkpoint=str(checkpoint),offline=True,window_len=60).eval().cpu()
    rows=[]
    for name in ALLOWED:
        video,labels,source_points=inspect_case(root,name)
        rgb=decode_select(video)
        array=np.frombuffer(rgb,dtype=np.uint8).copy().reshape(len(FRAMES),DIM,DIM,3)
        tensor=torch.from_numpy(array).permute(0,3,1,2).unsqueeze(0).float()
        x,y=source_points[0]
        queries=torch.tensor([[[0.,x,y]]],dtype=torch.float32)
        started=time.monotonic()
        with torch.inference_mode():
            tracks,vis=model(tensor,queries=queries)
        duration=time.monotonic()-started
        inferred=tracks[0,:,0,:].cpu().tolist()
        observed=[bool(z) for z in vis[0,:,0].cpu().tolist()]
        if len(inferred)!=len(FRAMES) or len(observed)!=len(FRAMES):
            raise ValueError("INFERENCE_FRAME_COUNT_DISAGREEMENT")
        errs=[]
        for point,seen,gt in zip(inferred,observed,source_points):
            if len(point)!=2 or any(not math.isfinite(float(z)) for z in point):
                raise ValueError("MODEL_INFERENCE_NONFINITE")
            errs.append(round(math.dist(point,gt),4) if seen else None)
        finite=[n for n in errs if n is not None]
        row=dict(case=name,original_h264_sha256=digest(video),source_joint_labels_sha256=digest(labels),
                 decoded_selected_rgb_sha256=hashlib.sha256(rgb).hexdigest(),
                 source_projected_left_ankle_xy=source_points,pretrained_tracking_xy=inferred,
                 pretrained_predicted_visible=observed,per_sample_visible_residual_px=errs,
                 visible_frames=len(finite),mean_observed_residual_px=round(sum(finite)/len(finite),4) if finite else None,
                 model_seconds=round(duration,3), scientific_status="OBSERVED_NO_REALISM_GRADE")
        rows.append(row)
        print("ACTUAL_CHARACTER_TRACKING",name,"VISIBLE",len(finite),"MAE",row["mean_observed_residual_px"],flush=True)
    result=dict(schema="scp.cotracker3.original-character-joint-projection.v1",
                pretrained_inference="REAL_CHECKPOINT_EXECUTED",source_git_sha=SOURCE_COMMIT,
                checkpoint_sha256=MODEL_SHA,license="CC BY-NC 4.0 research only",
                evaluator_sha256=digest(__file__),torch_version=str(torch.__version__),device="cpu",
                case_count=len(rows),sampled_original_frame_indices=FRAMES,
                observations=rows,qualification="RDT_E_OBSERVATIONS_NOT_ACCEPTANCE",
                limits=[
                    "Source 3D geometry can be defective; projected joint positions are not biomechanical ground truth",
                    "One left ankle point on low-resolution stylized original synthetic video per case",
                    "Uncertain visibility and occlusion make no observation equivalent to UNKNOWN",
                    "Tracking error against rendered source is not a video physics or stable identity score",
                    "Research/noncommercial checkpoint not admitted for production or redistribution",
                ])
    Path(out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def main():
    p=argparse.ArgumentParser()
    for key in ("source","checkpoint","root","out"):
        p.add_argument("--"+key,required=True)
    a=p.parse_args()
    try:
        run(a.source,a.checkpoint,a.root,a.out)
    except Exception as exc:
        print("ORIGINAL_CHARACTER_LEARNED_MODEL_ERROR="+type(exc).__name__+":"+str(exc)[:160],file=sys.stderr)
        raise

if __name__=="__main__":
    main()
