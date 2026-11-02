#!/usr/bin/env python3
"""Actual native Blender original surrogate two-actor multi-camera production.
Rigid bone-weighted skin proxies with independent bone controls, NOT a
hierarchical human IK rig, authentic identity or independently proved anatomy.
"""
import hashlib,json,math,pathlib,sys
args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
if len(args)!=2:raise SystemExit("usage: blender -b --python render_native.py -- TRACE_JSON OUTPUT_DIR")
tracepath,output=map(pathlib.Path,args)
source=tracepath.read_bytes()
trace=json.loads(source)
if trace["schema"]!="scp.shadow.original-two-actor.v1" or trace["private_r009"]!="HELD_NOT_ACCEPTED":
 raise RuntimeError("NONORIGINAL_OR_UNADMITTED_SHADOW_SOURCE")
output.mkdir(parents=True,exist_ok=False)
import bpy
from mathutils import Vector,Matrix

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.frame_start=0
scene.frame_end=71
scene.render.fps=12
scene.render.engine="BLENDER_WORKBENCH"
scene.display.shading.light="STUDIO"
scene.display.shading.color_type="MATERIAL"
scene.display.shading.show_shadows=True
scene.render.resolution_x=480
scene.render.resolution_y=270
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=False

def material(name,rgba):
 m=bpy.data.materials.new(name)
 m.diffuse_color=rgba
 return m
grass=material("OriginalParkGrass",(.19,.36,.20,1))
path=material("OriginalParkPath",(.52,.47,.38,1))
trunk=material("OriginalParkTrunk",(.32,.22,.14,1))
leaf=material("OriginalParkFoliage",(.13,.36,.18,1))
teal=material("CobaltOriginalTeal",(.11,.59,.70,1))
amber=material("MarigoldOriginalOchre",(.94,.49,.23,1))
dark=material("OriginalJointAccent",(.12,.17,.24,1))

def cube(name,pos,size,mat):
 bpy.ops.mesh.primitive_cube_add(size=1,location=pos)
 ob=bpy.context.object
 ob.name=name
 ob.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 ob.data.materials.append(mat)
 return ob
cube("OriginalParkGround",(0,0,-.2),(15,7,.30),grass)
cube("OriginalPath",(0,0,-.035),(14,1.65,.055),path)

# Original authored environment shapes; no stock/protected asset downloads.
for index,(x,y,spread) in enumerate([(-5,3.1,1.),(-2.4,2.2,.9),(2.8,2.3,1.),(5.1,3.1,1.1)]):
 cube("Tree%dTrunk"%index,(x,y,.62),(.16,.18,1.26),trunk)
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=spread,location=(x,y,1.65))
 bpy.context.object.name="Tree%dCrown"%index
 bpy.context.object.data.materials.append(leaf)

rest={}
arms={}
proxy=[]
radii={"torso":.13,"neck":.07,"head":.13,
 "left_thigh":.077,"right_thigh":.077,
 "left_shin":.055,"right_shin":.055,
 "left_foot":.065,"right_foot":.065,
 "left_upperarm":.051,"right_upperarm":.051,
 "left_forearm":.041,"right_forearm":.041}

