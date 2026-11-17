#!/usr/bin/env python3
"""R073 independent full-resolution EXR object-index motion vs camera projection.

Only original source-known synthetic head proxy; NOT a human tracker, learned
identity, rigged motion, physically correct optical flow, contact or film QA.
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
import perspprobe.audit as perspective
from renderlab.exraudit import pixel_decode

HEAD_NAMES={
    "head","nose","mouth","left-sclera","left-iris","left-pupil",
    "left-brow","left-ear","right-sclera","right-iris","right-pupil",
    "right-brow","right-ear"
}
OFFSETS={"0":0.0,"1":0.36,"2":-0.28}
HEAD_INDEX=3
MASK_MIN_PIXELS=500
CHANGE_FRACTION_MIN=0.005
DELTA_MIN_PX=2.0

def reject(why):
    raise ValueError("R073_TRACKING_EXR_HOLD_"+why)

def sha(path):
    if path.is_symlink() or not path.is_file() or not 128<=path.stat().st_size<=16*1024*1024:
        reject("UNSAFE_OR_OVERSIZED_FILE")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def validate(m):
    if not isinstance(m,dict) or m.get("schema")!="r073.original.synthetic.exr.object-track.v1" or m.get("status")!="SOURCE_TRACKING_CAPTURE_PENDING_INDEPENDENT_IMAGE":
        reject("UNADMITTED_SCHEMA_OR_STATUS")
    if m.get("rights")!="ORIGINAL_SYNTHETIC" or m.get("qualification")!="NOT_REAL_IDENTITY_OPTICAL_FLOW_OR_MAKEHUMAN":
        reject("FALSE_RIGHTS_OR_REAL_IDENTITY_CLAIM")
    if m.get("scene_id")!="original-synthetic-head-v1" or m.get("source_motion_type")!="RIGID_HEAD_TRANSLATION_WITH_SEMANTIC_EXR_ID":
        reject("WRONG_SOURCE_SCENE_OR_MOTION")
    if m.get("source_semantic_object_index")!=HEAD_INDEX or set(m.get("source_semantic_object_names",[]))!=HEAD_NAMES or len(m.get("source_semantic_object_names",[]))!=len(HEAD_NAMES):
        reject("WRONG_PROVENANCE_SEMANTIC_OBJECTS")
    if m.get("original_source_script_sha256")!=sha(ROOT/"renderlab"/"synthetic_scene.py") or m.get("perspective_script_sha256")!=sha(ROOT/"perspprobe"/"scene.py"):
        reject("SOURCE_SCRIPT_BYTES_CHANGED")
    cam=m.get("camera")
    if not isinstance(cam,dict) or cam.get("type")!="PERSP" or cam.get("lens_mm")!=65.0 or cam.get("sensor_width_mm")!=36.0 or cam.get("shift_x")!=0.0 or cam.get("shift_y")!=0.0 or cam.get("resolution")!=[256,256]:
        reject("CAMERA_NOT_SOURCE_CONTROLLED")
    if m.get("camera_sha256")!=perspective.canonical_hash(cam):
        reject("CAMERA_SHA")
    frames=m.get("frames")
    if not isinstance(frames,dict) or set(frames)!=set(OFFSETS):
        reject("MISSING_TIME_FRAMES")
    unique_source_geom=set()
    for key,shift in OFFSETS.items():
        f=frames[key]
        if f.get("frame_index")!=int(key) or type(f.get("frame_index")) is not int or f.get("source_head_x_delta")!=shift or type(f.get("source_head_x_delta")) not in (int,float):
            reject("MOTION_CLOCK_OR_OFFSET_MUTATION")
        if f.get("camera_sha256")!=m["camera_sha256"] or f.get("head_mesh_pass_index")!=HEAD_INDEX:
            reject("TIME_CAMERA_OR_ID_CHANGED")
        geom=f.get("source_geometry_sha256")
        if not isinstance(geom,str) or len(geom)!=64 or geom in unique_source_geom:
            reject("DUPLICATE_FRAME_GEOMETRY")
        unique_source_geom.add(geom)
        center=f.get("head_center_projection_px")
        if not isinstance(center,list) or len(center)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or not -256<v<512 for v in center):
            reject("UNPROJECTABLE_SOURCE_CENTER")
        rays=f.get("source_rays")
        if not isinstance(rays,list) or not 64<=len(rays)<=256:
            reject("NO_SOURCE_RAY_GRID")
        seen=set();count=0;head_count=0
        for r in rays:
            if not isinstance(r,dict):reject("NOT_SOURCE_RAY")
            x,y=r.get("x"),r.get("y")
            if type(x) is not int or type(y) is not int or not(0<=x<256 and 0<=y<256) or (x-8)%16 or (y-8)%16 or (x,y) in seen:
                reject("BAD_PIXEL_GRID")
            seen.add((x,y))
            if type(r.get("stable")) is not bool or type(r.get("pass_index")) is not int or r["pass_index"] not in (1,2,3):
                reject("BAD_SOURCE_RAY_SEMANTICS")
            axis=r.get("camera_axis_depth")
            if type(axis) not in (int,float) or not math.isfinite(axis) or axis<=0 or axis>=80:
                reject("BAD_CAMERA_AXIS_DEPTH")
            if r["stable"]:
                count+=1
                if r["pass_index"]==3:head_count+=1
        if count!=f.get("source_stable_rays") or count<64 or head_count!=f.get("source_stable_head_rays") or head_count<8:
            reject("NATIVE_HEAD_OCCLUSION_OR_WITNESS")
        files=f.get("files")
        if not isinstance(files,dict) or set(files)!={"beauty.png","render_passes.exr"}:
            reject("REAL_RENDER_PAIR_INCOMPLETE")
        for info in files.values():
            if not isinstance(info,dict) or type(info.get("bytes")) is not int or info["bytes"]<128 or not isinstance(info.get("sha256"),str) or len(info["sha256"])!=64:
                reject("BAD_EXR_SOURCE_RECEIPT")
    return frames

def mask_centroid(index_pixels):
    index=np.asarray(index_pixels,dtype=np.float64)
    if index.shape!=(256,256):
        reject("WRONG_EXR_INDEX_DIMENSIONS")
    mask=np.isfinite(index) & (np.abs(index-HEAD_INDEX)<=0.01)
    count=int(mask.sum())
    if count<MASK_MIN_PIXELS:
        reject("REAL_HEAD_SEGMENTATION_ABSENT")
    y,x=np.nonzero(mask)
    return mask,{"pixels":count,
                 "centroid_x":float(np.mean(x+0.5)),
                 "centroid_y":float(np.mean(y+0.5))}

def compare_motion(masks,centers,predicted):
    if set(masks)!={"0","1","2"} or set(centers)!={"0","1","2"} or set(predicted)!={"0","1","2"}:
        reject("MISSING_TRACK_FRAME")
    out={}
    baseline=centers["0"]
    for key in ("1","2"):
        source_dx=predicted[key][0]-predicted["0"][0]
        observed_dx=centers[key]["centroid_x"]-baseline["centroid_x"]
        if abs(source_dx)<DELTA_MIN_PX or abs(observed_dx)<DELTA_MIN_PX:
            reject("SOURCE_OR_RENDERED_TRACK_NO_MOVEMENT")
        if source_dx*observed_dx<=0:
            reject("REVERSED_RENDERED_SEGMENTATION_DIRECTION")
        residual=abs(source_dx-observed_dx)
        # This is a robust silhouette-centroid *directional* check, not a
        # falsely calibrated optical flow or exact camera reprojection metric.
        if residual>max(10.0,abs(source_dx)*0.45):
            reject("SEMANTIC_OBJECT_TRACK_EXCEEDS_PREDECLARED_ENVELOPE")
        area_ratio=centers[key]["pixels"]/baseline["pixels"]
        if not 0.65<=area_ratio<=1.35:
            reject("HEAD_SEGMENTATION_AREA_DISAPPEARED")
        change=float(np.mean(masks[key]!=masks["0"]))
        if change<CHANGE_FRACTION_MIN:
            reject("UNCHANGED_OBJECT_SEGMENTATION_AFTER_MOTION")
        out["0_to_"+key]={
          "native_source_projected_dx_px":source_dx,
          "real_EXR_index_centroid_dx_px":observed_dx,
          "relative_source_versus_mask_centroid_dx_residual_px":residual,
          "segment_area_ratio":area_ratio,
          "actual_segmentation_changed_fraction":change,
        }
    return out

def audit(root):
    manifest=root/"r073_source.json"
    m=prior.strict_json(manifest)
    frames=validate(m)
    masks={};centers={};predicted={}
    depth={}
    for key,frame in sorted(frames.items()):
        directory=root/("frame_%02d"%int(key))
        for filename,info in frame["files"].items():
            file=directory/filename
            if sha(file)!=info["sha256"] or file.stat().st_size!=info["bytes"]:
                reject("ACTUAL_EXR_OR_PNG_BYTES_CHANGED")
        pixels,exr=pixel_decode.decode(directory/"render_passes.exr")
        if exr["sha256"]!=frame["files"]["render_passes.exr"]["sha256"]:
            reject("INDEPENDENT_PIXEL_DECODE_SHA")
        row=perspective.compare_axial_depth(frame["source_rays"],pixels)
        mask,stats=mask_centroid(pixels["object"]["X"])
        masks[key]=mask;centers[key]=stats
        predicted[key]=frame["head_center_projection_px"]
        depth[key]={"joint_source_ray_matches":row["joint_correct"],
                    "native_stable_rays":row["native_stable_rays"],
                    "max_source_axis_Z_error":row["max_abs_axial_depth_error_among_correct"],
                    "head_mask":stats,
                    "exr_sha256":exr["sha256"]}
    movement=compare_motion(masks,centers,predicted)
    return {
      "schema":"r073.original.synthetic.exr.object-track-critic.v1",
      "status":"PASS_NARROW_REAL_EXR_SEMANTIC_TRACK_DIRECTION",
      "qualifier":"NOT_RELIABLE_PERSON_TRACKING_OR_TRUE_OPTICAL_FLOW",
      "rights":"ORIGINAL_SYNTHETIC",
      "source_manifest_sha256":sha(manifest),
      "frames":depth,"motion":movement
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    data=audit(args.root)
    args.out.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,sort_keys=True),flush=True)
