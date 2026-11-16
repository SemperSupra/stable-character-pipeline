#!/usr/bin/env python3
"""R045 independent *numerical* depth/ID oracle for real Blender Cycles EXR.
Blender scene.ray_cast rays are a second geometry algorithm, but use the same
scene representation. Claims are limited to synthetic image/geometry agreement.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"renderlab"/"exraudit"))
import pixel_decode

SIDE=256
DEPTH_TOLERANCE=0.05
OBJECT_TOLERANCE=0.01
MIN_STABLE_RAYS=64
MIN_CORRECT_FRACTION=0.98

def reject(msg):
    raise ValueError("R045_RAY_ORACLE_HOLD_"+msg)

def sha(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>32*1024*1024:
        reject("UNSAFE_OR_MISSING_FILE")
    return hashlib.sha256(path.read_bytes()).hexdigest()

def strict_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>512*1024:
        reject("UNSAFE_OR_MISSING_JSON")
    def duplicates(pairs):
        d={}
        for k,v in pairs:
            if k in d:reject("DUPLICATE_KEY")
            d[k]=v
        return d
    return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=duplicates,
                      parse_constant=lambda _:reject("NONFINITE_JSON"))

def validate_oracle(m, light):
    if m.get("schema")!="r045.ortho.raycast.v1" or m.get("status")!="ORIGINAL_SCENE_RAYCAST_CAPTURE_ONLY":
        reject("FORGED_STATUS_OR_SCHEMA")
    if m.get("rights")!="ORIGINAL_SYNTHETIC" or m.get("qualification")!="NOT_INDEPENDENT_RENDER_PASS_VALIDATION_YET":
        reject("BAD_RIGHTS_OR_QUALIFICATION")
    if m.get("camera_type")!="ORTHO" or m.get("pixel_convention")!="top-left pixel centers, 256x256":
        reject("WRONG_CAMERA_MODEL")
    if m.get("depth_hypothesis")!="camera-plane-forward-ray-parameter-meters-in-uncalibrated-scene-units":
        reject("UNADMITTED_DEPTH_HYPOTHESIS")
    if m.get("sample_stride")!=16 or m.get("scene_id")!="original-synthetic-head-v1":
        reject("UNRECOGNIZED_SOURCE_FIXTURE")
    if m.get("lighting_manifest_sha256")!=sha(light):
        reject("LIGHTING_RECEIPT_UNBOUND")
    l=strict_json(light)
    cases=l.get("scenarios",{})
    if set(cases)!={"diffuse_soft","directional_hard"}:
        reject("LIGHTING_MATRIX_MISSING")
    for name in cases:
        if cases[name].get("geometry_sha256")!=m.get("source_geometry_sha256") or cases[name].get("camera_sha256")!=m.get("source_camera_sha256"):
            reject("SOURCE_GEOMETRY_CAMERA_DISAGREEMENT")
    rays=m.get("rays")
    if not isinstance(rays,list) or len(rays)>256 or len(rays)<MIN_STABLE_RAYS:
        reject("WRONG_SAMPLE_SET")
    points=set()
    stable=0
    for r in rays:
        x,y=r.get("x"),r.get("y")
        if type(x) is not int or type(y) is not int or not(0<=x<SIDE and 0<=y<SIDE):
            reject("INVALID_PIXEL")
        if (x-8)%16 or (y-8)%16 or (x,y) in points:
            reject("OFFGRID_DUPLICATE_PIXEL")
        points.add((x,y))
        if type(r.get("stable")) is not bool: reject("BAD_STABILITY_FLAG")
        if type(r.get("pass_index")) is not int or r["pass_index"] not in (1,2):
            reject("UNAPPROVED_OBJECT_ID")
        depth=r.get("depth_from_camera_plane")
        if type(depth) not in (float,int) or not math.isfinite(depth) or not 0<depth<80:
            reject("INVALID_NATIVE_RAY_DEPTH")
        normal=r.get("geometric_normal")
        if not isinstance(normal,list) or len(normal)!=3 or any(type(z) not in (int,float) or not math.isfinite(z) for z in normal):
            reject("INVALID_NATIVE_NORMAL")
        if abs(sum(z*z for z in normal)-1)>0.01:
            reject("NONUNIT_NATIVE_NORMAL")
        if r["stable"]:stable+=1
    if stable!=m.get("stable_samples") or stable<MIN_STABLE_RAYS:
        reject("MISSING_STABLE_RAYS")
    return rays

def compare_known_rays(rays,decoded):
    depth=decoded["depth"]["Z"]
    index=decoded["object"]["X"]
    if depth.shape!=(SIDE,SIDE) or index.shape!=(SIDE,SIDE):
        reject("INVALID_EXR_SHAPE")
    total=0
    good=0
    bad_depth=0
    bad_index=0
    worst_depth=0.0
    for r in rays:
        if not r["stable"]:continue
        y,x=r["y"],r["x"]
        actual=float(depth[y,x])
        actual_id=float(index[y,x])
        delta=abs(actual-float(r["depth_from_camera_plane"]))
        if not math.isfinite(delta) or delta>DEPTH_TOLERANCE:
            bad_depth+=1
        else:
            worst_depth=max(worst_depth,delta)
        if not math.isfinite(actual_id) or abs(actual_id-float(r["pass_index"]))>OBJECT_TOLERANCE:
            bad_index+=1
        if math.isfinite(delta) and delta<=DEPTH_TOLERANCE and math.isfinite(actual_id) and abs(actual_id-r["pass_index"])<=OBJECT_TOLERANCE:
            good+=1
        total+=1
    if total<MIN_STABLE_RAYS:
        reject("INSUFFICIENT_NATIVE_STABLE_PIXELS")
    if good/total<MIN_CORRECT_FRACTION:
        reject("CAMERA_DEPTH_OR_OBJECT_REPROJECTION")
    return {"native_stable_rays":total,"joint_correct":good,
            "fraction_correct":good/total,
            "depth_mismatches":bad_depth,"object_id_mismatches":bad_index,
            "max_abs_depth_error_among_correct":worst_depth}

def run(root):
    ray_path=root/"raycast_oracle.json"
    manifest=root/"lighting_manifest.json"
    m=strict_json(ray_path)
    if m.get("synthetic_scene_script_sha256")!=sha(ROOT/"renderlab"/"synthetic_scene.py"):
        reject("WRONG_SCRIPT_SOURCE")
    rays=validate_oracle(m,manifest)
    results={}
    for lighting in ("diffuse_soft","directional_hard"):
        results[lighting]={}
        for arm in ("baseline","physical_material"):
            path=root/lighting/arm/"render_passes.exr"
            decoded,summary=pixel_decode.decode(path)
            receipt=strict_json(root/lighting/arm/"receipt.json")
            if summary["sha256"]!=receipt.get("render_passes_exr",{}).get("sha256"):
                reject("DECODED_EXR_UNBOUND_TO_RENDER_RECEIPT")
            r=compare_known_rays(rays,decoded)
            r["exr_sha256"]=summary["sha256"]
            results[lighting][arm]=r
    return {"schema":"r045.ortho.raycast.v1",
            "status":"PASS_NARROW_REAL_EXR_VS_SOURCE_NATIVE_RAYCAST",
            "qualification":"ORIGINAL_SYNTHETIC_GEOMETRY_ONLY_NOT_TRUE_NORMALS_OR_PHOTOREALISM",
            "original_rights":"ORIGINAL_SYNTHETIC",
            "raycast_receipt_sha256":sha(ray_path),
            "depth_tolerance_world_units":DEPTH_TOLERANCE,
            "required_correct_fraction":MIN_CORRECT_FRACTION,
            "results":results}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    report=run(a.root)
    a.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))
