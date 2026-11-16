"""R036: source-credited HRA lung GLB -> native MPFB armature diagnostic.

Real *reference organ geometry*, but provisional normalized fit, not medical
registration, correct size, tissue dynamics or validated anatomy placement.
"""
import bpy
import argparse
import hashlib
import json
import math
import os
import re
import struct
import sys
from mathutils import Vector

def cli():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=["build","verify"],required=True)
 p.add_argument("--organ",default="")
 p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])

def fail(x):
 print("R036_HRA_LUNG_FAIL "+x)
 raise RuntimeError(x)

def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
 return h.hexdigest()

def points(obj):
 bpy.context.view_layer.update()
 ob=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=ob.to_mesh()
 try:return [ob.matrix_world@v.co for v in mesh.vertices]
 finally:ob.to_mesh_clear()

def pose_digest(obj):
 h=hashlib.sha256()
 for p in points(obj):h.update(struct.pack("<3f",*p))
 return h.hexdigest()

def geometry_bounds(source_meshes):
 data=[p for ob in source_meshes for p in [ob.matrix_world@v.co for v in ob.data.vertices]]
 if not data:fail("empty source-licensed organ GLB")
 low=Vector((min(v[i] for v in data) for i in range(3)))
 high=Vector((max(v[i] for v in data) for i in range(3)))
 dim=high-low
 if min(dim)<=0 or max(dim)>1e6 or not all(math.isfinite(x) for v in data[:2000] for x in v):
  fail("source lung bounds invalid")
 return low,high,len(data)

def scene_objects():
 body=bpy.data.objects.get("R036_Official_MPFB_Human")
 rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
 if not body or not rig:fail("official MPFB native character absent")
 if rig.type!="ARMATURE" or len(rig.data.bones)<100:fail("official rig absent or invalid")
 if not any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers):
  fail("official body skinning lost")
 return body,rig