for actor in trace["actor_ids"]:
 initial=trace["frames"][0]["actors"][actor]["bones"]
 mat=teal if actor=="CobaltOriginal" else amber
 data=bpy.data.armatures.new(actor+"_Rig")
 arm=bpy.data.objects.new(actor+"_Armature",data)
 bpy.context.scene.collection.objects.link(arm)
 arms[actor]=arm
 bpy.context.view_layer.objects.active=arm
 arm.select_set(True)
 bpy.ops.object.mode_set(mode="EDIT")
 for bone,src in initial.items():
  head=Vector(src["head"]);tail=Vector(src["tail"])
  eb=data.edit_bones.new(bone)
  eb.head=head
  eb.tail=tail
  if (tail-head).length<.05:raise RuntimeError("ZERO_LENGTH_BONE")
  rest[(actor,bone)]=(head,tail)
 bpy.ops.object.mode_set(mode="OBJECT")
 arm.select_set(False)
 for bone,src in initial.items():
  head,tail=rest[(actor,bone)]
  axis=tail-head
  radius=radii[bone]
  bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=radius,depth=axis.length,
     location=(head+tail)*.5)
  ob=bpy.context.object
  ob.name=actor+"_"+bone+"_ActualSkinnedProxy"
  ob.rotation_mode="QUATERNION"
  ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(axis)
  bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
  ob.data.materials.append(dark if bone in ("left_foot","right_foot") else mat)
  group=ob.vertex_groups.new(name=bone)
  group.add(list(range(len(ob.data.vertices))),1.0,"REPLACE")
  deformer=ob.modifiers.new("ActualArmatureSkinning","ARMATURE")
  deformer.object=arm
  proxy.append((actor,bone,ob))
 bpy.context.view_layer.objects.active=arm
 for posebone in arm.pose.bones:
  posebone.rotation_mode="QUATERNION"

# 72 source-clock frames, all 26 bones, every key. Independent rest→pose
# rigid transform on separate bone controls; human hierarchical rig held.
for record in trace["frames"]:
 f=record["frame"]
 scene.frame_set(f)
 for actor,arm in arms.items():
  for bone,link in record["actors"][actor]["bones"].items():
   head0,tail0=rest[(actor,bone)]
   head=Vector(link["head"]);tail=Vector(link["tail"])
   delta=tail-head
   if abs(delta.length-(tail0-head0).length)>.001:
    raise RuntimeError("NATIVE_BONE_STRETCH_NOT_ALLOWED")
   quat=(tail0-head0).rotation_difference(delta)
   transform=(Matrix.Translation(head) @ quat.to_matrix().to_4x4()
              @ Matrix.Translation(-head0))
   p=arm.pose.bones[bone]
   p.matrix=transform @ p.bone.matrix_local
   p.keyframe_insert(data_path="location",frame=f,group=bone)
   p.keyframe_insert(data_path="rotation_quaternion",frame=f,group=bone)

# Verify evaluated Blender-bone endpoints match source ground truth.
sample_frames=(0,12,24,36,48,60,71)
worst_head=worst_tail=0.
for frame in sample_frames:
 scene.frame_set(frame)
 bpy.context.view_layer.update()
 rec=trace["frames"][frame]
 for actor,arm in arms.items():
  for bone,link in rec["actors"][actor]["bones"].items():
   p=arm.pose.bones[bone]
   dh=(p.head-Vector(link["head"])).length
   dt=(p.tail-Vector(link["tail"])).length
   worst_head=max(worst_head,dh)
   worst_tail=max(worst_tail,dt)
if max(worst_head,worst_tail)>.002:
 raise RuntimeError("ACTUAL_BLENDER_POSE_DISAGREES_WITH_SOURCE_ORACLE:"+str((worst_head,worst_tail)))

# Read evaluated mesh vertices; actual ARMATURE modifier must be active.
mesh_movement={}
def center_at(obj,frame):
 scene.frame_set(frame)
 bpy.context.view_layer.update()
 evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=evaluated.to_mesh()
 try:
  if len(mesh.vertices)<8:raise RuntimeError("MISSING_EVALUATED_SKIN_VERTICES")
  c=Vector((0,0,0))
  for vert in mesh.vertices:c+=vert.co
  return c/len(mesh.vertices)
 finally:evaluated.to_mesh_clear()
for actor,bone,ob in proxy:
 if bone in ("left_shin","right_shin","left_thigh","right_thigh","torso"):
  delta=(center_at(ob,12)-center_at(ob,0)).length
  if not math.isfinite(delta) or delta<.035:
   raise RuntimeError("NATIVE_SKIN_FROZEN_PROXY:"+actor+"_"+bone+":"+str(delta))
  mesh_movement[actor+"_"+bone]=round(delta,8)

