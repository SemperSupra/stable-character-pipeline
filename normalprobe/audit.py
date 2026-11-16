#!/usr/bin/env python3
"""R059 independent real OpenEXR normal pixel orientation vs native mesh ray normals.

Only original synthetic fixture. Face orientation/unit checks are not physical
shading-normal accuracy, normal-map realism, anatomical structure or human intent.
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

MIN_STABLE=64
MIN_FINITE_FRACTION=0.98
MIN_FACING_FRACTION=0.85
NORMAL_MIN_LENGTH=0.8
NORMAL_MAX_LENGTH=1.2
ORIGINAL=ROOT/"renderlab"/"synthetic_scene.py"
PERSPECTIVE=ROOT/"perspprobe"/"scene.py"

def reject(msg):
    raise ValueError("R059_NORMAL_PASS_HOLD_"+msg)

def sha(path):
    if path.is_symlink() or not path.is_file() or not 100<=path.stat().st_size<=16*1024*1024:
        reject("UNSAFE_SOURCE_OR_RENDER")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def validate(m):
    if not isinstance(m,dict) or m.get("schema")!="r059.original.synthetic.shading_normals.v1" or m.get("status")!="NATIVE_GEOMETRY_CAPTURE_PENDING_INDEPENDENT_EXR":
        reject("SCHEMA_OR_STATUS")
    if m.get("rights")!="ORIGINAL_SYNTHETIC" or m.get("qualification")!="NOT_REAL_HUMAN_PHYSICS_OR_ANATOMY":
        reject("FALSE_SOURCE_RIGHTS_OR_HUMAN_CLAIM")
    if m.get("scene_id")!="original-synthetic-head-v1":
        reject("SOURCE_SCENE")
    if m.get("source_script_sha256")!=sha(ORIGINAL) or m.get("perspective_script_sha256")!=sha(PERSPECTIVE):
        reject("SOURCE_SHA")
    camera=m.get("camera")
    if not isinstance(camera,dict) or camera.get("type")!="PERSP" or camera.get("lens_mm")!=65.0 or camera.get("sensor_width_mm")!=36.0 or camera.get("resolution")!=[256,256] or camera.get("shift_x")!=0.0 or camera.get("shift_y")!=0.0:
        reject("CAMERA_CONTRACT")
    if m.get("camera_sha256")!=persp.canonical_hash(camera):
        reject("CAMERA_SHA")
    if not isinstance(m.get("geometry_sha256"),str) or len(m["geometry_sha256"])!=64:
        reject("MESH_SOURCE_SHA")
    rays=m.get("source_rays")
    if not isinstance(rays,list) or not 64<=len(rays)<=256:
        reject("SAMPLE_SET")
    points=set();stable=0
    for ray in rays:
        if not isinstance(ray,dict):reject("RAY_TYPE")
        x,y=ray.get("x"),ray.get("y")
        if type(x) is not int or type(y) is not int or not(0<=x<256 and 0<=y<256) or (x-8)%16 or (y-8)%16 or (x,y) in points:
            reject("RAY_GRID")
        points.add((x,y))
        if type(ray.get("stable")) is not bool:reject("RAY_STABILITY_TYPE")
        if type(ray.get("pass_index")) is not int or ray["pass_index"] not in (1,2):
            reject("OBJECT_INDEX")
        n=ray.get("geometric_normal")
        if not isinstance(n,list) or len(n)!=3 or any(type(t) not in (float,int) or not math.isfinite(t) for t in n) or abs(sum(t*t for t in n)-1)>0.01:
            reject("NATIVE_GEOMETRIC_NORMAL")
        if ray["stable"]:stable+=1
    if stable!=m.get("source_stable_samples") or stable<MIN_STABLE:
        reject("INSUFFICIENT_STABLE_GEOMETRIC_WITNESS")
    arms=m.get("arms")
    if not isinstance(arms,dict) or set(arms)!={"baseline","physical_material"}:
        reject("INCOMPLETE_MATERIALS")
    for files in arms.values():
        if not isinstance(files,dict) or set(files)!={"beauty.png","render_passes.exr"}:
            reject("MISSING_ACTUAL_IMAGE")
        for meta in files.values():
            if not isinstance(meta,dict) or type(meta.get("bytes")) is not int or meta["bytes"]<=128 or not isinstance(meta.get("sha256"),str) or len(meta["sha256"])!=64:
                reject("BAD_RENDER_RECEIPT")
    return rays,arms

def analyze_normal(rays,normal):
    arr=np.stack([normal[c] for c in "XYZ"],axis=-1).astype(np.float64)
    if arr.shape!=(256,256,3):
        reject("NORMAL_SHAPE")
    total=0;finite=0;facing=0
    cosine=[]; lengths=[]
    for ray in rays:
        if not ray["stable"]:continue
        actual=arr[ray["y"],ray["x"]]
        total+=1
        if not np.all(np.isfinite(actual)):continue
        norm=float(np.linalg.norm(actual))
        if not NORMAL_MIN_LENGTH<=norm<=NORMAL_MAX_LENGTH:
            continue
        finite+=1
        source=np.asarray(ray["geometric_normal"],dtype=np.float64)
        dot=float(np.dot(source,actual)/norm)
        if not math.isfinite(dot):continue
        dot=max(-1.0,min(1.0,dot))
        if dot>0.0:facing+=1
        cosine.append(dot);lengths.append(norm)
    if total<MIN_STABLE or finite/total<MIN_FINITE_FRACTION:
        reject("INVALID_FINITE_UNIT_NORMALS")
    if facing/total<MIN_FACING_FRACTION:
        reject("NORMAL_PASS_DISAGREES_WITH_NATIVE_GEOMETRY_HEMISPHERE")
    return {"stable_native_rays":total,"finite_unit_length":finite,"facing_native_source":facing,
            "fraction_facing":facing/total,"min_source_dot":min(cosine),
            "median_source_dot":float(np.median(cosine)),
            "median_exr_normal_length":float(np.median(lengths)),
            "qualification":"ORIENTATION_HEMISPHERE_ONLY_NOT_EQUAL_SHADING_NORMAL"}

def audit(root):
    m=prior.strict_json(root/"r059_source.json")
    rays,arms=validate(m)
    decoded={}
    outcomes={}
    for arm in ("baseline","physical_material"):
        rendered=root/arm
        for filename,meta in arms[arm].items():
            file=rendered/filename
            if sha(file)!=meta["sha256"] or file.stat().st_size!=meta["bytes"]:
                reject("IMAGE_BYTE_CUSTODY")
        channels,summary=pixel_decode.decode(rendered/"render_passes.exr")
        if summary["sha256"]!=arms[arm]["render_passes.exr"]["sha256"]:
            reject("DECODED_NORMAL_EXR_CUSTODY")
        decoded[arm]=channels
        outcomes[arm]=analyze_normal(rays,channels["normal"])
        outcomes[arm]["exr_sha256"]=summary["sha256"]
    diffs=np.stack([
        np.abs(decoded["baseline"]["beauty"][c].astype(np.float64)-
               decoded["physical_material"]["beauty"][c].astype(np.float64))
        for c in "RGB"],axis=-1)
    changed=float(np.mean(np.any(diffs>2/255,axis=-1)))
    if not math.isfinite(changed) or changed<=0.001:reject("NO_SHADER_INTERVENTION")
    # One R059 observation: renderer normal pass may or may not encode microbump;
    # no assumption of comparable physical roughness is made.
    deltas=np.stack([
        np.abs(decoded["baseline"]["normal"][c].astype(np.float64)-
               decoded["physical_material"]["normal"][c].astype(np.float64))
        for c in "XYZ"],axis=-1)
    normal_change=float(np.mean(np.any(deltas>1e-3,axis=-1)))
    return {"schema":"r059.original.synthetic.normal_pixels.v1",
            "status":"PASS_NARROW_REAL_CYCLES_EXR_NORMAL_HEMISPHERE",
            "rights":"ORIGINAL_SYNTHETIC",
            "qualifier":"NOT_SHADING_NORMAL_TRUTH_PHOTOREALISM_OR_HUMAN",
            "source_manifest_sha256":sha(root/"r059_source.json"),
            "changed_beauty_pixel_fraction":changed,
            "normal_change_pixel_fraction_observed_only":normal_change,
            "arms":outcomes}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=audit(args.root)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(result,sort_keys=True),flush=True)
