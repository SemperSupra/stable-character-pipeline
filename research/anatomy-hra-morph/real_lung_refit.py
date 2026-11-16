"""R036 composed real HRA lung mesh + native MPFB morph/refit binding.

A research-only deterministic bone-relative geometric mapping; real source
organ meshes but no anatomical fitting, collision or physiology acceptance.
"""
import bpy
import argparse
import hashlib
import importlib
import json
import math
import os
import struct
import sys
from mathutils import Vector

def cli():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=["probe","verify"],required=True)
 p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

def fail(x):
 print("R036_HRA_REFIT_FAIL "+x)
 raise RuntimeError(x)

def native():
 body=bpy.data.objects.get("R036_Official_MPFB_Human")
 rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
 if not body or not rig or len(rig.data.bones)!=163:fail("missing native MPFB 163-bone rig")
 organs=sorted([o for o in bpy.context.scene.objects if o.name.startswith("R036_HRA_Lung_") and o.type=="MESH"],key=lambda o:o.name)
 if len(organs)!=67:fail("unexpected HRA lung reference submesh count")
 for o in organs:
  if o.get("source_sha256")!="e64351b72b0bc5289a4dc32ba2b402b9c974f9ec0b1972bf06b436864f917913":
   fail("HRA source provenance pin missing or changed")
  if not any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers):
   fail("HRA submesh not weighted to official MakeHuman rig")
 return body,rig,organs

def get_mpfb():
 import addon_utils
 package="bl_ext.user_default.mpfb"
 if not addon_utils.check(package)[1]:
  addon_utils.enable(package,default_set=False,persistent=False)
 if not addon_utils.check(package)[1]:fail("native MPFB extension unavailable")
 hs=importlib.import_module(package+".services.humanservice").HumanService
 ts=importlib.import_module(package+".services.targetservice").TargetService
 pp=importlib.import_module(package+".entities.objectproperties").HumanObjectProperties
 return hs,ts,pp

def pts(obj):
 bpy.context.view_layer.update()
 oo=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=oo.to_mesh()
 try:return [oo.matrix_world@v.co for v in mesh.vertices]
 finally:oo.to_mesh_clear()

def center(obj):
 p=pts(obj)
 return sum(p,Vector())/len(p)

def surface_digest(obj):
 h=hashlib.sha256()
 for p in pts(obj):h.update(struct.pack("<3f",*p))
 return h.hexdigest()

def raw_source_digest(objects):
 # Source topology may remain constant while transforms are deliberately refit.
 # Mesh local vertex coordinates and faces must stay unchanged.
 h=hashlib.sha256()
 for obj in objects:
  h.update(obj.name.encode())
  for v in obj.data.vertices:h.update(struct.pack("<3f",*v.co))
  for p in obj.data.polygons:
   h.update(struct.pack("<I",len(p.vertices)))
   for i in p.vertices:h.update(struct.pack("<I",i))
 return h.hexdigest()

def frame(rig):
 bone=rig.data.bones.get(rig.get("r036_test_bone"))
 if bone is None:fail("native binding bone missing")
 start=rig.matrix_world@bone.head_local
 tail=rig.matrix_world@bone.tail_local
 axis=tail-start
 length=axis.length
 if length<1e-6:fail("zero bone length")
 rot=Vector((0,0,1)).rotation_difference(axis.normalized())
 return start,rot,length

def capture_offsets(rig,organs):
 start,rot,length=frame(rig)
 return [rot.inverted()@(center(o)-start)/length for o in organs],length

def norm_delta(rig,organs,refs):
 observed,_=capture_offsets(rig,organs)
 deltas=[(observed[i]-refs[i]).length for i in range(len(refs))]
 return {"max_norm_offset_drift":max(deltas),"mean_norm_offset_drift":sum(deltas)/len(deltas),
    "above_0p01_bone_lengths":sum(d>.01 for d in deltas),"samples":len(deltas)}

def rebind(rig,organs,baseline_offsets,baseline_length):
 anchor,rot,new_length=frame(rig)
 for ob,offset in zip(organs,baseline_offsets):
  # Original donor mesh topology/vertices are immutable. Re-scale the entire
  # mesh uniformly and re-position its center in a bone-relative frame.
  factor=new_length/baseline_length
  ob.scale=(factor,factor,factor)
  bpy.context.view_layer.update()
  expected=anchor+rot@(offset*new_length)
  current=center(ob)
  ob.location+=rig.matrix_world.inverted().to_3x3()@(expected-current)
  bpy.context.view_layer.update()
  if (center(ob)-expected).length>1e-4:fail("rig-local donor organ rebinding did not converge")

