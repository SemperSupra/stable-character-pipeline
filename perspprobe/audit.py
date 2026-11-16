#!/usr/bin/env python3
"""Independent decoded Cycles perspective Z/object audit versus native mesh rays.

No fitted depth scale, learned offsets or private character data. R045 numerical
comparison reused verbatim; this file adds a genuinely different perspective
camera projection source and explicit lens/source/receipt identity gates.
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
import depthprobe.audit as ortho
sys.path.insert(0,str(ROOT/"renderlab"/"exraudit"))
import pixel_decode

LENS_VALUES={"lens_35":35.0,"lens_65":65.0}
ARMS={"baseline","physical_material"}
SOURCE=ROOT/"renderlab"/"synthetic_scene.py"

def reject(msg):
    raise ValueError("R057_PERSPECTIVE_HOLD_"+msg)

def sha(path,max_bytes=16*1024*1024):
    if path.is_symlink() or not path.is_file() or not 1<=path.stat().st_size<=max_bytes:
        reject("UNSAFE_MISSING_OR_OVERLARGE_FILE")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def canonical_hash(data):
    return hashlib.sha256(json.dumps(
        data,sort_keys=True,separators=(",",":"),allow_nan=False
    ).encode("utf-8")).hexdigest()

def validate_manifest(m):
    if not isinstance(m,dict) or m.get("schema")!="r057.perspective.native.v1" or m.get("status")!="PERSPECTIVE_SOURCE_RAY_CAPTURED_PENDING_EXR_CRITIC":
        reject("SOURCE_SCHEMA_OR_STATUS")
    if m.get("rights")!="ORIGINAL_SYNTHETIC" or m.get("qualification")!="NOT_PHOTOREALISM_OR_PRIVATE_HUMAN_EVIDENCE":
        reject("SOURCE_RIGHTS_OR_FALSE_PHOTOREAL_CLAIM")
    if m.get("source_scene_id")!="original-synthetic-head-v1" or m.get("resolution")!=256:
        reject("SOURCE_SCENE_OR_SIZE")
    if m.get("source_script_sha256")!=sha(SOURCE):
        reject("SOURCE_SCRIPT_SHA_UNBOUND")
    if not isinstance(m.get("geometry_sha256"),str) or len(m["geometry_sha256"])!=64:
        reject("MISSING_GEOMETRY_SHA")
    cases=m.get("lenses")
    if not isinstance(cases,dict) or set(cases)!=set(LENS_VALUES):
        reject("WRONG_CAMERA_CASES")
    cams=set()
    for key,expected in LENS_VALUES.items():
        case=cases[key]
        camera=case.get("camera")
        if not isinstance(camera,dict) or camera.get("type")!="PERSP":
            reject("CAMERA_NOT_PERSPECTIVE")
        if camera.get("sensor_fit")!="HORIZONTAL" or camera.get("sensor_width_mm")!=36.0:
            reject("UNAPPROVED_CAMERA_SENSOR")
        if camera.get("shift_x")!=0.0 or camera.get("shift_y")!=0.0:
            reject("UNAPPROVED_CAMERA_SHIFT")
        if camera.get("lens_mm")!=expected or camera.get("resolution")!=[256,256] or camera.get("pixel_aspect")!=[1.0,1.0]:
            reject("FOCAL_LENGTH_OR_ASPECT_MUTATION")
        mat=camera.get("world_matrix")
        if not isinstance(mat,list) or len(mat)!=16 or any(type(v) not in (float,int) or not math.isfinite(v) for v in mat):
            reject("INVALID_CAMERA_MATRIX")
        if not isinstance(camera.get("clip_start"),(int,float)) or not isinstance(camera.get("clip_end"),(int,float)):
            reject("CAMERA_CLIP_INVALID")
        if camera["clip_start"]<=0 or camera["clip_end"]<=camera["clip_start"]:
            reject("CAMERA_CLIP_INVALID")
        digest=canonical_hash(camera)
        if case.get("camera_sha256")!=digest or digest in cams:
            reject("CAMERA_DIGEST_OR_NON_DISTINCT_LENSES")
        cams.add(digest)
        if case.get("source_geometry_sha256")!=m["geometry_sha256"]:
            reject("MESH_DRIFT_BETWEEN_CAMERAS")
        rays=case.get("rays")
        if not isinstance(rays,list) or len(rays)>256 or len(rays)<64:
            reject("SOURCE_NATIVE_RAYS")
        pts=set()
        stable=0
        for r in rays:
            if not isinstance(r,dict):reject("RAY_NOT_OBJECT")
            x,y=r.get("x"),r.get("y")
            if type(x) is not int or type(y) is not int or not(0<=x<256 and 0<=y<256) or (x-8)%16 or (y-8)%16 or (x,y) in pts:
                reject("RAY_PIXEL_GRID_OR_DUPLICATE")
            pts.add((x,y))
            if type(r.get("stable")) is not bool:
                reject("RAY_STABILITY_NOT_BOOLEAN")
            if r["stable"]:stable+=1
            if type(r.get("pass_index")) is not int or r["pass_index"] not in (1,2):
                reject("RAY_UNKNOWN_OBJECT")
            z=r.get("depth_from_camera_plane")
            if type(z) not in (float,int) or not math.isfinite(z) or not 0<z<80:
                reject("NONFINITE_RAY_DISTANCE")
            n=r.get("geometric_normal")
            if not isinstance(n,list) or len(n)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in n) or abs(sum(v*v for v in n)-1)>0.01:
                reject("BAD_GEOMETRIC_NORMAL")
            if not isinstance(r.get("object_name"),str) or not r["object_name"]:
                reject("UNNAMED_SOURCE_OBJECT")
        if stable<64 or stable!=case.get("stable_count") or len(rays)!=case.get("ray_sample_count"):
            reject("INSUFFICIENT_STABLE_NATIVE_RAYS")
        if not isinstance(case.get("arms"),dict) or set(case["arms"])!=ARMS:
            reject("INCOMPLETE_MATERIAL_MATRIX")
        for arm,files in case["arms"].items():
            if set(files)!={"beauty.png","render_passes.exr"}:
                reject("MISSING_RENDER_FORMAT")
            for filename,info in files.items():
                if not isinstance(info,dict) or not isinstance(info.get("sha256"),str) or len(info["sha256"])!=64 or type(info.get("bytes")) is not int or info["bytes"]<128:
                    reject("RENDER_CUSTODY_INVALID")
    return cases

def independent_verify(root):
    path=root/"r057_source_manifest.json"
    m=ortho.strict_json(path)
    cases=validate_manifest(m)
    rows={}
    for label,case in sorted(cases.items()):
        rows[label]={}
        decoded={}
        for arm in ("baseline","physical_material"):
            files=case["arms"][arm]
            d=root/label/arm
            for name in ("beauty.png","render_passes.exr"):
                p=d/name
                if sha(p)!=files[name]["sha256"] or p.stat().st_size!=files[name]["bytes"]:
                    reject("RENDER_FILE_TAMPER_"+label+"_"+arm)
            pixels,report=pixel_decode.decode(d/"render_passes.exr")
            decoded[arm]=pixels
            if report["sha256"]!=files["render_passes.exr"]["sha256"]:
                reject("INDEPENDENT_EXR_SHA_DISAGREEMENT")
            row=ortho.compare_known_rays(case["rays"],pixels)
            row["exr_sha256"]=report["sha256"]
            rows[label][arm]=row
        diff=np.stack([
            np.abs(decoded["baseline"]["beauty"][c].astype(np.float64)-
                   decoded["physical_material"]["beauty"][c].astype(np.float64))
            for c in "RGB"
        ],axis=-1)
        changed=float(np.mean(np.any(diff>2/255,axis=-1)))
        if not math.isfinite(changed) or changed<=0.001:
            reject("MISSING_CONTROLLED_MATERIAL_DIFFERENCE_"+label)
        rows[label]["changed_linear_rgb_fraction"]=changed
    return {
        "schema":"r057.perspective.numeric.v1",
        "status":"PASS_NARROW_PERSPECTIVE_SOURCE_RAYS_VS_REAL_CYCLES_EXR",
        "qualification":"NOT_HUMAN_PHOTOREALISM_OR_NORMAL_PHYSICS_PROOF",
        "rights":"ORIGINAL_SYNTHETIC",
        "source_manifest_sha256":sha(path,max_bytes=512*1024),
        "depth_error_tolerance_blender_units":ortho.DEPTH_TOLERANCE,
        "min_joint_depth_object_correct":ortho.MIN_CORRECT_FRACTION,
        "cases":rows
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=independent_verify(args.root)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True),flush=True)