cameras={}
for name,config in trace["cameras"].items():
 data=bpy.data.cameras.new(name+"_OriginalCameraData")
 obj=bpy.data.objects.new(name+"_OriginalCamera",data)
 bpy.context.scene.collection.objects.link(obj)
 obj.location=config["position"]
 target=Vector(config["target"])
 obj.rotation_euler=(target-obj.location).to_track_quat("-Z","Y").to_euler()
 data.type="ORTHO"
 data.ortho_scale=9.6
 cameras[name]=obj

for name,cam in cameras.items():
 scene.camera=cam
 folder=output/name
 folder.mkdir()
 for frame in range(72):
  scene.frame_set(frame)
  scene.render.filepath=str(folder/("frame_%03d.png"%frame))
  bpy.ops.render.render(write_still=True)

# Debug-time source-truth visualization uses the very same Blender viewport
# with colored planted-foot vs swing markers. Create AFTER both clean views
# have rendered; debug graphics can never contaminate clean evaluation video.
stance_color=material("TraceFootPlantedGreen",(.05,.90,.09,1))
swing_color=material("TraceFootInSwingYellow",(.98,.77,.08,1))
markers=[]
for actor in trace["actor_ids"]:
 for side in ("left","right"):
  for is_contact in (True,False):
   bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.085,location=(0,0,-3))
   obj=bpy.context.object
   obj.name=actor+"_"+side+("_ground_truth_PLANTED" if is_contact else "_ground_truth_SWING")
   obj.data.materials.append(stance_color if is_contact else swing_color)
   markers.append(obj)
   for record in trace["frames"]:
    frame=record["frame"]
    foot=record["actors"][actor]["feet"][side]
    obj.location=foot["ankle"]
    obj.keyframe_insert(data_path="location",frame=frame)
    obj.hide_render=bool(foot["contact"]) != is_contact
    obj.keyframe_insert(data_path="hide_render",frame=frame)
scene.camera=cameras["front"]
debug_folder=output/"debug_front"
debug_folder.mkdir()
for frame in range(72):
 scene.frame_set(frame)
 scene.render.filepath=str(debug_folder/("frame_%03d.png"%frame))
 bpy.ops.render.render(write_still=True)

receipt={
 "schema":"scp.shadow.original-native-blender-park.v1",
 "status":"PASS_PUBLIC_ORIGINAL_SYNTHETIC_SKIN_AND_2CAMERA_RENDER_ONLY",
 "trace_sha256":hashlib.sha256(source).hexdigest(),
 "blender":bpy.app.version_string,
 "actors":list(arms),"articulated_segments_per_actor":13,
 "proxy_meshes":len(proxy),"actual_armature_modifiers":len(proxy),
 "actual_skinned_moving_samples":mesh_movement,
 "maximum_source_to_bpy_head_m":worst_head,
 "maximum_source_to_bpy_tail_m":worst_tail,
 "rendered_frames_each_view":72,"render_views":list(cameras),
 "debug_source_ground_truth_markers":len(markers),
 "debug_front_frames":72,"debug_only_markers_not_clean_views":True,
 "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
 "human_identity":"NOT_VERIFIED","physical_anatomy":"UNKNOWN_NOT_INDEPENDENTLY_MEASURED",
 "true_hierarchical_ik":"NOT_RUN_UNPARENTED_PROXY_CONTROLS",
 "real_skinning_of_protected_body":"NOT_RUN","private_r009":"HELD_NOT_ACCEPTED"
}
with (output/"native_receipt.json").open("x") as f:
 json.dump(receipt,f,sort_keys=True,indent=2);f.write("\n")
print("PASS_ORIGINAL_SURROGATE_NATIVE_BLENDER_SKIN_AND_RENDER",json.dumps(receipt,sort_keys=True))
