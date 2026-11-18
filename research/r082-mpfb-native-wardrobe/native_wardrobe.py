"""R082 native source-qualified original-fictional MakeHuman garment fit and rig test."""
import argparse,hashlib,importlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
import wardrobe_contract as c
def fail(code):
 print("R082_NATIVE_RED",code,flush=True);raise RuntimeError(code)
def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def evaluated_hash(obj):
 import struct
 bpy.context.view_layer.update()
 e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=e.to_mesh()
 try:
  h=hashlib.sha256()
  for v in mesh.vertices:h.update(struct.pack("<3f",v.co.x,v.co.y,v.co.z))
  return h.hexdigest(),len(mesh.vertices)
 finally:e.to_mesh_clear()
def services():
 import addon_utils
 mod="bl_ext.user_default.mpfb"
 if not addon_utils.check(mod)[1]:addon_utils.enable(mod,default_set=False,persistent=False)
 if not addon_utils.check(mod)[1]:fail("MISSING_PINNED_MPF_EXTENSION")
 return importlib.import_module(mod+".services.humanservice").HumanService
def color_material(name,rgba):
 m=bpy.data.materials.new(name)
 m.use_nodes=True;m.diffuse_color=rgba
 b=m.node_tree.nodes.get("Principled BSDF")
 if b:
  b.inputs["Base Color"].default_value=rgba
  b.inputs["Roughness"].default_value=.84
 return m
