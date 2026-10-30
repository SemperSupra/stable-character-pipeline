"""W16-C5A original C4 foot source -> ACTUAL weighted Blender skinned 6-bone rig.

One-frame source-to-native proof. NOT a walking-video/full-body/person acceptance.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector,Quaternion
SOURCE="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
ACTORS=(("CobaltOriginal",-1.65),("MarigoldOriginal",1.65))
LEGS=(("Left",-1),("Right",1))
LENGTH=.6
def add_actor(name,x):
 data=bpy.data.armatures.new(name+"_SourceFootArmature")
 arm=bpy.data.objects.new(name+"_Skeleton",data)
 bpy.context.scene.collection.objects.link(arm)
 arm.location=(x,0,0)
 bpy.context.view_layer.objects.active=arm
 arm.select_set(True)
 bpy.ops.object.mode_set(mode="EDIT")
 for leg,sign in LEGS:
  cx=sign*.22
  up=data.edit_bones.new(leg+"Upper")
  up.head=(cx,0,1.08);up.tail=(cx,0,.48)
  low=data.edit_bones.new(leg+"Lower")
  low.head=(cx,0,.48);low.tail=(cx,0,-.12)
  low.parent=up;low.use_connect=True
  foot=data.edit_bones.new(leg+"Foot")
  foot.head=(cx,0,-.12);foot.tail=(cx,.18,-.12)
  foot.parent=low;foot.use_connect=True
 bpy.ops.object.mode_set(mode="OBJECT")
 for bone in arm.pose.bones:bone.rotation_mode="QUATERNION"
 verts=[];faces=[];groups={};foot_landmarks={}
 for leg,sign in LEGS:
  cx=sign*.22
  for part,z0,z1 in (("Upper",1.08,.48),("Lower",.48,-.12)):
   off=len(verts);groups[leg+part]=[]
   for z in (z0,z1):
    verts.extend(((cx-.08,-.07,z),(cx+.08,-.07,z),
                  (cx+.08,.07,z),(cx-.08,.07,z)))
   groups[leg+part].extend(range(off,off+8))
   for j in range(4):
    a=off+j;b=off+(j+1)%4;c=off+4+j;d=off+4+(j+1)%4
    faces.extend(((a,b,c),(b,d,c)))
  off=len(verts);groups[leg+"Foot"]=list(range(off,off+8))
  for z in (-.12,-.08):
   for y in (-.12,.12):
    verts.extend(((cx-.07,y,z),(cx+.07,y,z)))
  faces.extend(((off,off+2,off+1),(off+1,off+2,off+3),
    (off+4,off+5,off+6),(off+5,off+7,off+6)))
  for a,b,c,d in ((0,1,4,5),(2,3,6,7),(0,2,4,6),(1,3,5,7)):
   faces.extend(((off+a,off+b,off+c),(off+b,off+d,off+c)))
  foot_landmarks[leg]={"heel":(off,off+1),"toe":(off+2,off+3),
                        "all_sole":(off,off+1,off+2,off+3)}
 mesh=bpy.data.meshes.new(name+"_FootMesh")
 mesh.from_pydata(verts,[],faces);mesh.update()
 obj=bpy.data.objects.new(name+"_SkinnedMesh",mesh)
 bpy.context.scene.collection.objects.link(obj);obj.parent=arm
 for bone,indices in groups.items():
  group=obj.vertex_groups.new(name=bone);group.add(indices,1.,"REPLACE")
 m=obj.modifiers.new("OriginalWeighted6BoneSkin","ARMATURE");m.object=arm
 arm["source_rights"]=SOURCE;obj["source_rights"]=SOURCE
 return arm,obj,foot_landmarks

def apply_frame(actor,arm,obj,landmarks,profile):
 if actor["id"]!=arm.name.replace("_Skeleton","") or len(actor["frames"])!=24:
  raise ValueError("C5A_ACTOR_SOURCE_ID")
 f=actor["frames"][0]
 if f["index"]!=0 or f["time_den"]!=12 or len(f["legs"])!=2:
  raise ValueError("C5A_SOURCE_CLOCK")
 data=arm.data
 direction=1 if profile=="forward" else -1
 desired_foot=Quaternion((0,0,1),math.pi) if direction<0 else Quaternion((1,0,0,0))
 errors=[]
 bpy.context.scene.frame_set(0)
 arm.location.y=f["root_y"]
 for li,(leg,sign) in enumerate(LEGS):
  s=f["legs"][li]
  if s["id"]!=leg or s["source_rights"]!=SOURCE:
   raise ValueError("C5A_LEG_RIGHTS")
  up=arm.pose.bones[leg+"Upper"]
  low=arm.pose.bones[leg+"Lower"]
  foot=arm.pose.bones[leg+"Foot"]
  hip,knee,ankle=map(Vector,(s["hip"],s["knee"],s["ankle"]))
  base=Vector((0,0,-1))
  wu=base.rotation_difference((knee-hip).normalized())
  wl=base.rotation_difference((ankle-knee).normalized())
  ru=data.bones[leg+"Upper"].matrix_local.to_quaternion()
  rl=data.bones[leg+"Lower"].matrix_local.to_quaternion()
  rf=data.bones[leg+"Foot"].matrix_local.to_quaternion()
  up.rotation_quaternion=ru.inverted()@wu@ru
  low.rotation_quaternion=rl.inverted()@wu.inverted()@wl@rl
  foot.rotation_quaternion=rf.inverted()@wl.inverted()@desired_foot@rf
  for bone in (up,low,foot):
   bone.keyframe_insert(data_path="rotation_quaternion",frame=0)
 arm.keyframe_insert(data_path="location",frame=0)
 bpy.context.view_layer.update()
 deps=bpy.context.evaluated_depsgraph_get()
 evaluated=obj.evaluated_get(deps)
 me=evaluated.to_mesh()
 try:
  world=[tuple(float(c) for c in obj.matrix_world@v.co) for v in me.vertices]
 finally:evaluated.to_mesh_clear()
 if len(world)!=48:
  raise ValueError("C5A_SKIN_VERTEX_COUNT")
 results=[]
 for li,(leg,sign) in enumerate(LEGS):
  s=f["legs"][li]
  up,low,foot=[arm.pose.bones[leg+part] for part in ("Upper","Lower","Foot")]
  expect=[Vector(s[k]) for k in ("knee","ankle")]
  actual=[arm.matrix_world@up.tail,arm.matrix_world@low.tail]
  errors.extend((actual[i]-expect[i]).length for i in range(2))
  sample={}
  for k in ("heel","toe"):
   ij=landmarks[leg][k]
   p=Vector(tuple((world[ij[0]][j]+world[ij[1]][j])*.5 for j in range(3)))
   sample[k]=list(p);errors.append((p-Vector(s[k])).length)
  ground=min(world[i][2] for i in landmarks[leg]["all_sole"])
  if ground<-.0001:
   raise ValueError("C5A_WEIGHTED_NATIVE_GROUND_PENETRATION")
  if s["state"]=="stance" and abs(ground)>1e-3:
   raise ValueError("C5A_NATIVE_STANCE_FLOAT")
  if s["state"]=="swing" and ground<.02:
   raise ValueError("C5A_NATIVE_SWING_CLEARANCE")
  results.append({"leg":leg,"state":s["state"],"observed":sample,
   "source":{k:s[k] for k in ("heel","toe","ankle","knee")},
   "native_swept_sole_min_height":ground,"source_rights":SOURCE})
 if max(errors)>1e-3:
  print("C5A_FIRST_NATIVE_SOURCE_FAILURE",json.dumps({"actor":actor["id"],"max":max(errors),"legs":results}),flush=True)
  raise ValueError("C5A_NATIVE_SOURCE_FK_OR_FOOT_LANDMARK")
 return max(errors),results

def main():
 p=argparse.ArgumentParser();p.add_argument("--profile",choices=("forward","outward"),required=True)
 p.add_argument("--source",required=True);p.add_argument("--out",required=True)
 a=p.parse_args();raw=Path(a.source).read_bytes();source=json.loads(raw)
 if source.get("schema")!="scp.walk_c4_original_ground_feasibility.v1" or source.get("rights")!=SOURCE or source.get("profile")!=a.profile or source.get("rest_hip_height")!=1.08:
  raise ValueError("C5A_SOURCE_RIGHTS_OR_REST")
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene;scene.frame_start=0;scene.frame_end=0;scene.render.fps=12
 proof=[];maximum=0.
 for i,(name,x) in enumerate(ACTORS):
  if source["actors"][i]["id"]!=name:raise ValueError("C5A_ACTOR_SET")
  arm,obj,marks=add_actor(name,x)
  err,legs=apply_frame(source["actors"][i],arm,obj,marks,a.profile)
  maximum=max(maximum,err);proof.append({"actor":name,"bones":len(arm.pose.bones),"vertices":len(obj.data.vertices),"legs":legs})
 blend=out/"source_first_frame_six_bone_foot.blend"
 bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
 glb=out/"source_first_frame_six_bone_foot.glb"
 bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",export_animations=True)
 if blend.stat().st_size<10000 or glb.stat().st_size<1000:
  raise ValueError("C5A_NATIVE_FILE")
 r={"schema":"scp.walk_c5a_actual_weighted_firstframe.v1",
  "status":"PASS_ORIGINAL_NATIVE_SKINNED_HEEL_TOE_FIRST_FRAME_ONLY","profile":a.profile,
  "source_rights":SOURCE,"source_sha256":hashlib.sha256(raw).hexdigest(),
  "max_native_joint_landmark_error":maximum,
  "actors":proof,"native_blend_sha256":hashlib.sha256(blend.read_bytes()).hexdigest(),
  "native_glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
  "scope":"ONE_FRAME_NO_24_FRAME_SKIN_COVERAGE_NO_FULL_BODY_NO_L1_IMAGE_ACCEPTANCE"}
 (out/"native_firstframe_receipt.json").write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W16C5A_NATIVE_WEIGHTED_SOLE_FIRSTFRAME_PASS",a.profile,maximum)
if __name__=="__main__":main()
