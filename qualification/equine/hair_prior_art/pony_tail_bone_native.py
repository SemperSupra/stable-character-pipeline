#!/usr/bin/env python3
"""Original 30-joint caudal bone-chain proximity to hair follicle roots.

A pose bone segment is NOT an anatomical surface or a skinned tail shaft.
This measures 48-frame original source tail_2 and tail_3 card roots against
tail_1/tail_2/tail_3 bone centerlines. Prevents false '173mm from rump
means defective follicle' admission without new tail geometry or snapping.
"""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify as source_gate

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=3:
    raise SystemExit("usage: blender -b --python pony_tail_bone_native.py -- actual.blend capsule.json out.json")
source,capsule_file,out=map(Path,sys.argv[sys.argv.index("--")+1:])
if not source.is_file() or not capsule_file.is_file() or out.exists() or not 4096<source.stat().st_size<300_000_000:
    raise ValueError("missing/unbounded original source or output overwrite")
c=json.loads(capsule_file.read_text())
receipt=source_gate(c)
if hashlib.sha256(source.read_bytes()).hexdigest()!=c["source_blend_sha256"]:
    raise ValueError("original 30j source bytes disagree with capsule")
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
rig=bpy.data.objects.get("PonyRig30")
if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30:
    raise ValueError("original tail source 30j rig absent")
guides=[g for g in c["guides"] if g["region"]=="tail"]
if len(guides)!=2 or set(g["owner_bone"] for g in guides)!={"tail_2","tail_3"}:
    raise ValueError("missing original distinct caudal owners")
def project_segment(p,a,b):
    line=b-a
    if not math.isfinite(line.length) or line.length<.001:
        raise ValueError("original caudal bone has degenerate segment")
    t=max(0.,min(1.,(p-a).dot(line)/line.length_squared))
    q=a+t*line
    return float((p-q).length),float(t),[float(v) for v in q]
observations=[{"card_id":g["card_id"],"region":"tail","owner_bone":g["owner_bone"],"frames":[]} for g in guides]
scene=bpy.context.scene
for frame in range(1,49):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    segments={}
    for bone in ("tail_1","tail_2","tail_3"):
        p=rig.pose.bones.get(bone)
        if p is None:raise ValueError("missing actual original caudal pose bone "+bone)
        a=rig.matrix_world@p.head
        b=rig.matrix_world@p.tail
        if not .001<(b-a).length<2.:raise ValueError("unbounded original caudal bone length")
        segments[bone]=(a,b)
    for g,row in zip(guides,observations):
        root=Vector(g["samples"][frame-1]["root_m"])
        costs=[]
        for bone,(a,b) in segments.items():
            dist,t,closest=project_segment(root,a,b)
            costs.append({"bone":bone,"root_distance_to_bone_centerline_m":dist,
                          "bone_segment_fraction":t,
                          "nearest_bone_centerline_point_m":closest,
                          "bone_head_world_m":[float(v) for v in a],
                          "bone_tail_world_m":[float(v) for v in b]})
        costs.sort(key=lambda a:(a["root_distance_to_bone_centerline_m"],a["bone"]))
        owner=next(x for x in costs if x["bone"]==g["owner_bone"])
        row["frames"].append({
            "frame":frame,"source_root_m":g["samples"][frame-1]["root_m"],
            "closest_tail_bone":costs[0],
            "source_owner_tail_bone":owner,
            "candidate_bone_distances":sorted(costs,key=lambda x:x["bone"])})
output={"schema":"equine.pony.original_caudal_bone_centerline_48f.v1",
    "source_blend_sha256":c["source_blend_sha256"],
    "source_capsule_sha256":receipt["source_capsule_sha256"],
    "source_kind":"original_synthetic","rig":"PonyRig30",
    "frames":48,"bone_names":["tail_1","tail_2","tail_3"],
    "tail_cards":observations,
    "bone_centerline_is_surface":False,"new_tail_shaft_generated":False,
    "source_roots_snapped_to_bones":False,
    "anatomical_acceptance":False,"scientific_hold":"KEEP","release_or_CPE_admission":False}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n")
print("PONY_ORIGINAL_CAUDAL_SOURCE_BONE_CHAIN_48F",json.dumps({
    "tail_cards":[g["card_id"] for g in guides],
    "rest_f1_distances_m":[{"card_id":g["card_id"],
       "owner_bone_m":o["frames"][0]["source_owner_tail_bone"]["root_distance_to_bone_centerline_m"],
       "closest_bone":o["frames"][0]["closest_tail_bone"]["bone"],
       "nearest_centerline_m":o["frames"][0]["closest_tail_bone"]["root_distance_to_bone_centerline_m"]}
       for g,o in zip(guides,observations)],
    "science":"KEEP"},sort_keys=True))
