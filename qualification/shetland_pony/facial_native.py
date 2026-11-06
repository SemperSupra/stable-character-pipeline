#!/usr/bin/env python3
"""Native Blender synthetic equine facial actuator qualification adapter.

Opens the exact parent producer's .blend; does not mutate original producer.
Produces real morph-target eyelids and nostril flare plus ear/jaw pose tracks.
Visual fidelity remains unaccepted; these are engineering proof controls.
"""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path

here=Path(__file__).resolve().parent
sys.path.insert(0,str(here))
from facial_controls import FRAMES,SCHEMA,sample,timeline

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=2:
    raise SystemExit("usage: blender -b --python facial_native.py -- <input.blend> <output_dir>")
input_scene,outdir=map(Path,sys.argv[sys.argv.index("--")+1:])
if not input_scene.is_file():raise FileNotFoundError(input_scene)
outdir.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(input_scene.resolve()))
rig=bpy.data.objects.get("PonyRig30")
if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30:
    raise ValueError("missing 30-joint source armature")
for required in ("jaw","ear_L","ear_R"):
    if required not in rig.pose.bones:raise ValueError("missing "+required)
for required in ("eye_L","eye_R","nostril_L","nostril_R"):
    if required not in bpy.data.objects:raise ValueError("missing "+required)

coat=bpy.data.materials.get("coat_black")
if coat is None:raise ValueError("missing original black coat")
shapes={}
for side in ("L","R"):
    eye=bpy.data.objects["eye_"+side]
    sign=-1 if side=="L" else 1
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=(.795,sign*.166,1.169))
    lid=bpy.context.object
    lid.name="upper_eyelid_"+side
    lid.scale=(.037,.011,.018)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    lid.data.materials.append(coat)
    group=lid.vertex_groups.new(name="head")
    group.add(list(range(len(lid.data.vertices))),1.,"REPLACE")
    lid.parent=rig
    mod=lid.modifiers.new("follow_synthetic_head","ARMATURE");mod.object=rig
    lid.shape_key_add(name="Basis",from_mix=False)
    closed=lid.shape_key_add(name="blink",from_mix=False)
    for v in closed.data:v.co.z-=.033
    shapes["blink_"+side]=lid.data.shape_keys.key_blocks["blink"]
    nostril=bpy.data.objects["nostril_"+side]
    nostril.shape_key_add(name="Basis",from_mix=False)
    flare=nostril.shape_key_add(name="flare",from_mix=False)
    for v in flare.data:
        v.co.x*=1.22;v.co.z*=1.22
    shapes["nostril_"+side]=nostril.data.shape_keys.key_blocks["flare"]

for frame in range(1,FRAMES+1):
    bpy.context.scene.frame_set(frame)
    values=sample(frame)
    for channel,key in shapes.items():
        key.value=values[channel]
        key.keyframe_insert(data_path="value",frame=frame)
    for bone,channel in (("ear_L","ear_L_yaw_deg"),("ear_R","ear_R_yaw_deg"),
                         ("jaw","jaw_open_deg")):
        pb=rig.pose.bones[bone]
        pb.rotation_mode="XYZ"
        angle=math.radians(values[channel])
        if bone=="jaw":angle=-angle
        pb.rotation_euler[2]=angle
        pb.keyframe_insert(data_path="rotation_euler",index=2,frame=frame,group="equine_facial_actions")
    if frame in (10,22,30,40):
        bpy.context.scene.render.filepath=str(outdir/("face_%03d.png"%frame))
        bpy.ops.render.render(write_still=True)

bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.context.scene.objects:
    if obj.type=="ARMATURE" or (obj.type=="MESH" and obj.name!="ground"):
        obj.select_set(True)
bpy.context.view_layer.objects.active=rig
target=outdir/"equine_face_native.glb"
bpy.ops.export_scene.gltf(filepath=str(target),export_format="GLB",
                          use_selection=True,export_skins=True,export_animations=True)
bpy.ops.wm.save_as_mainfile(filepath=str(outdir/"equine_face_native.blend"))
files={}
for p in [target,*sorted(outdir.glob("face_*.png"))]:
    if p.stat().st_size<500:raise ValueError("undersized evidence "+p.name)
    files[p.name]={"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
receipt={"schema":"equine.face.proof.v1","channels":list(sample(1)), "frames":FRAMES,
         "source_sha256":hashlib.sha256(input_scene.read_bytes()).hexdigest(),
         "morph_targets":[o for o in shapes],
         "quality":"synthetic engineering actuator proof ONLY; EquiFACS biological/visual UNKNOWN",
         "files":files}
(outdir/"face_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("FACE_NATIVE_CANDIDATE_EMITTED",json.dumps({k:v["bytes"] for k,v in files.items()}))
