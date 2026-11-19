"""Original synthetic Blender 4.5/5.2/5.3 rig, morph, save/reopen, GLB qualification.
No protected source, real-person likeness or performance comparisons are admitted.
"""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
import bpy
from mathutils import Vector
SCHEMA="scp.blender.cross-version-native.v1"
def fail(code):raise RuntimeError(code)
def sha(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
 return h.hexdigest()
def obj_mesh():
 o=bpy.data.objects.get("SCP_OriginalSyntheticStrip")
 if o is None or o.type!="MESH":fail("NATIVE_SKINNED_MESH_MISSING")
 return o
def validate_scene():
 sc=bpy.context.scene
 if sc.get("source_fixture")!="SCP_ORIGINAL_SYNTHETIC_RIG_V1":fail("BAD_SOURCE_FIXTURE")
 if (sc.frame_start,sc.frame_end,sc.render.fps)!=(0,24,12):fail("BAD_FRAME_CLOCK")
 rig=bpy.data.objects.get("SCP_OriginalSyntheticRig")
 obj=obj_mesh()
 if rig is None or rig.type!="ARMATURE":fail("NATIVE_ARMATURE_MISSING")
 if len(rig.data.bones)!=2 or rig.data.bones["Upper"].parent!=rig.data.bones["Root"]:fail("BAD_BONE_HIERARCHY")
 if not any(mod.type=="ARMATURE" and mod.object==rig for mod in obj.modifiers):fail("SKIN_MODIFIER_JOIN")
 if len(obj.data.vertices)!=6 or len(obj.data.polygons)!=2:fail("MESH_TOPOLOGY_CHANGED")
 if len(obj.data.uv_layers)<1:fail("UV_LAYER_MISSING")
 if not obj.data.shape_keys or "Tissue" not in obj.data.shape_keys.key_blocks:fail("SHAPE_KEY_LOST")
 if not rig.animation_data or not rig.animation_data.action:fail("RIG_ACTION_MISSING")
 if not obj.data.shape_keys.animation_data or not obj.data.shape_keys.animation_data.action:fail("MORPH_ACTION_MISSING")
 return rig,obj
def sample():
 rig,obj=validate_scene()
 out=[]
 for frame in (0,12,24):
  bpy.context.scene.frame_set(frame)
  dg=bpy.context.evaluated_depsgraph_get()
  evaluated=obj.evaluated_get(dg)
  em=evaluated.to_mesh()
  try:
   coords=[tuple(float(y) for y in (evaluated.matrix_world @ v.co)) for v in em.vertices]
   if len(coords)!=6 or not all(math.isfinite(a) for xyz in coords for a in xyz):fail("EVALUATED_SKIN_INVALID")
   out.append({"frame":frame,"evaluated_world_xyz":coords,
      "shape_value":float(obj.data.shape_keys.key_blocks["Tissue"].value),
      "upper_rotation_y":float(rig.pose.bones["Upper"].rotation_euler.y)})
  finally:evaluated.to_mesh_clear()
 if max(math.dist(a["evaluated_world_xyz"][5],b["evaluated_world_xyz"][5]) for a,b in zip(out,out[1:]))<.01:
  fail("NO_REAL_ANIMATED_SKINNING")
 return out
def make():
 bpy.ops.wm.read_factory_settings(use_empty=True)
 scene=bpy.context.scene
 scene.frame_start=0;scene.frame_end=24;scene.render.fps=12
 scene["source_fixture"]="SCP_ORIGINAL_SYNTHETIC_RIG_V1"
 verts=[(-.25,0,0),(.25,0,0),(-.25,0,.5),(.25,0,.5),(-.25,0,1),(.25,0,1)]
 mesh=bpy.data.meshes.new("SCP_OriginalGrid");mesh.from_pydata(verts,[],[(0,1,3,2),(2,3,5,4)]);mesh.update()
 uv=mesh.uv_layers.new(name="UVMap")
 for poly in mesh.polygons:
  for loop in poly.loop_indices:
   vert=verts[mesh.loops[loop].vertex_index]
   uv.data[loop].uv=((vert[0]+.25)*2,vert[2])
 obj=bpy.data.objects.new("SCP_OriginalSyntheticStrip",mesh);scene.collection.objects.link(obj)
 rig_data=bpy.data.armatures.new("SCP_2BoneSourceArmature")
 rig=bpy.data.objects.new("SCP_OriginalSyntheticRig",rig_data);scene.collection.objects.link(rig)
 bpy.context.view_layer.objects.active=rig
 rig.select_set(True)
 bpy.ops.object.mode_set(mode="EDIT")
 r=rig_data.edit_bones.new("Root");r.head=(0,0,0);r.tail=(0,0,.5)
 u=rig_data.edit_bones.new("Upper");u.head=(0,0,.5);u.tail=(0,0,1);u.parent=r;u.use_connect=True
 bpy.ops.object.mode_set(mode="OBJECT")
 for name,weights in (("Root",[(0,1),(1,1),(2,.4),(3,.4)]),("Upper",[(2,.6),(3,.6),(4,1),(5,1)])):
  g=obj.vertex_groups.new(name=name)
  for i,wt in weights:g.add([i],wt,"REPLACE")
 obj.parent=rig
 mod=obj.modifiers.new("SCP_Armature",type="ARMATURE");mod.object=rig
 obj.shape_key_add(name="Basis",from_mix=False)
 tissue=obj.shape_key_add(name="Tissue",from_mix=False)
 for i in (2,3,4,5):tissue.data[i].co.x+=.035
 for frame,angle,value in ((0,0.,0.),(12,.3,.6),(24,-.23,.15)):
  scene.frame_set(frame)
  rig.pose.bones["Upper"].rotation_mode="XYZ"
  rig.pose.bones["Upper"].rotation_euler.y=angle
  rig.pose.bones["Upper"].keyframe_insert("rotation_euler",frame=frame)
  tissue.value=value
  tissue.keyframe_insert("value",frame=frame)
 scene.frame_set(0)
 rig.select_set(False)
 return scene
def glb_structure(path):
 raw=Path(path).read_bytes()
 if len(raw)<24 or raw[:4]!=b"glTF" or struct.unpack_from("<I",raw,4)[0]!=2:
  fail("GLB_HEADER_BAD")
 if struct.unpack_from("<I",raw,8)[0]!=len(raw):fail("GLB_BYTE_LENGTH")
 n,typ=struct.unpack_from("<II",raw,12)
 if typ!=0x4E4F534A or n<=0 or 20+n>len(raw):fail("GLB_JSON_CHUNK_BAD")
 js=json.loads(raw[20:20+n].decode("utf-8"))
 if not js.get("skins") or not js.get("animations") or not js.get("meshes"):
  fail("GLB_SKIN_MORPH_ANIMATION_MISSING")
 return {"file_sha256":sha(path),"mesh_entries":len(js["meshes"]),
         "skin_entries":len(js["skins"]),"animation_entries":len(js["animations"]),
         "morph_targets":sum(len(prim.get("targets",[])) for mesh in js["meshes"] for prim in mesh["primitives"])}
def witness(path,expected):
 rows=sample()
 if expected is not None:
  if len(expected)!=len(rows):fail("REOPEN_SAMPLE_COUNT")
  for a,b in zip(expected,rows):
   if a["frame"]!=b["frame"] or abs(a["shape_value"]-b["shape_value"])>1e-6 or abs(a["upper_rotation_y"]-b["upper_rotation_y"])>1e-6:
    fail("REOPEN_ANIMATION_DRIFT")
   for u,v in zip(a["evaluated_world_xyz"],b["evaluated_world_xyz"]):
    if math.dist(u,v)>1e-5:fail("REOPEN_SKIN_GEOMETRY_DRIFT")
 return rows
def run(args):
 out=Path(args.out)
 out.mkdir(parents=True,exist_ok=True)
 blend=out/"synthetic-reference.blend"
 glb=out/"synthetic-export.glb"
 receipt=out/"native.json"
 if args.stage=="build":
  make()
  s=witness(blend,None)
  bpy.context.scene.frame_set(0)
  bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
  bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",export_skins=True,export_morph=True,export_animations=True)
  g=glb_structure(glb)
  if g["morph_targets"]<1:fail("GLB_MORPH_TARGET_LOSS")
  payload={"schema":SCHEMA,"stage":"BUILD","version":bpy.app.version_string,
           "scene_sha256":sha(blend),"samples":s,"glb":g,"technical_compatibility_only":True}
  receipt.write_text(json.dumps(payload,sort_keys=True,indent=2,allow_nan=False)+"\n")
  print("SCP_BUILD_NATIVE_ABI",json.dumps({"version":bpy.app.version_string,"glb":g},sort_keys=True),flush=True)
 elif args.stage=="verify":
  original=json.loads(receipt.read_text())
  if sha(blend)!=original["scene_sha256"]:fail("SAVED_SOURCE_CHANGED")
  s=witness(blend,original["samples"])
  g=glb_structure(glb)
  if g!=original["glb"]:fail("GLB_CHANGED_BETWEEN_PROCESSES")
  result={"schema":SCHEMA,"status":"PASS_NARROW_NATIVE_CORE_ABI",
          "version":bpy.app.version_string,"source_scene_sha256":sha(blend),
          "glb_sha256":g["file_sha256"],"skin_entries":g["skin_entries"],
          "morph_targets":g["morph_targets"],"animation_entries":g["animation_entries"],
          "samples_verified":len(s),"frames":25,"fps":12,
          "native_reopen_qualified":True,"cross_version_parity_qualified":False,
          "mpfb_addon_accepted":False,"recorded_motion_contact_accepted":False,
          "mvp_accepted":False,"release_authorized":False}
  (out/"qualified.json").write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
  print("SCP_VERIFY_NATIVE_ABI",json.dumps(result,sort_keys=True),flush=True)
 else:fail("INVALID_STAGE")
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=("build","verify"),required=True)
 p.add_argument("--out",required=True)
 try:run(p.parse_args(sys.argv[sys.argv.index("--")+1:]))
 except (ValueError,RuntimeError,OSError,TypeError,KeyError) as e:
  print("SCP_BLENDER_ABI_RED",repr(e),file=sys.stderr);sys.exit(12)
