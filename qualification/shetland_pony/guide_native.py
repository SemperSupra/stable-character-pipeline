#!/usr/bin/env python3
"""Native Blender proof for physically evolved guide-hair deltas.

Guide simulation is in portable stdlib. Bake 9 key morph-target profiles
into original 1050-card mane/forelock/tail mesh for GLB interoperability.
Not full wind physics in GLB and not individual-strand contact validated.
"""
import bpy
import json
import math
import hashlib
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from guide_dynamics import Guide,simulate,report,norm,sub

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=2:
    raise SystemExit("usage: <input.blend> <outdir>")
source,out=map(Path,sys.argv[sys.argv.index("--")+1:])
if not source.is_file():raise FileNotFoundError(source)
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
rig=bpy.data.objects.get("PonyRig30")
groom=bpy.data.objects.get("geometric_coat_mane_tail")
if rig is None or len(rig.data.bones)!=30 or groom is None or groom.type!="MESH":
    raise ValueError("source rig/groom missing")
if len(groom.data.vertices)!=1050*4:
    raise ValueError("changed groom topology needs explicit remap")
# Reject a partial egg removal, but allow this proof to run alone or after
# the deliberate-tail corrective: long hair stays skinned to source bones.
volumes=[bpy.data.objects.get("tail_volume_"+str(i)) for i in range(3)]
if sum(x is not None for x in volumes) not in (0,3):
    raise ValueError("partial original tail volume topology")
for obj in volumes:
    if obj is not None:bpy.data.objects.remove(obj,do_unlink=True)
v=groom.data.vertices
roots=[];tips=[]
for i in range(1050):
    roots.append(tuple((v[i*4].co+v[i*4+1].co)*.5))
    tips.append(tuple((v[i*4+2].co+v[i*4+3].co)*.5))

bands=((0,440,20),(440,670,15),(670,1050,20))
groups=[]
for start,stop,stride in bands:
    for lo in range(start,stop,stride):
        hi=min(stop,lo+stride)
        j=(lo+hi-1)//2
        direct=sub(tips[j],roots[j])
        length=norm(direct)
        if not (.08<=length<=.7):
            raise ValueError("out of guide length bounds")
        guide=Guide(roots[j],direct,length)
        history=simulate(guide,48,wind=(-4.0,.55,0.),root_velocity=(0.,0.,0.))
        groups.append((lo,hi,j,history))
if len(groups)<40 or len(groups)>80:raise ValueError("invalid reduced guide groups")

sample_frames=(1,7,13,19,25,31,37,43,48)
groom.shape_key_add(name="Basis",from_mix=False)
target_keys={}
max_tip_shift=0.
for frame in sample_frames:
    key=groom.shape_key_add(name="wind_%03d"%frame,from_mix=False)
    for lo,hi,j,history in groups:
        current=history[frame-1][-1]
        delta=sub(current,tips[j])
        shift=norm(delta)
        max_tip_shift=max(max_tip_shift,shift)
        # Keep synthetic displacement bounded; collision remains a separate gate.
        if shift>.22:delta=tuple(x*.22/shift for x in delta)
        for i in range(lo,hi):
            for k in (2,3):
                data=key.data[i*4+k]
                for axis in range(3):
                    data.co[axis]+=delta[axis]
    target_keys[frame]=key

for frame in sample_frames:
    bpy.context.scene.frame_set(frame)
    for own_frame,key in target_keys.items():
        key.value=1.0 if own_frame==frame else 0.0
        key.keyframe_insert(data_path="value",frame=frame)
for frame in (1,13,25,43):
    bpy.context.scene.frame_set(frame)
    bpy.context.scene.render.filepath=str(out/("hair_%03d.png"%frame))
    bpy.ops.render.render(write_still=True)
# Separate detail views for mane and tail motion, two frames each.
from mathutils import Vector
scene=bpy.context.scene
original_camera=scene.camera
for region,loc,look,scale in (
    ("mane",(1.05,-1.55,1.50),(.46,0.,1.11),1.07),
    ("tail",(-1.72,-1.42,1.30),(-.73,0.,.64),1.25),
):
    cam_data=bpy.data.cameras.new("HAIR_QA_"+region)
    camera=bpy.data.objects.new("HairDetailQA_"+region,cam_data)
    scene.collection.objects.link(camera)
    camera.location=loc
    camera.rotation_euler=(Vector(look)-camera.location).to_track_quat('-Z','Y').to_euler()
    cam_data.type="ORTHO";cam_data.ortho_scale=scale
    scene.camera=camera
    for frame in (13,25):
        scene.frame_set(frame)
        scene.render.filepath=str(out/("hair_detail_"+region+"_%03d.png"%frame))
        bpy.ops.render.render(write_still=True)
scene.camera=original_camera

bpy.context.scene.frame_set(1)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.context.scene.objects:
    if obj.type=="ARMATURE" or (obj.type=="MESH" and obj.name!="ground"):obj.select_set(True)
bpy.context.view_layer.objects.active=rig
glb=out/"equine_longhair_wind.glb"
bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",
                          use_selection=True,export_skins=True,export_animations=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/"equine_longhair_wind.blend"))
files={}
for p in [glb,*sorted(out.glob("hair_*.png"))]:
    if p.stat().st_size<500:raise ValueError("missing evidence "+p.name)
    files[p.name]={"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
receipt={"schema":"equine.longhair.native.proof.v1","source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
    "source_cards":1050,"guide_groups":len(groups),"baked_shape_keys":len(target_keys),
    "sim_physics_hz":120,"render_fps":24,"frames":48,
    "max_raw_tip_shift_m":max_tip_shift,"clamp_m":.22,
    "export":"baked morph guide approximations, NOT GLB native physics",
    "visual_collision_acceptance":"UNKNOWN","files":files}
(out/"hair_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("GUIDE_WIND_NATIVE_CANDIDATE_EMITTED",json.dumps({"groups":len(groups),"glb":glb.stat().st_size}))
