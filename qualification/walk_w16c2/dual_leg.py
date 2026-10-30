"""W16-C2 original synthetic two-actor, TWO-LEG weighted Blender gait prototype.

Distinct independent native acceptance; derived only from prior original W16-C
methods and W15 independent non-bpy glTF reader. No private character or
anatomical/force claim, no inferred source timing or labeled heel/toe.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Quaternion,Vector
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w16c"))
from integrated_3d import analytic_ik,evaluated_points,min_pair_match
SOURCE="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
FRAMES=(0,12,24,36,48,60,71)
FPS=12
ACTORS=(("CobaltOriginal",-1.65),("MarigoldOriginal",1.65))
LEGS=(("Left",-1),("Right",1))
LEVELS=(1.34,1.12,.91,.80,.69,.48,.27)
TOL=5e-4
def add_actor(name,x,profile):
 arm_data=bpy.data.armatures.new(name+"_ArmatureData")
 arm=bpy.data.objects.new(name+"_Skeleton",arm_data)
 bpy.context.scene.collection.objects.link(arm)
 arm.location=(x,0,0)
 bpy.context.view_layer.objects.active=arm
 arm.select_set(True)
 bpy.ops.object.mode_set(mode="EDIT")
 for leg,sign in LEGS:
  upper=arm_data.edit_bones.new(leg+"Upper")
  upper.head=(.22*sign,0,1.40)
  upper.tail=(.22*sign,0,.80)
  lower=arm_data.edit_bones.new(leg+"Lower")
  lower.head=(.22*sign,0,.80)
  lower.tail=(.22*sign,0,.20)
  lower.parent=upper;lower.use_connect=True
 bpy.ops.object.mode_set(mode="OBJECT")
 for b in arm.pose.bones:b.rotation_mode="QUATERNION"
 verts=[];faces=[]
 for leg,sign in LEGS:
  off=len(verts)
  for z in LEVELS:
   cx=sign*.22
   verts.extend(((cx-.10,-.07,z),(cx+.08,-.065,z),
                 (cx+.095,.085,z),(cx-.085,.080,z)))
  for r in range(len(LEVELS)-1):
   for k in range(4):
    a=off+r*4+k;b=off+r*4+(k+1)%4
    c=off+(r+1)*4+k;d=off+(r+1)*4+(k+1)%4
    faces.extend(((a,c,b),(b,c,d)))
 mesh=bpy.data.meshes.new(name+"_source_mesh")
 mesh.from_pydata(verts,[],faces);mesh.update()
 for f in mesh.polygons:f.use_smooth=True
 obj=bpy.data.objects.new(name+"_SkinnedMesh",mesh)
 bpy.context.scene.collection.objects.link(obj)
 obj.parent=arm
 for leg_i,(leg,sign) in enumerate(LEGS):
  u=obj.vertex_groups.new(name=leg+"Upper")
  l=obj.vertex_groups.new(name=leg+"Lower")
  for k,z in enumerate(LEVELS):
   upper_weight=1 if z>=.91 else (0 if z<=.48 else (.5 if z==.80 else .25))
   idx=list(range(leg_i*28+k*4,leg_i*28+k*4+4))
   if upper_weight:u.add(idx,upper_weight,"REPLACE")
   if upper_weight<1:l.add(idx,1-upper_weight,"REPLACE")
 mod=obj.modifiers.new("OriginalWeighted4BoneSkin","ARMATURE");mod.object=arm
 arm["source_rights"]=SOURCE;obj["source_rights"]=SOURCE
 return arm,obj

def animate_actor(name,arm,profile):
 source_axis=Vector((0,0,-1))
 data=arm.data
 if len(arm.pose.bones)!=4:raise ValueError("W16C2_TWO_LEG_HIERARCHY_MISSING")
 residuals=[]
 for f in FRAMES:
  bpy.context.scene.frame_set(f)
  fraction=f/71.0
  direction=1 if profile=="forward" else -1
  forward=direction*.16*fraction
  arm.location=(arm.location.x if f==0 else arm["fixed_x"],forward,0)
  if f==0:arm["fixed_x"]=float(arm.location.x)
  for leg,sign in LEGS:
   upper=arm.pose.bones[leg+"Upper"]
   lower=arm.pose.bones[leg+"Lower"]
   if f==0:
    q_upper=Quaternion((1,0,0,0));q_lower=Quaternion((1,0,0,0))
   else:
    hip=Vector((arm.location.x+sign*.22,forward,1.40))
    phase=2*math.pi*fraction+(math.pi if sign<0 else 0)
    stride=.18*math.sin(phase)
    rise=.04*max(0.,math.cos(phase))
    ankle=Vector((hip.x,forward+stride,.25+rise))
    pole=hip+Vector((sign*.36,.48,-.42))
    knee=analytic_ik(hip,ankle,pole)
    world_upper=source_axis.rotation_difference((knee-hip).normalized())
    world_lower=source_axis.rotation_difference((ankle-knee).normalized())
    ru=data.bones[leg+"Upper"].matrix_local.to_quaternion()
    rl=data.bones[leg+"Lower"].matrix_local.to_quaternion()
    q_upper=ru.inverted()@world_upper@ru
    q_lower=rl.inverted()@world_upper.inverted()@world_lower@rl
   upper.rotation_quaternion=q_upper
   lower.rotation_quaternion=q_lower
   bpy.context.view_layer.update()
   if f>0:
    native_knee=arm.matrix_world@upper.tail
    native_end=arm.matrix_world@lower.tail
    knee_res=(native_knee-knee).length
    end_res=(native_end-ankle).length
    residuals.extend((knee_res,end_res))
    if max(knee_res,end_res)>1e-3:
     print("W16C2_NATIVE_FK_FIRST_FAILURE",json.dumps({
      "actor":name,"leg":leg,"frame":f,
      "knee_residual":knee_res,"ankle_residual":end_res,
      "source_knee":list(knee),"native_knee":list(native_knee),
      "source_end":list(ankle),"native_end":list(native_end)
     }),flush=True)
     raise ValueError("W16C2_REAL_NATIVE_TWO_LEG_IK_FK")
   upper.keyframe_insert(data_path="rotation_quaternion",frame=f)
   lower.keyframe_insert(data_path="rotation_quaternion",frame=f)
  arm.keyframe_insert(data_path="location",frame=f)
 return max(residuals,default=0.)

def setup_camera(scene):
 data=bpy.data.cameras.new("SyntheticTwoLegCamera")
 data.type="ORTHO";data.ortho_scale=5.5
 camera=bpy.data.objects.new("SyntheticTwoLegCamera",data)
 scene.collection.objects.link(camera)
 camera.location=(0,-7,2.)
 vec=Vector((0,0,.75))-camera.location
 camera.rotation_euler=vec.to_track_quat("-Z","Y").to_euler()
 scene.camera=camera
 scene.render.engine="BLENDER_WORKBENCH"
 scene.render.resolution_x=320;scene.render.resolution_y=180
 scene.render.resolution_percentage=100

def bind_actions(assets):
 for name in assets:
  arm=bpy.data.objects.get(name+"_Skeleton")
  if arm is None or arm.type!="ARMATURE":raise ValueError("W16C2_ARMATURE_NOT_REIMPORTED")
  action=bpy.data.actions.get(arm.name+"Action")
  if action is None:raise ValueError("W16C2_EXACT_ACTION_MISSING")
  slots=[s for s in action.slots if s.target_id_type=="OBJECT"]
  if len(slots)!=1:raise ValueError("W16C2_ACTION_SLOT_AMBIGUOUS")
  anim=arm.animation_data_create()
  if anim.action is not None and anim.action is not action:raise ValueError("W16C2_DIFFERENT_ACTION_BOUND")
  anim.action=action;anim.action_slot=slots[0]
  if anim.action is not action or anim.action_slot!=slots[0]:raise ValueError("W16C2_ACTION_SLOT_NOT_LIVE")

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--profile",choices=("forward","outward"),required=True)
 a.add_argument("--out",required=True)
 opts=a.parse_args()
 out=Path(opts.out);out.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene;scene.render.fps=FPS
 scene.frame_start=0;scene.frame_end=71
 assets={}
 fk_error=0.
 for name,x in ACTORS:
  arm,obj=add_actor(name,x,opts.profile)
  fk_error=max(fk_error,animate_actor(name,arm,opts.profile))
  assets[name]=(arm,obj)
 if len(assets)!=2 or any(len(arm.pose.bones)!=4 for arm,_ in assets.values()):
  raise ValueError("W16C2_TWO_ACTORS_FOUR_BONES_EACH")
 setup_camera(scene)
 native={name:{str(f):evaluated_points(obj,f) for f in FRAMES} for name,(_,obj) in assets.items()}
 if any(len(v["0"])!=56 for v in native.values()):raise ValueError("W16C2_EXPECT_56_INDEXED_PER_ACTOR")
 for name,(_,obj) in assets.items():
  vertex_assignments=[len(v.groups) for v in obj.data.vertices]
  if min(vertex_assignments)<1 or max(vertex_assignments)<2:raise ValueError("W16C2_MIXED_WEIGHTS_NOT_PROVEN")
 scene.frame_set(0)
 blend=out/"original_two_actors_dual_leg.blend"
 bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
 glb=out/"original_two_actors_dual_leg.glb"
 bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",export_animations=True)
 if not (glb.stat().st_size>1000 and blend.stat().st_size>10000):
  raise ValueError("W16C2_EDITABLE_OR_GLTF_MISSING")
 scene.render.image_settings.file_format="FFMPEG"
 scene.render.ffmpeg.format="MPEG4";scene.render.ffmpeg.codec="H264"
 scene.render.ffmpeg.constant_rate_factor="HIGH"
 video=out/"original_two_actors_dual_leg_preview.mp4"
 scene.render.filepath=str(video.resolve())
 bpy.ops.render.render(animation=True)
 if not video.exists() or video.stat().st_size<=1000:raise ValueError("W16C2_H264_MISSING")
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.context.scene.render.fps=FPS
 bpy.ops.import_scene.gltf(filepath=str(glb.resolve()))
 imported={}
 for obj in bpy.data.objects:
  if obj.type=="MESH" and any(m.type=="ARMATURE" for m in obj.modifiers):
   imported[obj.name.split("_SkinnedMesh")[0]]=obj
 if set(imported)!=set(assets):raise ValueError("W16C2_IMPORTED_ORIGINAL_ACTOR_SET")
 if len([o for o in bpy.data.objects if o.type=="ARMATURE"])!=2:
  raise ValueError("W16C2_IMPORTED_ARMATURE_SET")
 bind_actions(assets)
 count=0;maximum=0.;motion_min=math.inf
 for name,obj in imported.items():
  mapping=min_pair_match(native[name]["0"],evaluated_points(obj,0))
  moved=0.
  for f in FRAMES:
   source=native[name][str(f)]
   observed=evaluated_points(obj,f)
   if len(source)!=56 or len(observed)!=len(mapping):raise ValueError("W16C2_INDEXED_TOPOLOGY_CHANGED")
   for i,k in enumerate(mapping):
    err=math.dist(source[i],observed[k])
    maximum=max(maximum,err)
    if err>TOL:
     print("W16C2_WEIGHTED_SOURCE_REIMPORT_FIRST_FAILURE",
       name,f,i,k,err,source[i],observed[k],flush=True)
     raise ValueError("W16C2_WEIGHTED_NATIVE_INDEXED_XYZ_GATE")
   count+=len(mapping)
   moved=max(moved,max(math.dist(v,w) for v,w in zip(source,native[name]["0"])))
  motion_min=min(motion_min,moved)
 if count!=784 or motion_min<.02:raise ValueError("W16C2_STATIC_OR_COVERAGE_GATE")
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 truth={"schema":"scp.walk_w15_source_truth.v1","source_rights":SOURCE,
  "glb_sha256":sha(glb),"frames":list(FRAMES),
  "world_vertices":{str(f):{name:native[name][str(f)] for name in assets} for f in FRAMES}}
 (out/"native_source_vertex_truth.json").write_text(json.dumps(truth,indent=2,sort_keys=True)+"\n")
 receipt={"schema":"scp.walk_w16c2_native_dual_leg_3d.v1",
  "status":"PASS_ORIGINAL_TWO_ACTORS_TWO_LEGS_EACH_NATIVE_SKIN",
  "source_rights":SOURCE,"profile":opts.profile,"actors":2,
  "legs_per_actor":2,"bones_per_actor":4,"vertices_per_actor":56,
  "source_frames":list(FRAMES),"fps":FPS,"indexed_vertex_observations":count,
  "maximum_native_import_world_xyz_error":maximum,"native_ik_fk_max":fk_error,
  "minimum_real_deformation":motion_min,
  "native_mesh_basis":"BLENDER_WORLD_XYZ_Z_UP",
  "glb_basis":"GLTF_RH_Y_UP_SERIALIZED",
  "native_quaternion":"BLENDER_WXYZ","serialized_quaternion":"GLTF_XYZW",
  "time_origin":"ARTIFICIAL_12FPS_NOT_OBSERVED_HUMAN_GAIT",
  "foot_contact":"NOT_QUALIFIED_NO_HEEL_TOE_LANDMARKS",
  "source_motion":"ORIGINAL_PROCEDURAL_ALTERNATING_DUAL_LEG_IK_NOT_HUMAN_GAIT",
  "blend_sha256":sha(blend),"glb_sha256":sha(glb),"video_sha256":sha(video)}
 (out/"native_dual_leg_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W16C2_ORIGINAL_NATIVE_DUAL_LEG_PASS",json.dumps(receipt,sort_keys=True),flush=True)
if __name__=="__main__":main()
