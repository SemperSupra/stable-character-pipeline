#!/usr/bin/env python3
"""Source-exact 30j bone/frame diagnostic. Original Blender 4.5 observer ONLY.

Records whether a single-owner original hair card actually follows the bone
orientation computed from the rig (rest-to-pose transform), across 48 frames.
No editing, no new hair physics, no production or biology acceptance.
"""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify as validate_source

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=3:
    raise SystemExit("usage: blender -b --python pony_skin_frame_native.py -- original.blend capsule.json evidence.json")
source,capsule_path,destination=map(Path,sys.argv[sys.argv.index("--")+1:])
if not source.is_file() or not capsule_path.is_file() or destination.exists():
    raise ValueError("source not readable or observer output would overwrite evidence")
if not 4096 < source.stat().st_size < 300000000:
    raise ValueError("original source size outside bound")
capsule=json.loads(capsule_path.read_text())
validation=validate_source(capsule)
if hashlib.sha256(source.read_bytes()).hexdigest()!=capsule["source_blend_sha256"]:
    raise ValueError("original Blender source SHA differs from approved capsule")
destination.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
rig=bpy.data.objects.get("PonyRig30")
groom=bpy.data.objects.get("geometric_coat_mane_tail")
if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30:
    raise ValueError("original 30-joint rig missing")
if groom is None or groom.type!="MESH" or len(groom.data.vertices)!=10500:
    raise ValueError("original 1050x10 card source missing")
skin_modifiers=[m for m in groom.modifiers if m.type=="ARMATURE" and m.object==rig]
if len(skin_modifiers)!=1:raise ValueError("original skinned card armature missing")
keys=[k for k in groom.data.shape_keys.key_blocks if k.name.startswith("wind_")] if groom.data.shape_keys else []
if len(keys)!=9:raise ValueError("original wind morph source count not nine")
records=[{"card_id":g["card_id"],"region":g["region"],"owner_bone":g["owner_bone"],
          "frames":[]} for g in capsule["guides"]]
scene=bpy.context.scene
bone_at_first={}
for frame in range(1,49):
    scene.frame_set(frame)
    for key in keys:key.value=0.0
    bpy.context.view_layer.update()
    obj=groom.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m=obj.to_mesh()
    try:
        if len(m.vertices)!=10500:raise ValueError("evaluated original card geometry changed")
        world=obj.matrix_world.copy()
        for rec,g in zip(records,capsule["guides"]):
            card=rec["card_id"]
            i=card*10
            actual_root=world@((m.vertices[i].co+m.vertices[i+1].co)*.5)
            actual_tip=world@((m.vertices[i+8].co+m.vertices[i+9].co)*.5)
            expected=g["samples"][frame-1]
            root=Vector(expected["root_m"]);tip=Vector(expected["tip_m"])
            if (actual_root-root).length>1e-5 or (actual_tip-tip).length>1e-5:
                raise ValueError("observed original source not equal to SHA-bound capsule at frame "+str(frame))
            bone=rec["owner_bone"]
            pose=rig.pose.bones.get(bone)
            rest=rig.data.bones.get(bone)
            if pose is None or rest is None:raise ValueError("owner bone not on exact pony")
            # World-space matrix maps rest card geometry through the actual
            # source owner's 30j pose, including rest-to-pose correction.
            bone_skin=rig.matrix_world@pose.matrix@rest.matrix_local.inverted()
            if abs(bone_skin.determinant())<1e-10:
                raise ValueError("singular bone skin in original 30j source")
            if card not in bone_at_first:bone_at_first[card]=bone_skin.copy()
            transport=bone_skin@bone_at_first[card].inverted()
            predicted_root=transport@Vector(g["samples"][0]["root_m"])
            start=g["samples"][0]
            source_dir=Vector(start["tip_m"])-Vector(start["root_m"])
            predicted_tip=predicted_root+(transport.to_3x3()@source_dir)
            q=transport.to_quaternion().normalized()
            if any(not math.isfinite(x) for x in q):
                raise ValueError("nonfinite original bone delta quaternion")
            rec["frames"].append({
                "frame":frame,
                "source_root_m":expected["root_m"],
                "source_tip_m":expected["tip_m"],
                "bone_transport_predicted_root_m":[float(x) for x in predicted_root],
                "bone_transport_predicted_tip_m":[float(x) for x in predicted_tip],
                "bone_transport_delta_quat_wxyz":[float(x) for x in q],
                "source_bone_transport_root_error_m":float((predicted_root-root).length),
                "source_bone_transport_tip_error_m":float((predicted_tip-tip).length)})
    finally:
        obj.to_mesh_clear()
output={
    "schema":"equine.pony.source_skin_bone_frame_48f.v1",
    "source_blend_sha256":capsule["source_blend_sha256"],
    "source_capsule_sha256":validation["source_capsule_sha256"],
    "source_kind":"original_synthetic",
    "rig":"PonyRig30","frame_count":48,"cards":records,
    "bone_transport_proof":"rest-to-pose source rig matrix, world-space",
    "wind_morphs_disabled":True,
    "scientific_hold":"KEEP","hair_material_accepted":False,
    "release_or_CPE_admission":False}
destination.write_text(json.dumps(output,sort_keys=True,indent=2)+"\n")
print("SCP_ORIGINAL_30J_BONE_FRAME_NATIVE",json.dumps({
    "cards":[rec["card_id"] for rec in records],
    "source_sha256":output["source_blend_sha256"],
    "max_bone_tip_reconstruction_error_m":max(f["source_bone_transport_tip_error_m"] for c in records for f in c["frames"]),
    "max_bone_root_reconstruction_error_m":max(f["source_bone_transport_root_error_m"] for c in records for f in c["frames"]),
    "science_hold":"KEEP"},sort_keys=True))
