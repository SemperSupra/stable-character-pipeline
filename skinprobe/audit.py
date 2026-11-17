#!/usr/bin/env python3
"""R072 independent NumPy LBS vs actual Blender Armature modifier and Cycles EXR.

Independent arithmetic on source bind coords, exact weights and Blender bone
kinematic matrices; actual evaluated vertices are independent modifier output.
Not a biologically valid rig, motion retargeter or person/source authorization.
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

ANGLES={"0":0.0,"1":0.34,"2":-0.29}
BONES=("root","tip")
SIDES=12
RINGS=8
VERTICES=SIDES*RINGS
MAX_LBS_ERROR=0.0001
MIN_REAL_DEFORMATION=0.05

def reject(msg):
    raise ValueError("R072_SKIN_LBS_HOLD_"+msg)

def canonical_hash(x):
    return hashlib.sha256(json.dumps(
        x,sort_keys=True,separators=(",",":"),allow_nan=False
    ).encode()).hexdigest()

def sha(path):
    if path.is_symlink() or not path.is_file() or not 128<=path.stat().st_size<=16*1024*1024:
        reject("MISSING_UNSAFE_OR_OVERSIZE_SOURCE")
    h=hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda:file.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def finite_array(x,shape,why):
    arr=np.asarray(x,dtype=np.float64)
    if arr.shape!=shape or not np.all(np.isfinite(arr)):
        reject(why)
    return arr

def validate_source(m):
    if not isinstance(m,dict) or m.get("schema")!="r072.synthetic.skinning.native.v1" or m.get("status")!="NATIVE_ARMATURE_SOURCE_CAPTURE_PENDING_INDEPENDENT_LBS_EXR":
        reject("SCHEMA_OR_STATUS")
    if m.get("rights")!="ORIGINAL_SYNTHETIC" or m.get("qualification")!="NOT_REAL_PERSON_OR_MAKEHUMAN_SKINNING":
        reject("FALSE_PERSON_OR_RIGHTS")
    if m.get("source_scene_id")!="original-synthetic-head-v1" or m.get("motion_type")!="TWO_BONE_LINEAR_BLEND_SKINNING_NO_HUMAN":
        reject("SCENE_OR_RIG_MODEL")
    if m.get("original_source_script_sha256")!=sha(ROOT/"renderlab"/"synthetic_scene.py") or m.get("perspective_script_sha256")!=sha(ROOT/"perspprobe"/"scene.py"):
        reject("ACTUAL_ORIGINAL_SOURCE_SHA")
    if m.get("rig_object_name")!="r072-original-weighted-sleeve" or m.get("rig_object_id")!=3:
        reject("UNAPPROVED_MESH_ID")
    camera=m.get("camera")
    if not isinstance(camera,dict) or camera.get("type")!="PERSP" or camera.get("lens_mm")!=65.0 or camera.get("sensor_width_mm")!=36.0 or camera.get("shift_x")!=0.0 or camera.get("shift_y")!=0.0 or camera.get("resolution")!=[256,256]:
        reject("UNCONTROLLED_CAMERA")
    if m.get("camera_sha256")!=perspective.canonical_hash(camera):
        reject("CAMERA_SOURCE_SHA")
    source=m.get("source")
    if not isinstance(source,dict) or source.get("bone_names")!=list(BONES):
        reject("BONE_NAMES")
    bind=finite_array(source.get("vertex_bind"),(VERTICES,3),"BIND_VERTEX_NONFINITE")
    weights=finite_array(source.get("weights"),(VERTICES,2),"SKIN_WEIGHT_NONFINITE")
    if np.any(weights<-1e-8) or np.any(weights>1+1e-8) or np.max(np.abs(weights.sum(axis=1)-1))>1e-6:
        reject("SKIN_WEIGHT_SUM_OR_SIGN")
    faces=source.get("faces")
    if not isinstance(faces,list) or len(faces)<SIDES*(RINGS-1):
        reject("TOPOLOGY_MISSING")
    if any(not isinstance(face,list) or len(face)<3 or any(type(i) is not int or i<0 or i>=VERTICES for i in face) for face in faces):
        reject("INVALID_VERTEX_INDICES")
    if source.get("rest_mesh_sha256")!=canonical_hash({
        "vertices":source["vertex_bind"],"faces":faces,"weights":source["weights"]
    }):
        reject("BIND_MESH_SOURCE_DIGEST")
    rest=source.get("bone_rest_matrices")
    if not isinstance(rest,dict) or set(rest)!=set(BONES):
        reject("MISSING_REST_BONE")
    for name in BONES:
        matrix=finite_array(rest[name],(16,),"BAD_REST_BONE_MATRIX").reshape((4,4))
        if abs(np.linalg.det(matrix[:3,:3]))<1e-8 or not np.allclose(matrix[3],np.array([0,0,0,1]),atol=1e-7):
            reject("BAD_REST_FRAME")
    frames=m.get("frames")
    if not isinstance(frames,dict) or set(frames)!=set(ANGLES):
        reject("SKIN_FRAMES")
    return bind,weights,faces,frames

def verify_lbs(bind,weights,transforms,evaluated):
    if not isinstance(transforms,dict) or set(transforms)!=set(BONES):
        reject("UNKNOWN_OR_MISSING_SKIN_BONE")
    matrices={}
    for name in BONES:
        m=finite_array(transforms[name],(16,),"INVALID_POSE_BONE_MATRIX").reshape(4,4)
        if abs(np.linalg.det(m[:3,:3]))<1e-8 or not np.allclose(m[3],np.array([0,0,0,1]),atol=1e-7):
            reject("NONRIGID_OR_UNPROJECTIVE_SKIN_MATRIX")
        if not np.allclose(m[:3,:3].T @ m[:3,:3],np.eye(3),atol=1e-4):
            reject("SKIN_BONE_MUST_BE_RIGID")
        matrices[name]=m
    observed=finite_array(evaluated,(VERTICES,3),"INVALID_EVALUATED_GEOMETRY")
    homogeneous=np.column_stack((bind,np.ones(VERTICES)))
    independent=sum(
        weights[:,index,None]*(homogeneous @ matrices[name].T)[:,:3]
        for index,name in enumerate(BONES)
    )
    delta=np.linalg.norm(independent-observed,axis=1)
    maximum=float(np.max(delta))
    if not math.isfinite(maximum) or maximum>MAX_LBS_ERROR:
        reject("ACTUAL_BLENDER_ARMATURE_VS_INDEPENDENT_LBS")
    return {"vertex_count":VERTICES,"max_actual_modifier_vs_independent_lbs_error":maximum,
            "median_actual_modifier_vs_independent_lbs_error":float(np.median(delta))}

def verify(root):
    m=prior.strict_json(root/"r072_source.json")
    bind,weights,faces,frames=validate_source(m)
    rows={}
    posed={}
    pixel={}
    poses=set()
    for key in sorted(frames):
        data=frames[key]
        if type(data.get("frame_index")) is not int or data["frame_index"]!=int(key) or data.get("tip_local_rotation_x_radians")!=ANGLES[key]:
            reject("WRONG_FRAME_POSE_ANGLE")
        if data.get("camera_sha256")!=m["camera_sha256"]:
            reject("CAMERA_MOVED_DURING_ARMATURE_POSE")
        evaluated=data.get("evaluated_vertices")
        check=verify_lbs(bind,weights,data.get("armature_pose_matrices"),evaluated)
        if data.get("evaluated_mesh_sha256")!=canonical_hash({
            "vertices":evaluated,"faces":faces
        }) or data["evaluated_mesh_sha256"] in poses:
            reject("EVALUATED_MESH_TAMPER_OR_UNCHANGED")
        poses.add(data["evaluated_mesh_sha256"])
        r=data.get("rays")
        if not isinstance(r,list) or not 64<=len(r)<=256:
            reject("INSUFFICIENT_NATIVE_SCENE_RAYS")
        stable=0;rig=0;seen=set()
        for ray in r:
            if not isinstance(ray,dict):reject("NOT_A_RAY")
            x,y=ray.get("x"),ray.get("y")
            if type(x) is not int or type(y) is not int or not (0<=x<256 and 0<=y<256) or (x-8)%16 or (y-8)%16 or (x,y) in seen:
                reject("DUPLICATE_OR_BAD_SOURCE_RAY")
            seen.add((x,y))
            if type(ray.get("stable")) is not bool or type(ray.get("pass_index")) is not int or ray["pass_index"] not in (1,2,3):
                reject("RAY_INDEX_OR_STABILITY")
            if ray["stable"]:
                stable+=1
                if ray["pass_index"]==3:rig+=1
        if stable!=data.get("stable_ray_count") or stable<64 or rig!=data.get("stable_rig_ray_count") or rig<2:
            reject("NOT_ENOUGH_ACTUAL_SKINNED_VISIBLE_RAYS")
        directory=root/("frame_%02d"%int(key))
        file_set=data.get("files")
        if not isinstance(file_set,dict) or set(file_set)!={"beauty.png","render_passes.exr"}:
            reject("RENDER_FILES_MISSING")
        for name,receipt in file_set.items():
            path=directory/name
            if not isinstance(receipt,dict) or sha(path)!=receipt.get("sha256") or path.stat().st_size!=receipt.get("bytes"):
                reject("RENDER_BYTES_NOT_SOURCE_BOUND")
        decoded,meta=pixel_decode.decode(directory/"render_passes.exr")
        if meta["sha256"]!=file_set["render_passes.exr"]["sha256"]:
            reject("EXR_DECODER_SOURCE_DIGEST")
        z=perspective.compare_axial_depth(r,decoded)
        if z["joint_correct"]<64:reject("FAIL_AXIAL_DEPTH_OBJECT_SOURCE")
        posed[key]=np.asarray(evaluated,dtype=np.float64)
        pixel[key]=decoded
        check.update(z)
        check["rig_stable_ray_count"]=rig
        check["evaluated_mesh_sha256"]=data["evaluated_mesh_sha256"]
        rows[key]=check
    original=posed["0"]
    if float(np.max(np.linalg.norm(original-bind,axis=1)))>0.0001:
        reject("REST_POSE_NOT_IDENTITY")
    moves={}
    for key in ("1","2"):
        step=float(np.max(np.linalg.norm(posed[key]-original,axis=1)))
        if step<MIN_REAL_DEFORMATION:
            reject("REAL_ARMATURE_VERTEX_DEFORMATION_MISSING")
        beauty0=pixel["0"]["beauty"]
        beauty1=pixel[key]["beauty"]
        diff=np.stack([np.abs(beauty0[c].astype(np.float64)-beauty1[c].astype(np.float64))
                       for c in "RGB"],axis=-1)
        changed=float(np.mean(np.any(diff>2/255,axis=-1)))
        if changed<0.01:
            reject("REAL_CYCLES_ANIMATED_FRAME_NO_DIFFERENCE")
        moves[key]={"max_evaluated_vertex_displacement_from_rest":step,
                    "changed_beauty_pixel_fraction":changed}
    if float(np.max(np.linalg.norm(posed["1"]-posed["2"],axis=1)))<0.1:
        reject("OPPOSING_POSES_TOO_ALIKE")
    return {
        "schema":"r072.original.synthetic.actual-armature-lbs.v1",
        "status":"PASS_NARROW_ACTUAL_BLENDER_ARMATURE_LBS_EXR",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_MAKEHUMAN_WEIGHTED_SKIN_OR_BONE_RETARGET",
        "source_manifest_sha256":sha(root/"r072_source.json"),
        "independent_lbs_max_allowance":MAX_LBS_ERROR,
        "frames":rows,"observed_deformation":moves
    }

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    result=verify(args.root)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True),flush=True)
