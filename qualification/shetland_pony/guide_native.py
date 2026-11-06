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
from mathutils import Vector
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

# Keep card source ownership exact and fail closed on weighted skin changes.
# Each original generated 4-vertex card is bound to one named head/neck/tail bone.
card_bones=[]
for i in range(1050):
    weights=v[4*i].groups
    if len(weights)!=1 or abs(weights[0].weight-1.)>1e-6:
        raise ValueError("unexpected original single-bone hair attachment")
    card_bones.append(groom.vertex_groups[weights[0].group].name)
if any(x not in {"head","neck","tail_1","tail_2","tail_3"} for x in card_bones):
    raise ValueError("unexpected follicle bone")

bands=((0,440,20),(440,670,15),(670,1050,20))
spans=[]
for start,stop,stride in bands:
    for lo in range(start,stop,stride):
        hi=min(stop,lo+stride)
        # Group noncontiguous hairs by the SAME skin-owner bone within a
        # small spatial window. Do not create hundreds of 1-card groups
        # merely because guide-generation interleaved head/neck owners.
        owners=sorted(set(card_bones[lo:hi]))
        for owner in owners:
            members=tuple(i for i in range(lo,hi) if card_bones[i]==owner)
            if members:
                spans.append((members,members[len(members)//2]))
if not 40<=len(spans)<=160:
    raise ValueError("unexpected reduced guide / bone partition count")

# Evaluate the actual animated rig before adding any hair morph keys. This
# supports pure hair and full face→tail→hair integration without hardcoded
# tail behavior, animation curve names, or guessed joint accelerations.
scene=bpy.context.scene
source_roots={j:[] for _,j in spans}
source_tips={j:[] for _,j in spans}
source_inverse_skin={}
for frame in range(1,49):
    scene.frame_set(frame)
    eval_obj=groom.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated=eval_obj.to_mesh()
    if len(evaluated.vertices)!=1050*4:
        raise ValueError("evaluated groom topology changed")
    world=eval_obj.matrix_world.copy()
    for _,j in spans:
        i=j*4
        source_roots[j].append(tuple(world@((evaluated.vertices[i].co+evaluated.vertices[i+1].co)*.5)))
        source_tips[j].append(tuple(world@((evaluated.vertices[i+2].co+evaluated.vertices[i+3].co)*.5)))
    eval_obj.to_mesh_clear()
    matrices={}
    for name in set(card_bones):
        pb=rig.pose.bones.get(name)
        if pb is None:raise ValueError("missing driven hair bone "+name)
        skin=rig.matrix_world @ pb.matrix @ rig.data.bones[name].matrix_local.inverted()
        if abs(skin.determinant())<1e-8:raise ValueError("singular hair skin")
        matrices[name]=skin.to_3x3().inverted()
    source_inverse_skin[frame]=matrices
scene.frame_set(1)

groups=[]
max_root_speed=0.
max_dynamic_lag=0.
for members,j in spans:
    trajectory=source_roots[j]
    initial=trajectory[0]
    direct=sub(source_tips[j][0],initial)
    length=norm(direct)
    if not (.08<=length<=.7):raise ValueError("invalid evaluated guide length")
    guide=Guide(initial,direct,length)
    # The first sample is both initial pin and frame 1; subsequent positions
    # are the exact deformed source root from the skinned motion, including
    # deliberate tail intent when loaded from the joined source .blend.
    root_frames=[initial]+trajectory
    history=simulate(guide,48,wind=(-4.,.55,0.),root_frames=root_frames)
    speed=max(norm(sub(a,b))*24 for a,b in zip(trajectory,trajectory[1:]))
    max_root_speed=max(max_root_speed,speed)
    max_dynamic_lag=max(max_dynamic_lag,max(norm(sub(history[f][-1],source_tips[j][f])) for f in range(48)))
    groups.append((members,j,history))
if len(groups)!=len(spans) or not groups:
    raise ValueError("unbounded guide simulation")

sample_frames=(1,7,13,19,25,31,37,43,48)
groom.shape_key_add(name="Basis",from_mix=False)
target_keys={}
max_tip_shift=0.
for frame in sample_frames:
    key=groom.shape_key_add(name="wind_%03d"%frame,from_mix=False)
    for members,j,history in groups:
        current=history[frame-1][-1]
        # The physics is in world coordinates. Skin-aware offsets must be
        # unrotated into each card's own rest/bind local coordinates before
        # the GLB exporter applies those bones again.
        delta=sub(current,source_tips[j][frame-1])
        shift=norm(delta)
        max_tip_shift=max(max_tip_shift,shift)
        if shift>.22:delta=tuple(x*.22/shift for x in delta)
        for i in members:
            local=source_inverse_skin[frame][card_bones[i]]@Vector(delta)
            for k in (2,3):
                data=key.data[i*4+k]
                for axis in range(3):
                    data.co[axis]+=local[axis]
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
    "max_observed_root_speed_m_s":max_root_speed,
    "max_world_tip_lag_m":max_dynamic_lag,
    "root_source":"actual evaluated Blender skin from 48 source frames",
    "source_tack_and_motion":"source .blend authoritative; not procedural guesses",
    "export":"baked morph guide approximations, NOT GLB native physics",
    "visual_collision_acceptance":"UNKNOWN","files":files}
(out/"hair_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("GUIDE_WIND_NATIVE_CANDIDATE_EMITTED",json.dumps({"groups":len(groups),"glb":glb.stat().st_size}))
