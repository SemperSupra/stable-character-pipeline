#!/usr/bin/env python3
"""Actual Blender articulated tail-dock proof, separate from hair solver."""
import bpy
import json
import hashlib
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tail_intent import FRAMES,TAIL_BONES,sample,timeline,validate_timeline

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=2:
    raise SystemExit("expected <input.blend> <outdir>")
source,out=map(Path,sys.argv[sys.argv.index("--")+1:])
if not source.is_file():raise FileNotFoundError(source)
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
rig=bpy.data.objects.get("PonyRig30")
if rig is None or len(rig.data.bones)!=30:raise ValueError("missing original 30-bone rig")
if any(b not in rig.pose.bones for b in TAIL_BONES):raise ValueError("tail topology incomplete")
# The original three decorative UV ellipsoids form a visible rigid egg at
# the tail tip. Omit them from this non-destructive native derivative; retain
# all 380 skinned tail hairs and the articulated dock bones.
removed=[]
for i in range(3):
    obj=bpy.data.objects.get("tail_volume_"+str(i))
    if obj is not None:
        removed.append(obj.name)
        bpy.data.objects.remove(obj,do_unlink=True)
if len(removed)!=3:raise ValueError("unexpected original tail ellipsoid source")
values=[sample(f) for f in range(1,FRAMES+1)]
validate_timeline(values)
for frame,angles in enumerate(values,1):
    bpy.context.scene.frame_set(frame)
    for b,v in angles.items():
        bone=rig.pose.bones[b]
        bone.rotation_mode="XYZ"
        bone.rotation_euler[1]=v
        bone.keyframe_insert(data_path="rotation_euler",index=1,frame=frame,group="voluntary_tail_swish")
    if frame in (1,15,24,31):
        bpy.context.scene.render.filepath=str(out/("tail_%03d.png"%frame))
        bpy.ops.render.render(write_still=True)
# Rear-oblique camera makes lateral tail-dock movement observable.
from mathutils import Vector
scene=bpy.context.scene
original_camera=scene.camera
rear_data=bpy.data.cameras.new("TAIL_REAR_QA_ORTHO")
rear_camera=bpy.data.objects.new("TailRearQA",rear_data)
scene.collection.objects.link(rear_camera)
rear_camera.location=(-2.05,-.50,1.45)
rear_camera.rotation_euler=(Vector((-.68,0.,.68))-rear_camera.location).to_track_quat('-Z','Y').to_euler()
rear_data.type="ORTHO";rear_data.ortho_scale=1.45
scene.camera=rear_camera
for frame in (1,15,24,31):
    scene.frame_set(frame)
    scene.render.filepath=str(out/("tail_rear_%03d.png"%frame))
    bpy.ops.render.render(write_still=True)
scene.camera=original_camera

bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.context.scene.objects:
    if obj.type=="ARMATURE" or (obj.type=="MESH" and obj.name!="ground"):obj.select_set(True)
bpy.context.view_layer.objects.active=rig
glb=out/"equine_tail_intent.glb"
bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",
                          use_selection=True,export_skins=True,export_animations=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/"equine_tail_intent.blend"))
files={}
for p in [glb,*sorted(out.glob("tail_*.png"))]:
    if p.stat().st_size<500:raise ValueError("no evidence "+p.name)
    files[p.name]={"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
receipt={"schema":"equine.tail.intent.proof.v1","frames":FRAMES,"joint_names":TAIL_BONES,
    "source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
    "hair_simulation":"NOT_IN_SCOPE","biomechanical_acceptance":"UNKNOWN",
    "actual_curve_samples":values,"files":files}
(out/"tail_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("TAIL_INTENT_NATIVE_CANDIDATE_EMITTED",glb.stat().st_size)