def build(a):
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0":fail("BASE_SOURCE_CLASS_CHANGED")
 if not c.test_contract():fail("WRONG_OUTFIT_CONTRACT")
 out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 zipped={}
 for pack in c.PACKS:
  path=Path(a.packs)/(pack+"_cc0.zip")
  if not path.is_file():fail("ARCHIVE_MISSING_"+pack)
  zipped[pack]=c.source_archive(pack,path.read_bytes())
 cache=out/"asset-cache";cache.mkdir()
 hs=services();details=[]
 for name,layers in c.OUTFITS.items():
  body=bpy.data.objects.get(name+"_MPFBBody")
  rig=bpy.data.objects.get(name+"_MPFBRig")
  if body is None or rig is None:fail("NATIVE_MPF_BODY_RIG_NOT_FOUND")
  actor=[]
  for pack,asset,rgba in layers:
   z=zipped[pack]
   rel,members=c.select_bytes(z,asset)
   for n in members:z.extract(n,path=cache)
   mhclo=cache/rel
   if not mhclo.is_file():fail("SELECTED_ASSET_FILE_MISSING")
   bpy.ops.object.select_all(action="DESELECT")
   body.select_set(True);bpy.context.view_layer.objects.active=body
   garment=hs.add_mhclo_asset(str(mhclo.resolve()),body,asset_type="Clothes",subdiv_levels=0,material_type="NONE",
                             set_up_rigging=True,interpolate_weights=True,import_subrig=True,import_weights=True)
   if garment is None or garment.type!="MESH" or len(garment.data.vertices)<100:fail("REAL_MPF_GARMENT_NOT_IMPORTED_"+asset)
   if not any(x.type=="ARMATURE" and x.object==rig for x in garment.modifiers):fail("NATIVE_GARMENT_RIG_BINDING_MISSING_"+asset)
   garment.name=name+"_CC0_"+asset
   garment.data.materials.clear()
   garment.data.materials.append(color_material(garment.name+"_Procedural",rgba))
   scene.frame_set(0);h0,v0=evaluated_hash(garment)
   scene.frame_set(35);h1,v1=evaluated_hash(garment)
   if h0==h1 or v0!=v1:fail("MESH_GARMENT_DID_NOT_DEFORM_"+asset)
   actor.append({"asset":asset,"pack":pack,"mhclo_header":"EXPLICIT_CC0","native_object":garment.name,
                 "vertices":len(garment.data.vertices),"evaluated_vertices":v0,
                 "first_pose_sha256":h0,"mid_pose_sha256":h1,
                 "procedural_material":True,"source_licensed_external_texture_used":False})
  details.append({"name":name,"garments":actor})
 scene.frame_set(0)
 scene["r082_wardrobe"]="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL"
 scene.render.engine="BLENDER_WORKBENCH"
 scene.render.resolution_x=320;scene.render.resolution_y=180;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format="PNG"
 saved=out/"aster-juniper-cc0-native-wardrobe.blend"
 bpy.ops.wm.save_as_mainfile(filepath=str(saved.resolve()))
 result={"schema":"scp.r082.mpfb-cc0-native-outfit.v1","blend_sha256":digest(saved),
         "source_baseline_sha256":a.baseline_sha,"status":"PASS_NARROW_NATIVE_GARMENT_SKIN_HOLD_VISUAL",
         "archive_sha256":{p:c.PACKS[p]["sha256"] for p in c.PACKS},
         "characters":details,"source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
         "garment_collisions_accepted":False,"cloth_dynamics_accepted":False,
         "reference_outfit_match_accepted":False,"photoreal_accepted":False,
         "mvp_accepted":False,"release_authorized":False}
 (out/"build.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("R082_NATIVE_DRESSED_PAIR",json.dumps(result,sort_keys=True),flush=True)
def verify(a):
 scene=bpy.context.scene;out=Path(a.out)
 if digest(Path(a.scene))!=a.sha:fail("SAVED_WARDROBE_SHA_CHANGED")
 if scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":fail("UNVERIFIED_ASSET_CLASS")
 receipt=json.loads((out/"build.json").read_text())
 if receipt["blend_sha256"]!=a.sha:fail("RECEIPT_SCENE_JOIN_FAILED")
 observations=[]
 for frame in (0,35,71):
  scene.frame_set(frame);actors=[]
  for actor in receipt["characters"]:
   row=[]
   for garment in actor["garments"]:
    obj=bpy.data.objects.get(garment["native_object"])
    rig=bpy.data.objects.get(actor["name"]+"_MPFBRig")
    if not obj or not any(mod.type=="ARMATURE" and mod.object==rig for mod in obj.modifiers):fail("FRESH_REOPEN_ASSET_RIG_LOST")
    h,n=evaluated_hash(obj)
    if n!=garment["evaluated_vertices"]:fail("FRESH_REOPEN_GARMENT_VERTEX_COUNT_CHANGED")
    row.append({"asset":garment["asset"],"deformed_mesh_sha256":h})
   actors.append({"name":actor["name"],"garments":row})
  observations.append({"frame":frame,"actors":actors})
 for i in range(2):
  for j in range(3):
   if observations[0]["actors"][i]["garments"][j]["deformed_mesh_sha256"]==observations[1]["actors"][i]["garments"][j]["deformed_mesh_sha256"]:fail("STATIC_GARMENT_NOT_ANIMATED")
 stills=out/"stills";stills.mkdir(exist_ok=False)
 for frame in (0,35,71):
  scene.frame_set(frame);scene.render.filepath=str(stills/("frame_%03d.png"%frame));bpy.ops.render.render(write_still=True)
 result={"schema":"scp.r082.garment-fresh-reopen.v1","scene_sha256":a.sha,"observations":observations,
         "status":"PASS_NATIVE_OUTFIT_RIG_NARROW_HOLD_CLOTH",
         "reference_outfit_match_accepted":False,"cloth_simulation_accepted":False,
         "photoreal_accepted":False,"mvp_accepted":False,"release_authorized":False}
 (out/"verify.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("R082_WARDROBE_VERIFY",json.dumps(result,sort_keys=True),flush=True)
def parse():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=("build","verify"),required=True)
 p.add_argument("--packs",default="");p.add_argument("--out",required=True)
 p.add_argument("--baseline-sha",default="");p.add_argument("--scene",default="");p.add_argument("--sha",default="")
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
if __name__=="__main__":
 try:
  a=parse()
  if a.stage=="build":build(a)
  else:verify(a)
 except (RuntimeError,ValueError,OSError,KeyError,TypeError) as e:
  print("R082_FAIL_CLOSED",repr(e),file=sys.stderr);sys.exit(12)
