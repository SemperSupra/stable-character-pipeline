#!/usr/bin/env python3
"""R060 independent 3-frame source-mesh camera-axis-Z/ID and temporal uniqueness.

Controlled translation only, no skeleton, deformation skin, person, real gait,
physical contact or human preference. Runtime only source-safe public CPU.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import depthprobe.audit as prior
import perspprobe.audit as persp
from renderlab.exraudit import pixel_decode

OFFSETS={"0":0.0,"1":0.36,"2":-0.28}
HEAD_COUNT=13
MIN_CHANGE_FRACTION=0.01

def reject(msg):
    raise ValueError("R060_TEMPORAL_DEPTH_HOLD_"+msg)

def sha(path):
    if path.is_symlink() or not path.is_file() or not 100<=path.stat().st_size<=16*1024*1024:
        reject("UNSAFE_SOURCE_OR_RENDER")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()

def validate(m):
    if not isinstance(m,dict) or m.get("schema")!="r060.synthetic.pose_time.v1" or m.get("status")!="ORIGINAL_SOURCE_POSE_CAPTURE_ONLY":
        reject("MISSING_SOURCE_SCHEMA")
    if m.get("rights")!="ORIGINAL_SYNTHETIC" or m.get("qualification")!="NOT_RIGGED_SKIN_OR_HUMAN_MOTION":
        reject("FORGED_ADMISSION")
    if m.get("source_script_sha256")!=sha(ROOT/"renderlab"/"synthetic_scene.py") or m.get("perspective_script_sha256")!=sha(ROOT/"perspprobe"/"scene.py"):
        reject("SOURCE_SCRIPT_SHA")
    if m.get("scene_id")!="original-synthetic-head-v1" or m.get("motion_type")!="CONTROLLED_MULTI_OBJECT_RIGID_HEAD_TRANSLATION_NOT_SKIN":
        reject("UNADMITTED_MOTION")
    if m.get("exr_z_convention")!="CAMERA_AXIS_DEPTH_MINUS_LOCAL_Z":
        reject("WRONG_PERSPECTIVE_DEPTH_CONVENTION")
    camera=m.get("camera")
    if not isinstance(camera,dict) or camera.get("type")!="PERSP" or camera.get("lens_mm")!=65.0 or camera.get("resolution")!=[256,256] or camera.get("sensor_width_mm")!=36.0:
        reject("UNCONTROLLED_CAMERA")
    if m.get("camera_sha256")!=persp.canonical_hash(camera):
        reject("CAMERA_IDENTITY")
    names=m.get("head_mesh_names")
    if not isinstance(names,list) or len(names)!=HEAD_COUNT or len(set(names))!=HEAD_COUNT or "head" not in names or "nose" not in names:
        reject("SOURCE_HEAD_OBJECTS")
    frames=m.get("frames")
    if not isinstance(frames,dict) or set(frames)!=set(OFFSETS):
        reject("FRAME_SET_NOT_PREDECLARED")
    poses=set();geometry=set();source_total=0
    for key,delta in OFFSETS.items():
        f=frames[key]
        if type(f.get("frame_index")) is not int or f["frame_index"]!=int(key) or type(f.get("head_x_delta_source_units")) not in (int,float) or f["head_x_delta_source_units"]!=delta:
            reject("FRAME_INDEX_OR_OFFSET_TAMPER")
        if f.get("camera_sha256")!=m["camera_sha256"]:
            reject("CAMERA_MOVED_WITH_POSE")
        for kind,collection in (("pose_sha256",poses),("geometry_sha256",geometry)):
            value=f.get(kind)
            if not isinstance(value,str) or len(value)!=64 or value in collection:
                reject("DUPLICATE_POSE_GEOMETRY_OR_DIGEST")
            collection.add(value)
        rays=f.get("rays")
        if not isinstance(rays,list) or len(rays)>256 or len(rays)<64:
            reject("NO_NATIVE_FRAME_RAYS")
        seen=set();stable=0
        for r in rays:
            if not isinstance(r,dict):reject("RAY_OBJECT")
            x,y=r.get("x"),r.get("y")
            if type(x) is not int or type(y) is not int or not(0<=x<256 and 0<=y<256) or (x-8)%16 or (y-8)%16 or (x,y) in seen:
                reject("BAD_RAY_GRID")
            seen.add((x,y))
            if type(r.get("stable")) is not bool:reject("BAD_STABILITY")
            if type(r.get("pass_index")) is not int or r["pass_index"] not in (1,2):reject("BAD_RAY_ID")
            z=r.get("camera_axis_depth")
            length=r.get("ray_distance")
            if type(z) not in (float,int) or type(length) not in (float,int) or not math.isfinite(z) or not math.isfinite(length) or not 0<z<=length+1e-4<80.001:
                reject("NONFINITE_AXIS_RAY")
            if r["stable"]:stable+=1
        if stable!=f.get("stable_ray_count") or stable<64:
            reject("STABLE_RAY_COUNT")
        source_total+=stable
        files=f.get("files")
        if not isinstance(files,dict) or set(files)!={"beauty.png","render_passes.exr"}:
            reject("FRAME_RENDER_INCOMPLETE")
        for info in files.values():
            if not isinstance(info,dict) or type(info.get("bytes")) is not int or info["bytes"]<=128 or not isinstance(info.get("sha256"),str) or len(info["sha256"])!=64:
                reject("BAD_SOURCE_RENDER_CUSTODY")
    return frames,source_total

def verify(root):
    manifest=root/"r060_source.json"
    m=prior.strict_json(manifest)
    frames,total=validate(m)
    rows={};decoded={}
    for key,f in sorted(frames.items()):
        directory=root/("frame_%02d"%int(key))
        for name,info in f["files"].items():
            target=directory/name
            if sha(target)!=info["sha256"] or target.stat().st_size!=info["bytes"]:
                reject("FILE_TAMPER_"+key)
        pix,meta=pixel_decode.decode(directory/"render_passes.exr")
        decoded[key]=pix
        if meta["sha256"]!=f["files"]["render_passes.exr"]["sha256"]:
            reject("EXR_PIXEL_SOURCE_UNBOUND")
        row=persp.compare_axial_depth(f["rays"],pix)
        row["pose_sha256"]=f["pose_sha256"]
        row["geometry_sha256"]=f["geometry_sha256"]
        row["exr_sha256"]=meta["sha256"]
        rows[key]=row
    changes={}
    for key in ("1","2"):
        first=decoded["0"];second=decoded[key]
        diff=np.stack([np.abs(first["beauty"][c].astype(np.float64)-second["beauty"][c].astype(np.float64)) for c in "RGB"],axis=-1)
        fraction=float(np.mean(np.any(diff>2/255,axis=-1)))
        if not math.isfinite(fraction) or fraction<MIN_CHANGE_FRACTION:
            reject("NO_REAL_RENDERED_FRAME_DIFFERENCE_"+key)
        changes["0_to_"+key]=fraction
    return {"schema":"r060.original.synthetic.temporal.z.v1",
            "status":"PASS_NARROW_REAL_MOVING_MESH_DEPTH_BY_FRAME",
            "qualification":"NOT_BONED_RIG_SKIN_CONTACT_OR_HUMAN_GAIT",
            "rights":"ORIGINAL_SYNTHETIC",
            "source_manifest_sha256":sha(manifest),
            "source_native_stable_total":total,
            "frame_count":3,
            "changed_beauty_fraction":changes,
            "frames":rows}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    report=verify(args.root)
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(report,sort_keys=True),flush=True)
