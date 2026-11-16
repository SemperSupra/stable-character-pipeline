"""R036 MPFB official HumanService create_human/add_builtin_rig integration smoke.
Source is fetched at immutable commit in a public ephemeral Actions runner.
Anatomical ellipsoids are synthetic demonstration proxies, NOT true organs.
"""
import argparse
import hashlib
import importlib
import json
import math
import os
import struct
import sys
import bpy
from mathutils import Vector

def parse():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=["build","verify"],required=True)
 p.add_argument("--source",default="")
 p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

def fail(s): print("R036_NATIVE_MPF_FAILURE "+s);raise RuntimeError(s)
def checksum(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def positions(obj):
 bpy.context.view_layer.update()
 deps=bpy.context.evaluated_depsgraph_get()
 ob=obj.evaluated_get(deps)
 m=ob.to_mesh()
 try:
  h=hashlib.sha256()
  for v in m.vertices: h.update(struct.pack("<3f",*(ob.matrix_world@v.co)))
  return h.hexdigest(),len(m.vertices)
 finally:ob.to_mesh_clear()
def mat(name,rgb):
 m=bpy.data.materials.new(name)
 m.diffuse_color=(*rgb,1)
 return m

def build(n):
 if not os.path.isdir(os.path.join(n.source,"src","mpfb","data")):fail("missing pinned upstream MPFB source")
 # Blender 4.2+ extensions must be loaded as bl_ext.<repo>.<package>, not
 # a plain sys.path import; LocationService uses extension_path_user(__package__).
 import addon_utils
 module_name="bl_ext.user_default.mpfb"
 if not addon_utils.check(module_name)[1]:
  addon_utils.enable(module_name,default_set=False,persistent=False)
 if not addon_utils.check(module_name)[1]:fail("MPFB extension not enabled via Blender official extension repository")
 humanmod=importlib.import_module(module_name+".services.humanservice")
 hs=humanmod.HumanService
 bpy.ops.object.select_all(action="SELECT")
 bpy.ops.object.delete(use_global=False)
 body=hs.create_human()
 if body is None or body.type!="MESH":fail("HumanService.create_human returned no usable body")
 rig=hs.add_builtin_rig(body,"default",import_weights=True)
 if rig is None or rig.type!="ARMATURE":fail("HumanService.add_builtin_rig did not construct armature")
 if len(rig.data.bones)<15:fail("MPFB official rig unexpectedly small")
 has_skin=any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers)
 if not has_skin:fail("native body missing MPFB armature deformation")
 # glTF skinning typically exposes at most 4 vertex influences. Measure original
 # MPFB rig weight tails explicitly; exporter may truncate those influences.
 bone_names=set(b.name for b in rig.data.bones)
 group_names={i:g.name for i,g in enumerate(body.vertex_groups)}
 more_than_four=0
 max_influences=0
 max_tail_fraction=0.0
 total_tail_mass=0.0
 for v in body.data.vertices:
  weights=sorted((vg.weight for vg in v.groups if group_names.get(vg.group) in bone_names and vg.weight>0),reverse=True)
  max_influences=max(max_influences,len(weights))
  if len(weights)>4:
   more_than_four+=1
   total=sum(weights)
   tail=sum(weights[4:])
   total_tail_mass+=tail
   if total>0:max_tail_fraction=max(max_tail_fraction,tail/total)
 skin_fidelity={"source_vertices_more_than_four_joint_weights":more_than_four,"source_max_joint_influences":max_influences,
  "max_discarded_weight_fraction":max_tail_fraction,"sum_discarded_weight_mass":total_tail_mass,
  "gltf_4_weight_limit":"HOLD" if more_than_four>0 else "UNVERIFIED",
  "note":"counts are source skin weights, not independently imported/exported weight delta"}
 body.name="R036_Official_MPFB_Human"
 rig.name="R036_Official_MPFB_Rig"
 possible=[b for b in rig.data.bones if b.use_deform and ("spine" in b.name.lower() or "chest" in b.name.lower() or "torso" in b.name.lower())]
 if not possible:fail("no official torso bone found; inspect pinned rig rather than guessing")
 target=sorted(possible,key=lambda x:x.name)[0]
 bone=rig.pose.bones[target.name]
 rig["r036_test_bone"]=target.name
 bounds=[body.matrix_world@Vector(v.co) for v in body.data.vertices]
 height=max(v.z for v in bounds)-min(v.z for v in bounds)
 if height<0.5 or height>4:fail("unsupported physical scale/units in MPFB base")
 origin=rig.matrix_world@target.head_local
 # Two purpose-built proxy anatomy structures, skinned to an actual MPFB bone.
 organs=[]
 for index,side in enumerate((-.09,.09)):
  bpy.ops.mesh.primitive_uv_sphere_add(segments=14,ring_count=8,location=origin+Vector((height*side,0,height*.03)))
  ob=bpy.context.object
  ob.name=("R036_AnatomyProxy_Left","R036_AnatomyProxy_Right")[index]
  ob.scale=(height*.06,height*.035,height*.1)
  bpy.context.view_layer.objects.active=ob
  bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
  ob.data.materials.append(mat(ob.name+"_material",(.72,.28,.31)))
  g=ob.vertex_groups.new(name=target.name)
  g.add(list(range(len(ob.data.vertices))),1,"REPLACE")
  ob.parent=rig
  arm=ob.modifiers.new("R036_ArmatureLink","ARMATURE")
  arm.object=rig
  ob["anatomy_class"]="UNVALIDATED_SYNTHETIC_PROXY"
  organs.append(ob)
 bone.rotation_mode="XYZ"
 for frame,angle in ((1,0.0),(12,.13),(24,.22)):
  bone.rotation_euler=(angle,0,0)
  bone.keyframe_insert(data_path="rotation_euler",frame=frame)
 scene=bpy.context.scene
 scene.frame_start=1
 scene.frame_end=24
 scene.frame_set(1)
 rest_body,num=positions(body)
 rest_organ,_=positions(organs[0])
 scene.frame_set(24)
 posed_body,num2=positions(body)
 posed_organ,_=positions(organs[0])
 if rest_body==posed_body or rest_organ==posed_organ or num!=num2:fail("official MPFB skin/organ did not deform")
 before,_=positions(body)
 for o in organs:o.hide_render=True
 after,_=positions(body)
 if before!=after:fail("visibility mutated external physical surface")
 scene.render.engine="CYCLES"
 scene.cycles.device="CPU"
 scene.cycles.samples=8
 scene.render.resolution_x=256
 scene.render.resolution_y=256
 scene.render.resolution_percentage=100
 scene.render.image_settings.file_format="PNG"
 cx=sum(v.x for v in bounds)/len(bounds)
 cy=sum(v.y for v in bounds)/len(bounds)
 zmin=min(v.z for v in bounds)
 bpy.ops.object.camera_add(location=(cx+1.3*height,cy-2.2*height,zmin+.65*height))
 cam=bpy.context.object
 cam.rotation_euler=(Vector((cx,cy,zmin+.55*height))-cam.location).to_track_quat("-Z","Y").to_euler()
 scene.camera=cam
 bpy.ops.object.light_add(type="AREA",location=(cx+.9*height,cy-1.1*height,zmin+1.1*height))
 bpy.context.object.data.energy=1100
 bpy.context.object.data.size=height
 os.makedirs(n.out,exist_ok=True)
 scene.render.filepath=os.path.join(n.out,"mpfb_native_surface.png")
 bpy.ops.render.render(write_still=True)
 body.hide_render=True
 for o in organs:o.hide_render=False
 scene.render.filepath=os.path.join(n.out,"mpfb_native_anatomy.png")
 bpy.ops.render.render(write_still=True)
 body.hide_render=False
 for o in organs:o.hide_render=True
 blend=os.path.join(n.out,"mpfb-official-anatomy.blend")
 bpy.ops.wm.save_as_mainfile(filepath=blend,check_existing=False)
 for o in bpy.context.selected_objects:o.select_set(False)
 for o in [rig,body]+organs:o.select_set(True)
 bpy.context.view_layer.objects.active=rig
 glb=os.path.join(n.out,"mpfb-official-anatomy.glb")
 bpy.ops.export_scene.gltf(filepath=glb,export_format="GLB",use_selection=True,export_all_influences=False)
 if not os.path.exists(glb):fail("official MPFB four-influence GLB missing")
 allweights_glb=os.path.join(n.out,"mpfb-official-anatomy-allweights.glb")
 bpy.ops.export_scene.gltf(filepath=allweights_glb,export_format="GLB",use_selection=True,export_all_influences=True)
 if not os.path.exists(allweights_glb):fail("official MPFB all-influences GLB missing")
 r={"status":"PASS_OFFICIAL_MPFB_NATIVE_SMOKE","blender":bpy.app.version_string,
   "real_mpfb_rig_bones":len(rig.data.bones),"selected_torso_bone":target.name,
   "body_vertices":num,"skin_rest_sha":rest_body,"skin_pose_sha":posed_body,
   "organ_rest_sha":rest_organ,"organ_pose_sha":posed_organ,
   "visibility_render_only":before==after,"source_skin_influence_audit":skin_fidelity,"blend_sha256":checksum(blend),
   "glb_sha256":checksum(glb),"allweights_glb_sha256":checksum(allweights_glb),
   "allweights_export":"STRUCTURAL_EXPERIMENT_NOT_ENGINE_COMPATIBLE","source":"makehumancommunity/mpfb2 pinned Git commit",
   "limits":"generic MPFB official rig; unregistered synthetic proxy organs; no soft tissue physics, photorealism or human anatomy accepted"}
 with open(os.path.join(n.out,"receipt.json"),"w") as f:json.dump(r,f,sort_keys=True,indent=2)
 print("R036_NATIVE_MPFB_RECEIPT "+json.dumps(r,sort_keys=True))