def build(n):
 body,rig=scene_objects()
 if not n.organ or not os.path.isfile(n.organ):fail("missing authorized public HRA lung source GLB")
 if os.path.getsize(n.organ)>20*1024*1024:fail("unbounded external lung asset")
 with open(n.organ,"rb") as f:
  if f.read(4)!=b"glTF":fail("organ reference not GLB")
 prior=set(bpy.context.scene.objects)
 bpy.ops.import_scene.gltf(filepath=n.organ)
 new=[o for o in bpy.context.scene.objects if o not in prior]
 source=[o for o in new if o.type=="MESH" and len(o.data.vertices)>0]
 if not source:fail("HRA organ did not import actual mesh")
 if len(source)>200:fail("source model has unexpectedly many mesh objects")
 low,high,nverts=geometry_bounds(source)
 if nverts>250000:fail("over-size anatomy source vertices in public CPU lane")
 center=(low+high)*.5
 longest=max(high[i]-low[i] for i in range(3))
 # 0.3m target length is a **provisional artist preview normalization**,
 # not inferred organ dimensions or a validated individual registration.
 factor=.30/longest
 bone=rig.data.bones.get(rig.get("r036_test_bone"))
 if not bone:fail("missing official spine01 anatomy diagnostic anchor")
 head=rig.matrix_world@bone.head_local
 tail=rig.matrix_world@bone.tail_local
 axis=(tail-head).normalized()
 target=head+axis*.12
 restored=[]
 for i,origin in enumerate(source):
  coords=[(origin.matrix_world@v.co-center)*factor+target for v in origin.data.vertices]
  faces=[list(poly.vertices) for poly in origin.data.polygons]
  if not coords or not faces:continue
  mesh=bpy.data.meshes.new("HRA_ReferenceLung_Mesh_"+str(i))
  mesh.from_pydata(coords,[],faces)
  mesh.update()
  ob=bpy.data.objects.new("R036_HRA_Lung_"+str(i),mesh)
  bpy.context.collection.objects.link(ob)
  # Attach the imported mesh to the actual MPFB spine01 control bone.
  # A constant weight is a basic rigid follow proxy, not tissue mechanics.
  group=ob.vertex_groups.new(name=bone.name)
  group.add(list(range(len(mesh.vertices))),1.0,"REPLACE")
  ob.parent=rig
  mod=ob.modifiers.new("R036_AnatomyBoneBinding","ARMATURE")
  mod.object=rig
  ob["provenance_url"]="https://cdn.humanatlas.io/hra-releases/v1.2/models/VH_M_Lung.glb"
  ob["provenance_license"]="CC BY 4.0 (HuBMAP CCF Reference Object Library v1.2)"
  ob["anatomical_label"]="Lung, male v1.2, HBM787.FWXN.723"
  ob["source_sha256"]=sha(n.organ)
  ob["binding_validity"]="ARTIST_PROVISIONAL_UNQUALIFIED"
  ob["system"]="respiratory"
  restored.append(ob)
 # Remove donor import intermediates and only retain original documented geometry
 # as source-provenance-tagged derived meshes, not a second duplicate hierarchy.
 for ob in new:bpy.data.objects.remove(ob,do_unlink=True)
 if not restored:fail("source glTF had no accepted polygon surfaces")
 scene=bpy.context.scene
 scene.frame_set(1)
 rest=[pose_digest(ob) for ob in restored]
 ext_rest=pose_digest(body)
 scene.frame_set(24)
 posed=[pose_digest(ob) for ob in restored]
 if all(a==b for a,b in zip(rest,posed)):fail("actual donor meshes did not follow MPFB rig")
 ext_posed=pose_digest(body)
 if ext_rest==ext_posed:fail("external skin did not deform")
 before=pose_digest(body)
 for ob in restored:ob.hide_render=not ob.hide_render
 after=pose_digest(body)
 if before!=after:fail("organ visibility affected native skin deformation")
 for ob in restored:ob.hide_render=False
 body.hide_render=True
 scene.render.filepath=os.path.join(n.out,"hra_lung_provisional_cutaway.png")
 bpy.ops.render.render(write_still=True)
 body.hide_render=False
 for ob in restored:ob.hide_render=True
 scene.render.filepath=os.path.join(n.out,"hra_lung_external.png")
 bpy.ops.render.render(write_still=True)
 blend=os.path.join(n.out,"mpfb-with-hra-lung-provisional.blend")
 bpy.ops.wm.save_as_mainfile(filepath=blend,check_existing=False)
 result={"schema":"scp.anatomy.hra_lung_native_v1","status":"PASS_SOURCE_ORGAN_MESH_IMPORT_AND_DIAGNOSTIC_BONE_BINDING",
  "source_sha256":sha(n.organ),"source_file_bytes":os.path.getsize(n.organ),
  "source_url":"https://cdn.humanatlas.io/hra-releases/v1.2/models/VH_M_Lung.glb",
  "source_attribution":"Kristen Browne; Heidi Schlehlein. HuBMAP CCF 3D Reference Organ for Lung, Male v1.2. CC BY 4.0",
  "source_mesh_count":len(source),"source_vertices":nverts,
  "source_max_extent_in_glb_units":longest,
  "provisional_scene_scale":factor,"provisional_target_length_m":.3,
  "attached_named_submeshes":len(restored),"attached_source_vertices":sum(len(o.data.vertices) for o in restored),
  "bone":bone.name,"source_skin_pose_changed":ext_rest!=ext_posed,
  "source_lung_pose_changed":any(a!=b for a,b in zip(rest,posed)),
  "render_visibility_preserved_skin":before==after,
  "native_blend_sha256":sha(blend),
  "anatomical_registration":"NOT_QUALIFIED","physical_tissue_simulation":"NOT_RUN",
  "external_visual_quality":"NOT_INSPECTED","source_physics_alignment":"NOT_QUALIFIED"}
 with open(os.path.join(n.out,"hra-lung-receipt.json"),"w") as f:json.dump(result,f,sort_keys=True,indent=2)
 print("R036_HRA_LUNG_RECEIPT "+json.dumps(result,sort_keys=True,separators=(",",":")))

def verify(n):
 body,rig=scene_objects()
 parts=[o for o in bpy.context.scene.objects if o.name.startswith("R036_HRA_Lung_") and o.type=="MESH"]
 if not parts:fail("saved scene lost HRA source geometry")
 for ob in parts:
  if ob.get("system")!="respiratory" or ob.get("binding_validity")!="ARTIST_PROVISIONAL_UNQUALIFIED":
   fail("source license / representation state lost on save")
  if not any(m.type=="ARMATURE" and m.object==rig for m in ob.modifiers):
   fail("saved donor organ lost native MPFB rig attachment")
 bpy.context.scene.frame_set(1)
 a=[pose_digest(o) for o in parts]
 bpy.context.scene.frame_set(24)
 b=[pose_digest(o) for o in parts]
 if a==b:fail("saved organ geometry not animated")
 print("R036_HRA_LUNG_VERIFY "+json.dumps({"status":"PASS_SAVE_REOPEN_REAL_SOURCE_MESH_NARROW",
  "submeshes":len(parts),"bone_count":len(rig.data.bones),
  "actual_medical_registration":"HOLD","anatomical_physics":"NOT_RUN"},sort_keys=True))

if __name__=="__main__":
 n=cli()
 if n.stage=="build":build(n)
 else:verify(n)
