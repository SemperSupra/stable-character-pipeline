#!/usr/bin/env python3
"""R074 independent FCurve/subframe and LBS/EXR source audit.

Actual keyframed Blender evaluated vertex samples versus separately computed
NumPy LBS; no user feedback, real person, MMD or temporal physical guarantee.
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
import skinprobe.audit as lbs
from renderlab.exraudit import pixel_decode

KEYS={"t000":(0.0,0.0),"t050":(0.5,0.17),
      "t100":(1.0,0.34),"t150":(1.5,0.025),"t200":(2.0,-0.29)}
MAX_FCURVE_ERROR=1e-5
MIN_EVALUATED_DISTINCT=0.015
MIN_IMAGE_CHANGE=0.002

def reject(msg):
    raise ValueError("R074_SUBFRAME_HOLD_"+msg)

def sha(path):
    if path.is_symlink() or not path.is_file() or not 128<=path.stat().st_size<=20*1024*1024:
        reject("UNSAFE_SOURCE_OR_RENDER_FILE")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for x in iter(lambda:f.read(1024*1024),b""):
            h.update(x)
    return h.hexdigest()

def validate(m):
    if not isinstance(m,dict) or m.get("schema")!="r074.original.synthetic.native-subframes.v1" or m.get("status")!="ACTUAL_BLENDER_FCURVE_SUBFRAMES_PENDING_EXR_LBS_AUDIT":
        reject("SOURCE_SCHEMA_OR_STATUS")
    if m.get("rights")!="ORIGINAL_SYNTHETIC" or m.get("qualification")!="NOT_REAL_PERSON_SKIN_OR_MMD_RETARGET":
        reject("FALSE_RIGHTS_OR_REAL_MOTION")
    if m.get("source_scene_id")!="original-synthetic-head-v1" or m.get("timebase")!="BLENDER_SCENE_FRAMES_WITH_EXPLICIT_SUBFRAME" or m.get("interpolation")!="ACTUAL_BLENDER_FCURVE_LINEAR":
        reject("UNBOUND_TIMEBASE")
    checks=(("source_original_sha256",ROOT/"renderlab"/"synthetic_scene.py"),
            ("source_skin_sha256",ROOT/"skinprobe"/"scene.py"),
            ("source_camera_sha256",ROOT/"perspprobe"/"scene.py"))
    for name,path in checks:
        if m.get(name)!=sha(path):
            reject("SOURCE_SCRIPT_DIGEST_"+name)
    if m.get("keys")!=[[0,0.0],[1,0.34],[2,-0.29]]:
        reject("ANIMATION_KEY_SOURCE_CHANGED")
    cam=m.get("camera")
    if not isinstance(cam,dict) or cam.get("type")!="PERSP" or cam.get("lens_mm")!=65.0 or cam.get("sensor_width_mm")!=36.0 or cam.get("resolution")!=[256,256] or cam.get("shift_x")!=0.0 or cam.get("shift_y")!=0.0 or m.get("camera_sha256")!=perspective.canonical_hash(cam):
        reject("CAMERA_SOURCE_CHANGED")
    source=m.get("source")
    # Reuse original R072 source/weight/topology validator with its frame
    # header converted solely for verifying its independent source data.
    parent={
      "schema":"r072.synthetic.skinning.native.v1",
      "status":"NATIVE_ARMATURE_SOURCE_CAPTURE_PENDING_INDEPENDENT_LBS_EXR",
      "rights":"ORIGINAL_SYNTHETIC",
      "qualification":"NOT_REAL_PERSON_OR_MAKEHUMAN_SKINNING",
      "source_scene_id":"original-synthetic-head-v1",
      "motion_type":"TWO_BONE_LINEAR_BLEND_SKINNING_NO_HUMAN",
      "original_source_script_sha256":m["source_original_sha256"],
      "perspective_script_sha256":m["source_camera_sha256"],
      "rig_object_name":"r072-original-weighted-sleeve",
      "rig_object_id":3,"camera":cam,
      "camera_sha256":m["camera_sha256"],
      "source":source,"frames":{"0":{},"1":{},"2":{}}
    }
    bind,weights,faces,_=lbs.validate_source(parent)
    samples=m.get("samples")
    if not isinstance(samples,dict) or set(samples)!=set(KEYS):
        reject("MISSING_SUBFRAMES")
    unique=set()
    for key,(time,angle) in KEYS.items():
        sample=samples[key]
        if type(sample.get("time_frames")) not in (int,float) or sample["time_frames"]!=time or type(sample.get("actual_fcurve_angle_x")) not in (int,float) or type(sample.get("source_expected_linear_angle_x")) not in (int,float):
            reject("WRONG_SUBFRAME_TIME_OR_TYPE")
        if abs(sample["actual_fcurve_angle_x"]-angle)>MAX_FCURVE_ERROR or sample["source_expected_linear_angle_x"]!=angle:
            reject("NATIVE_FCURVE_INTERPOLATION_MISMATCH")
        vertices=sample.get("evaluated_vertices")
        if not isinstance(vertices,list) or sample.get("faces_sha256")!=lbs.canonical_hash(faces):
            reject("MODIFIER_TOPOLOGY_CHANGED")
        token=sample.get("evaluated_mesh_sha256")
        if token!=lbs.canonical_hash({"vertices":vertices,"faces":faces}) or token in unique:
            reject("MISSING_DEFORMATION_OR_SHA_REPLAY")
        unique.add(token)
        rays=sample.get("rays")
        if not isinstance(rays,list) or not 64<=len(rays)<=256:
            reject("SOURCE_RAY_GRID")
        seen=set();count=0;rig_count=0
        for r in rays:
            if not isinstance(r,dict):reject("MALFORMED_SOURCE_RAY")
            x,y=r.get("x"),r.get("y")
            if type(x) is not int or type(y) is not int or not(0<=x<256 and 0<=y<256) or (x-8)%16 or (y-8)%16 or (x,y) in seen:
                reject("DUPLICATE_OR_BAD_PIXEL_RAY")
            seen.add((x,y))
            if type(r.get("stable")) is not bool or type(r.get("pass_index")) is not int or r["pass_index"] not in (1,2,3):
                reject("SOURCE_RAY_TYPE")
            if r["stable"]:
                count+=1
                if r["pass_index"]==3:rig_count+=1
        if count!=sample.get("stable_ray_count") or count<64 or rig_count!=sample.get("rig_stable_ray_count") or rig_count<2:
            reject("SUBFRAME_NATIVE_RAY_WITNESS")
        files=sample.get("files")
        if not isinstance(files,dict) or set(files)!={"beauty.png","render_passes.exr"}:
            reject("REAL_IMAGE_PAIR_MISSING")
        for info in files.values():
            if not isinstance(info,dict) or type(info.get("bytes")) is not int or info["bytes"]<=128 or not isinstance(info.get("sha256"),str) or len(info["sha256"])!=64:
                reject("BAD_IMAGE_CUSTODY")
    return bind,weights,faces,samples

def verify(root):
    manifest=root/"r074_source.json"
    m=strict.strict_json(manifest)
    bind,weights,faces,samples=validate(m)
    result={};vertices={};pictures={}
    for key in KEYS:
        sample=samples[key]
        check=lbs.verify_lbs(bind,weights,sample["armature_pose_matrices"],sample["evaluated_vertices"])
        directory=root/key
        for name,record in sample["files"].items():
            f=directory/name
            if sha(f)!=record["sha256"] or f.stat().st_size!=record["bytes"]:
                reject("SOURCE_RENDER_BYTE_TAMPER")
        pix,exr=pixel_decode.decode(directory/"render_passes.exr")
        if exr["sha256"]!=sample["files"]["render_passes.exr"]["sha256"]:
            reject("INDEPENDENT_PIXEL_CUSTODY")
        depth=perspective.compare_axial_depth(sample["rays"],pix)
        check.update(depth)
        check["time_frames"]=sample["time_frames"]
        check["observed_tip_angle_x"]=sample["actual_fcurve_angle_x"]
        check["rig_stable_ray_count"]=sample["rig_stable_ray_count"]
        result[key]=check
        vertices[key]=np.array(sample["evaluated_vertices"],dtype=np.float64)
        pictures[key]=pix["beauty"]
    change={}
    rest=vertices["t000"]
    for key in list(KEYS)[1:]:
        dist=float(np.max(np.linalg.norm(vertices[key]-rest,axis=1)))
        if not math.isfinite(dist) or dist<MIN_EVALUATED_DISTINCT:
            reject("RENDERED_SUBFRAME_SKIN_POSE_ALIAS")
        rgb=np.stack([
          np.abs(pictures["t000"][channel].astype(np.float64)-
                 pictures[key][channel].astype(np.float64))
          for channel in "RGB"],axis=-1)
        fraction=float(np.mean(np.any(rgb>2/255,axis=-1)))
        if not math.isfinite(fraction) or fraction<MIN_IMAGE_CHANGE:
            reject("SUBFRAME_NO_REAL_IMAGE_DIFFERENCE")
        change[key]={"max_actual_skin_displacement_from_rest":dist,
                     "changed_beauty_pixel_fraction":fraction}
    for key,a,b in (("t050","t000","t100"),("t150","t100","t200")):
        for endpoint in (a,b):
            d=float(np.max(np.linalg.norm(vertices[key]-vertices[endpoint],axis=1)))
            if d<MIN_EVALUATED_DISTINCT:
                reject("FRACTIONAL_FRAME_COLLAPSED_TO_KEYFRAME")
    return {"schema":"r074.original.synthetic.subframe-LBS-exr.v1",
            "status":"PASS_NARROW_ACTUAL_BLENDER_KEYED_SUBFRAME_SKIN_EXR",
            "rights":"ORIGINAL_SYNTHETIC",
            "qualification":"NOT_REAL_RIG_MMD_MORPH_IK_OR_TEMPORAL_PHYSICS",
            "source_manifest_sha256":sha(manifest),
            "subframe_LBS_tolerance_source_units":lbs.MAX_LBS_ERROR,
            "samples":result,"image_and_vertex_changes":change}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    output=verify(args.root)
    args.out.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n")
    print(json.dumps(output,sort_keys=True),flush=True)
