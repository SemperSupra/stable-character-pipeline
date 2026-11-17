#!/usr/bin/env python3
"""R075 independent actual EXR semantic visibility policy with real 3D occluder.

Source-known original synthetic surface with partial / severe masking. The
correct output on occlusion is a typed HOLD, never guessed continuity/identity.
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
import depthprobe.audit as strict
import perspprobe.audit as perspective
from renderlab.exraudit import pixel_decode

CASES=("clear","partial","severe")
SOURCE_PARAMS={
    "clear":{"width":0.08,"height":0.08,"offset_x":100.0,"offset_y":0.0},
    "partial":{"width":0.56,"height":0.78,"offset_x":0.18,"offset_y":0.11},
    "severe":{"width":2.4,"height":2.3,"offset_x":0.0,"offset_y":0.0},
}
MIN_BASE_HEAD=500
PARTIAL_RATIO=(0.25,0.93)
SEVERE_MAX_RATIO=0.20

def reject(reason):
    raise ValueError("R075_OCCLUSION_HOLD_"+reason)

def sha(path):
    if path.is_symlink() or not path.is_file() or not 128<=path.stat().st_size<=20*1024*1024:
        reject("UNSAFE_FILE_SIZE_OR_PATH")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def validate(m):
    if not isinstance(m,dict) or m.get("schema")!="r075.original.synthetic.real-occlusion.v1" or m.get("status")!="ACTUAL_SOURCE_OCCLUSION_PENDING_INDEPENDENT_EXR":
        reject("SOURCE_SCHEMA")
    if m.get("rights")!="ORIGINAL_SYNTHETIC" or m.get("qualification")!="NOT_REAL_PERSON_IDENTITY_OR_OCCLUSION_TRACKING":
        reject("FALSE_SOURCE_ADMISSION")
    if m.get("source_scene_id")!="original-synthetic-head-v1" or m.get("source_motion_type")!="KNOWN_STATIONARY_HEAD_MOVING_FOREGROUND_OCCLUDER":
        reject("UNKNOWN_MOTION_SOURCE")
    if m.get("source_script_sha256")!=sha(ROOT/"renderlab"/"synthetic_scene.py") or m.get("perspective_script_sha256")!=sha(ROOT/"perspprobe"/"scene.py"):
        reject("SOURCE_SCRIPT_DIGEST")
    if m.get("source_semantic_head_id")!=3 or m.get("source_occluder_id")!=4:
        reject("SOURCE_OBJECT_PASS_IDS")
    expected={"head","nose","mouth","left-sclera","left-iris","left-pupil",
        "left-brow","left-ear","right-sclera","right-iris","right-pupil",
        "right-brow","right-ear"}
    names=m.get("source_semantic_head_names")
    if not isinstance(names,list) or set(names)!=expected or len(names)!=len(expected):
        reject("UNKNOWN_OR_DUPLICATE_SOURCE_MESHES")
    cam=m.get("camera")
    if not isinstance(cam,dict) or cam.get("type")!="PERSP" or cam.get("lens_mm")!=65.0 or cam.get("sensor_width_mm")!=36.0 or cam.get("resolution")!=[256,256] or cam.get("shift_x")!=0.0 or cam.get("shift_y")!=0.0:
        reject("CAMERA_FIELDS")
    if m.get("camera_sha256")!=perspective.canonical_hash(cam):
        reject("CAMERA_SHA")
    frames=m.get("cases")
    if not isinstance(frames,dict) or set(frames)!=set(CASES):
        reject("MISSING_CASES")
    geometry=set()
    for index,case in enumerate(CASES):
        f=frames[case]
        if f.get("frame_index")!=index or type(f.get("frame_index")) is not int or f.get("case")!=case or f.get("source_occluder_geometry")!=SOURCE_PARAMS[case]:
            reject("FRAME_CASE_OR_3D_SOURCE_GEOMETRY_MUTATED")
        if f.get("source_occluder_id")!=4 or f.get("source_head_id")!=3 or f.get("camera_sha256")!=m["camera_sha256"]:
            reject("FRAME_SOURCE_ID_OR_CAMERA")
        digest=f.get("source_geometry_sha256")
        if not isinstance(digest,str) or len(digest)!=64 or digest in geometry:
            reject("SOURCE_GEOMETRY_REPLAY")
        geometry.add(digest)
        rays=f.get("rays")
        if not isinstance(rays,list) or not 64<=len(rays)<=256:
            reject("NATIVE_RAY_SET")
        seen=set();stable=0;head=0;occ=0
        for r in rays:
            if not isinstance(r,dict):reject("RAY_NOT_OBJECT")
            x,y=r.get("x"),r.get("y")
            if type(x) is not int or type(y) is not int or not (0<=x<256 and 0<=y<256) or (x-8)%16 or (y-8)%16 or (x,y) in seen:
                reject("DUPLICATED_OR_INVALID_PIXEL_RAY")
            seen.add((x,y))
            if type(r.get("stable")) is not bool or type(r.get("pass_index")) is not int or r["pass_index"] not in (1,2,3,4):
                reject("INVALID_RAY_PASS_INDEX")
            z=r.get("camera_axis_depth")
            length=r.get("ray_distance")
            if type(z) not in (int,float) or type(length) not in (int,float) or not math.isfinite(z) or not math.isfinite(length) or not 0<z<=length+1e-4<80.001:
                reject("NONFINITE_OR_WRONG_PERSPECTIVE_DEPTH")
            if r["stable"]:
                stable+=1
                head+=int(r["pass_index"]==3)
                occ+=int(r["pass_index"]==4)
        if stable!=f.get("stable_rays") or stable<64 or head!=f.get("head_source_rays") or occ!=f.get("occluder_source_rays"):
            reject("SOURCE_STABLE_RAY_COUNTER")
        if case=="clear" and (head<8 or occ>0):
            reject("CLEAR_SOURCE_NOT_VISIBLE")
        if case!="clear" and occ<2:
            reject("NO_ACTUAL_OCCLUDER_SOURCE_RAYS")
        files=f.get("files")
        if not isinstance(files,dict) or set(files)!={"beauty.png","render_passes.exr"}:
            reject("MISSING_ACTUAL_RENDER")
        for value in files.values():
            if not isinstance(value,dict) or type(value.get("bytes")) is not int or value["bytes"]<=128 or not isinstance(value.get("sha256"),str) or len(value["sha256"])!=64:
                reject("BAD_RENDER_CUSTODY")
    return frames

def pixel_visibility(index):
    arr=np.asarray(index,dtype=np.float64)
    if arr.shape!=(256,256):
        reject("INDEX_PASS_DIMENSIONS")
    finite=np.isfinite(arr)
    return {"head":int(np.sum(finite & (np.abs(arr-3.0)<=0.01))),
            "occluder":int(np.sum(finite & (np.abs(arr-4.0)<=0.01)))}

def classify_coverage(counts):
    if not isinstance(counts,dict) or set(counts)!=set(CASES):
        reject("MISSING_TYPED_OCCLUSION_CASE")
    for case in CASES:
        v=counts[case]
        if not isinstance(v,dict) or type(v.get("head")) is not int or type(v.get("occluder")) is not int or v["head"]<0 or v["occluder"]<0:
            reject("INVALID_SEGMENT_AREA")
    base=counts["clear"]["head"]
    if base<MIN_BASE_HEAD or counts["clear"]["occluder"]!=0:
        reject("CLEAR_BASELINE_NOT_CLEAR")
    if counts["partial"]["occluder"]<200 or counts["severe"]["occluder"]<1000:
        reject("FOREGROUND_OCCLUDER_NOT_OBSERVED")
    partial=counts["partial"]["head"]/base
    severe=counts["severe"]["head"]/base
    if not PARTIAL_RATIO[0]<=partial<=PARTIAL_RATIO[1]:
        reject("PARTIAL_COVERAGE_OUTSIDE_PREDECLARED_BAND")
    if severe>SEVERE_MAX_RATIO or severe>=partial:
        reject("SEVERE_COVERAGE_NOT_ENOUGH")
    return {
        "clear":{"decision":"SOURCE_VISIBLE_SYNTHETIC_ONLY","head_visible_fraction":1.0},
        "partial":{"decision":"HOLD_PARTIAL_OCCLUSION_NO_PERSON_ID",
                   "head_visible_fraction":partial},
        "severe":{"decision":"HOLD_SEVERE_OCCLUSION_NO_PERSON_ID",
                  "head_visible_fraction":severe}
    }

def verify(root):
    manifest=root/"r075_source.json"
    m=strict.strict_json(manifest)
    cases=validate(m)
    pixel_counts={}
    rows={}
    for case in CASES:
        frame=cases[case]
        directory=root/case
        for name,receipt in frame["files"].items():
            file=directory/name
            if sha(file)!=receipt["sha256"] or file.stat().st_size!=receipt["bytes"]:
                reject("SOURCE_IMAGE_CUSTODY_CHANGED")
        decoded,meta=pixel_decode.decode(directory/"render_passes.exr")
        if meta["sha256"]!=frame["files"]["render_passes.exr"]["sha256"]:
            reject("INDEPENDENT_EXR_BYTE_CUSTODY")
        match=perspective.compare_axial_depth(frame["rays"],decoded)
        pixel_counts[case]=pixel_visibility(decoded["object"]["X"])
        rows[case]={"native_stable_rays":match["native_stable_rays"],
                    "joint_source_depth_id_matches":match["joint_correct"],
                    "max_abs_axial_depth_error":match["max_abs_axial_depth_error_among_correct"],
                    "source_head_stable_rays":frame["head_source_rays"],
                    "source_occluder_stable_rays":frame["occluder_source_rays"],
                    "actual_EXR_segmentation_pixels":pixel_counts[case],
                    "exr_sha256":meta["sha256"]}
    decisions=classify_coverage(pixel_counts)
    return {"schema":"r075.original.synthetic.exr.occlusion-policy.v1",
            "status":"PASS_NARROW_REAL_EXR_OCCLUSION_REQUIRES_TYPED_HOLD",
            "qualification":"NOT_TRUE_PERSON_RECOGNITION_OR_OCCLUDED_TRACKING",
            "rights":"ORIGINAL_SYNTHETIC",
            "source_manifest_sha256":sha(manifest),
            "frames":rows,"typed_visibility_decisions":decisions}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    r=verify(args.root)
    args.out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(r,sort_keys=True),flush=True)