def verify(n):
 body=bpy.data.objects.get("R036_Official_MPFB_Human")
 rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
 organs=[bpy.data.objects.get("R036_AnatomyProxy_Left"),bpy.data.objects.get("R036_AnatomyProxy_Right")]
 if not body or not rig or any(o is None for o in organs):fail("reload lost core body or anatomy")
 if not any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers):fail("reload lost native rig binding")
 for o in organs:
  if not any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers):fail("reload lost organ binding")
 sc=bpy.context.scene
 sc.frame_set(1)
 a,_=positions(body);x,_=positions(organs[0])
 sc.frame_set(24)
 b,_=positions(body);y,_=positions(organs[0])
 if a==b or x==y:fail("saved scene did not preserve animation")
 path=os.path.join(n.out,"mpfb-official-anatomy.glb")
 with open(path,"rb") as f:
  header=f.read(12)
  if header[:4]!=b"glTF":fail("invalid GLB")
  length,kind=struct.unpack("<II",f.read(8))
  if kind!=0x4e4f534a:fail("missing GLB JSON")
  manifest=json.loads(f.read(length))
 if not manifest.get("skins") or len(manifest.get("meshes",[]))<3:fail("lost skin or anatomy meshes in GLB")
 allpath=os.path.join(n.out,"mpfb-official-anatomy-allweights.glb")
 with open(allpath,"rb") as f:
  header=f.read(12)
  if header[:4]!=b"glTF":fail("invalid all-influences GLB")
  length,kind=struct.unpack("<II",f.read(8))
  if kind!=0x4e4f534a:fail("all-influences GLB JSON missing")
  full=json.loads(f.read(length))
 additional_weight_sets=sum(1 for mesh in full.get("meshes",[]) for primitive in mesh.get("primitives",[]) if "WEIGHTS_1" in primitive.get("attributes",{}))
 if additional_weight_sets==0:fail("all-influences glTF did not preserve any WEIGHTS_1 set")
 print("R036_NATIVE_MPFB_VERIFY "+json.dumps({"status":"PASS_REOPEN_INTERCHANGE_NARROW","gltf_skins":len(manifest["skins"]),"gltf_meshes":len(manifest["meshes"]),
    "allweights_additional_primitives":additional_weight_sets,"allweights_glb_sha256":checksum(allpath),
    "allweights_engine_compatibility":"UNVERIFIED","fourweight_positional_fidelity":"HOLD",
    "bone_count":len(rig.data.bones),"animation_survived":True},sort_keys=True))

if __name__=="__main__":
 n=parse()
 if n.stage=="build":build(n)
 else:verify(n)
