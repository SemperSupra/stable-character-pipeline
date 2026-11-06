#!/usr/bin/env python3
"""Extract six *actual* source rig-deformed 48f pony hair trajectories, no authoring.

Source is the current 4.5 original-black skinned groom .blend. Built morph
wind keys are suppressed to isolate 30-joint skin motion. This is an observer
that saves a small source-grounded JSON capsule, not an independent solver.
"""
import bpy
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pony_source_trajectory import classify,IDS,SCHEMA

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=2:
    raise SystemExit("usage: blender -b --python pony_source_extract_native.py -- <actual.blend> <source.json>")
source,out=map(Path,sys.argv[sys.argv.index("--")+1:])
if not source.is_file() or out.exists() or not 1024<source.stat().st_size<300000000:
    raise ValueError("missing/oversized original blend or overwrite")
out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
rig=bpy.data.objects.get("PonyRig30")
groom=bpy.data.objects.get("geometric_coat_mane_tail")
if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=30:
    raise ValueError("source exact 30-joint rig absent")
if groom is None or groom.type!="MESH" or len(groom.data.vertices)!=10500:
    raise ValueError("original curved hair topology absent")
if not any(m.type=="ARMATURE" and m.object==rig for m in groom.modifiers):
    raise ValueError("groom not attached to original rig")
records=[]
for region,ids in IDS.items():
    for card in ids:
        vertex=groom.data.vertices[card*10]
        if len(vertex.groups)!=1:
            raise ValueError("source follicle skin assignment not single owner")
        assignment=vertex.groups[0]
        owner=groom.vertex_groups[assignment.group].name
        if abs(assignment.weight-1)>1e-6:
            raise ValueError("non-exact original skin weight")
        records.append({"card_id":card,"region":region,"owner_bone":owner,"samples":[]})
scene=bpy.context.scene
if scene.frame_start>1 or scene.frame_end<48:
    raise ValueError("incomplete original source sequence")
keys=[x for x in groom.data.shape_keys.key_blocks if x.name.startswith("wind_")] if groom.data.shape_keys else []
if len(keys)!=9:
    raise ValueError("missing nine source-original baked hair animation keys")
for f in range(1,49):
    scene.frame_set(f)
    for key in keys:key.value=0.
    bpy.context.view_layer.update()
    evaluated=groom.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    if mesh is None or len(mesh.vertices)!=10500:
        raise ValueError("hair evaluated card topology invalid")
    mat=evaluated.matrix_world
    try:
        for rec in records:
            i=rec["card_id"]*10
            root=mat@((mesh.vertices[i].co+mesh.vertices[i+1].co)*.5)
            tip=mat@((mesh.vertices[i+8].co+mesh.vertices[i+9].co)*.5)
            rec["samples"].append({"frame":f,"root_m":[float(q) for q in root],
                                  "tip_m":[float(q) for q in tip]})
    finally:
        evaluated.to_mesh_clear()
capsule={"schema":SCHEMA,"source_kind":"original_synthetic",
         "source_blend_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
         "rig":"PonyRig30","cards_total":1050,"vertices_per_card":10,
         "fps":24,"frames":48,"guides":records,"visual_science_hold":"KEEP"}
gate=classify(capsule)
out.write_text(json.dumps(capsule,sort_keys=True,indent=2)+"\n")
(out.parent/"pony_source_check.json").write_text(json.dumps(gate,sort_keys=True,indent=2)+"\n")
print("ACTUAL_PONY_SKIN_ROOTS_48F",json.dumps({
    "card_ids":[x["card_id"] for x in records],
    "owner_bones":[x["owner_bone"] for x in records],
    "source_blend_sha256":capsule["source_blend_sha256"],
    "capsule_sha256":gate["source_capsule_sha256"],
    "sciencestatus":"UNQUALIFIED_SIMULATION"},sort_keys=True))