def probe(out):
 body,rig,organs=native()
 hs,ts,pp=get_mpfb()
 bpy.context.scene.frame_set(1)
 baseline_offsets,baseline_length=capture_offsets(rig,organs)
 expected_source=raw_source_digest(organs)
 raw_baseline=len(body.data.vertices)
 results=[]
 configs=[("reference",None),("taller_lighter",{"height":.77,"weight":.25}),("shorter_heavier",{"height":.24,"weight":.76})]
 for label,macro in configs:
  if macro:
   for key,value in macro.items():pp.set_value(key,value,entity_reference=body)
   ts.reapply_macro_details(body)
   hs.refit(body)
  bpy.context.scene.frame_set(1)
  before=norm_delta(rig,organs,baseline_offsets)
  if macro:rebind(rig,organs,baseline_offsets,baseline_length)
  after=norm_delta(rig,organs,baseline_offsets)
  if len(body.data.vertices)!=raw_baseline:fail("MakeHuman source mesh topology changed")
  if expected_source!=raw_source_digest(organs):fail("HRA source organ mesh topology changed under morph")
  if after["max_norm_offset_drift"]>1e-4:fail("real donor mesh bone-local alignment not preserved")
  body_rest=surface_digest(body)
  organ_rest=surface_digest(organs[0])
  bpy.context.scene.frame_set(24)
  body_pose=surface_digest(body)
  organ_pose=surface_digest(organs[0])
  if body_pose==body_rest or organ_pose==organ_rest:fail("external and source donor lung animation disconnected")
  bpy.context.scene.frame_set(1)
  results.append({"name":label,"macro":macro,
   "body_raw_vertices":len(body.data.vertices),
   "body_evaluated_vertices":len(pts(body)),
   "bone_length_m":frame(rig)[2],"pre_rebind":before,"post_rebind":after,
   "body_moves_under_pose":body_pose!=body_rest,"donor_moves_under_pose":organ_pose!=organ_rest})
 bpy.context.scene.frame_set(1)
 os.makedirs(out,exist_ok=True)
 output=os.path.join(out,"mpfb-hra-lung-morphed.blend")
 bpy.ops.wm.save_as_mainfile(filepath=output,check_existing=False)
 h=hashlib.sha256()
 with open(output,"rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 receipt={"schema":"scp.anatomy.real_donor_mpfb_macro_fit.v1","status":"PASS_NARROW_NATIVE_67_ORGAN_MESH_REBIND",
    "source":"HRA Lung Male v1.2; CC BY 4.0; source SHA256 e64351b72b0bc5289a4dc32ba2b402b9c974f9ec0b1972bf06b436864f917913",
    "source_submeshes":len(organs),"original_source_geometry_unchanged":True,
    "organ_vertices":sum(len(o.data.vertices) for o in organs),"source_topology_digest":expected_source,
    "macro_profiles":results,"saved_scene_sha256":h.hexdigest(),
    "medical_registration":"NOT_QUALIFIED","collisions":"NOT_RUN",
    "tissue_physics":"NOT_RUN","photorealism":"NOT_INSPECTED"}
 with open(os.path.join(out,"hra-morph-receipt.json"),"w") as f:json.dump(receipt,f,indent=2,sort_keys=True)
 print("R036_HRA_MORPH_RECEIPT "+json.dumps(receipt,sort_keys=True,separators=(",",":")))

def verify(out):
 body,rig,organs=native()
 if len(body.data.vertices)!=19158:fail("unexpected MakeHuman raw body topology on saved scene")
 path=os.path.join(out,"hra-morph-receipt.json")
 if not os.path.isfile(path):fail("source receipt not persisted in ephemeral workcell")
 with open(path) as f:receipt=json.load(f)
 if raw_source_digest(organs)!=receipt["source_topology_digest"]:
  fail("saved real donor lung mesh source topology has drifted")
 bpy.context.scene.frame_set(1)
 start=surface_digest(organs[0])
 bpy.context.scene.frame_set(24)
 end=surface_digest(organs[0])
 if start==end:fail("reopened donor lung no longer animated")
 print("R036_HRA_MORPH_VERIFY "+json.dumps({"status":"PASS_NARROW_SOURCE_ORGAN_MORPH_REOPEN",
  "real_donor_submeshes":len(organs),"bone_count":len(rig.data.bones),
  "exact_source_mesh_topology_preserved":True,
  "medical_registration":"NOT_QUALIFIED","external_engine_import":"NOT_RUN"},sort_keys=True))

if __name__=="__main__":
 n=cli()
 if n.stage=="probe":probe(n.out)
 else:verify(n.out)
