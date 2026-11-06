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
    # Original shiny circular button eye is not equine. Retain its original
    # skinned mesh and provenance, refine to a flatter lateral almond ellipse.
    if len(eye.data.vertices)<100:raise ValueError("unexpected source eye geometry")
    for v in eye.data.vertices:
        v.co.x*=1.07
        v.co.y*=.35
        v.co.z*=.68
    eye.location.y+=sign*.003
    eye_shader=eye.data.materials[0]
    eye_shader.diffuse_color=(.018,.009,.006,1.)
    eye_shader.use_nodes=True
    eye_bsdf=eye_shader.node_tree.nodes.get("Principled BSDF")
    if eye_bsdf:
        eye_bsdf.inputs["Base Color"].default_value=(.018,.009,.006,1.)
        eye_bsdf.inputs["Roughness"].default_value=.38
    # Upper lid is a thin anatomically oriented moving skin curtain, not an
    # overlapping rigid ellipsoid. The top arc stays rooted as lower edge
    # translates across the visible eyeball via a blendshape.
    lidverts=[];lidfaces=[];samples=24
    for j in range(samples+1):
        u=2.*j/samples-1.
        arc=math.sqrt(max(0.,1.-u*u))
        x=.795+.036*u
        y=sign*(.159+.001*arc)
        upper=1.145+.023*arc
        lidverts.extend(((x,y,upper+.002),(x,y,upper-(.0025+.003*arc))))
    for j in range(samples):
        a=2*j
        lidfaces.extend(((a,a+1,a+2),(a+1,a+3,a+2)))
    lidmesh=bpy.data.meshes.new("upper_eyelid_"+side+"_skin")
    lidmesh.from_pydata(lidverts,[],lidfaces)
    lidmesh.update()
    lid=bpy.data.objects.new("upper_eyelid_"+side,lidmesh)
    bpy.context.collection.objects.link(lid)
    lid.data.materials.append(coat)
    group=lid.vertex_groups.new(name="head")
    group.add(list(range(len(lid.data.vertices))),1.,"REPLACE")
    lid.parent=rig
    mod=lid.modifiers.new("follow_synthetic_head","ARMATURE");mod.object=rig
    lid.shape_key_add(name="Basis",from_mix=False)
    closed=lid.shape_key_add(name="blink",from_mix=False)
    for j in range(samples+1):
        u=2.*j/samples-1.
        arc=math.sqrt(max(0.,1.-u*u))
        closed.data[2*j+1].co.z=1.145-.021*arc
    shapes["blink_"+side]=lid.data.shape_keys.key_blocks["blink"]
    # Flatten glossy nostril-sphere proxy into a matte flexible equine slit.
    nostril=bpy.data.objects["nostril_"+side]
    nostril.location.y+=sign*.014
    for vertex in nostril.data.vertices:
        vertex.co.x*=.64;vertex.co.y*=.26;vertex.co.z*=1.08
    nostril_mat=bpy.data.materials.get("nostril_shadow") or bpy.data.materials.new("nostril_shadow")
    nostril_mat.use_nodes=True
    nostril_mat.diffuse_color=(.015,.012,.013,1.)
    nose_bsdf=nostril_mat.node_tree.nodes.get("Principled BSDF")
    if nose_bsdf:
        nose_bsdf.inputs["Base Color"].default_value=(.015,.012,.013,1.)
        nose_bsdf.inputs["Roughness"].default_value=.98
    nostril.data.materials.clear();nostril.data.materials.append(nostril_mat)
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

# Secondary independent close-up camera: make eyelids/nostrils observable.
from mathutils import Vector
scene=bpy.context.scene
original_camera=scene.camera
close_data=bpy.data.cameras.new("FACIAL_QA_ORTHO")
close_camera=bpy.data.objects.new("FacialCloseupQA",close_data)
scene.collection.objects.link(close_camera)
close_camera.location=(1.55,-1.35,1.45)
close_camera.rotation_euler=(Vector((.92,-.04,1.055))-close_camera.location).to_track_quat('-Z','Y').to_euler()
close_data.type="ORTHO";close_data.ortho_scale=.72
scene.camera=close_camera
for frame in (10,22,30,40):
    scene.frame_set(frame)
    scene.render.filepath=str(outdir/("face_detail_%03d.png"%frame))
    bpy.ops.render.render(write_still=True)
scene.camera=original_camera

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
# Native dimensional guard; limits are source-specific engineering bounds.
eye_dimensions={}
for side in ("L","R"):
    eye=bpy.data.objects["eye_"+side]
    axes=[(min(v.co[i] for v in eye.data.vertices),max(v.co[i] for v in eye.data.vertices)) for i in range(3)]
    radii=[(hi-lo)*.5 for lo,hi in axes]
    if not (.030<radii[0]<.042 and .003<radii[1]<.007 and .017<radii[2]<.025):
        raise ValueError("eye did not acquire flatter equine ellipse")
    eye_dimensions[side]={"rest_eye_local_radii_m":radii,
        "left_right_source_mesh":"original synthetic eye; modified non-destructively in derivative"}
receipt={"schema":"equine.face.proof.v1","channels":list(sample(1)), "frames":FRAMES,
         "source_sha256":hashlib.sha256(input_scene.read_bytes()).hexdigest(),
         "morph_targets":[o for o in shapes],
         "eyes":eye_dimensions,
         "quality":"synthetic engineering actuator proof ONLY; EquiFACS biological/visual UNKNOWN",
         "files":files}
(outdir/"face_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("FACE_NATIVE_CANDIDATE_EMITTED",json.dumps({k:v["bytes"] for k,v in files.items()}))
