"""Real 4.5.16-produced MakeHuman dressed source scene, read-only forward-open in Blender 5.x."""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bridge_contract import check_observation,compare,FRAMES,ACTORS
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def reject(reason):raise RuntimeError(reason)
def evaluated(obj):
 bpy.context.view_layer.update()
 e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 m=e.to_mesh()
 try:
  if len(m.vertices)<100:reject("MISSING_EVALUATED_MESH")
  h=hashlib.sha256()
  for v in m.vertices:
   coords=(v.co.x,v.co.y,v.co.z)
   if not all(math.isfinite(float(x)) for x in coords):reject("NONFINITE_EVALUATED_MESH")
   h.update(struct.pack("<3f",*coords))
  return {"sha256":h.hexdigest(),"n":len(m.vertices)}
 finally:e.to_mesh_clear()
def pose(rig):
 h=hashlib.sha256()
 for bone in rig.pose.bones:
  for row in bone.matrix:
   for v in row:h.update(struct.pack("<f",float(v)))
 return h.hexdigest()
def observe():
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or sc.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":reject("UNLICENSED_SOURCE_OR_MISSING_CC0_WARDROBE")
 if sc.render.fps!=12 or sc.frame_start!=0 or sc.frame_end!=71:reject("SOURCE_CLOCK_NOT_R082")
 result={}
 for name in ACTORS:
  rig=bpy.data.objects.get(name+"_MPFBRig");body=bpy.data.objects.get(name+"_MPFBBody")
  if not rig or not body or rig.type!="ARMATURE" or len(rig.data.bones)!=163 or len(body.data.vertices)<10000:reject("ACTUAL_SOURCE_NATIVE_RIG_UNAVAILABLE")
  if not any(md.type=="ARMATURE" and md.object==rig for md in body.modifiers):reject("SKIN_RIG_LINK_LOST")
  clothes={ob.name:ob for ob in bpy.data.objects if ob.type=="MESH" and ob.name.startswith(name+"_CC0_")}
  if len(clothes)!=3:reject("SOURCE_WARDROBE_NOT_THREE")
  for obj in clothes.values():
   if not any(md.type=="ARMATURE" and md.object==rig for md in obj.modifiers):reject("GARMENT_RIG_LINK_LOST")
  samples=[]
  for frame in FRAMES:
   sc.frame_set(frame)
   samples.append({"frame":frame,"native_rig_bones":len(rig.data.bones),
     "body":evaluated(body),"rig_pose_sha256":pose(rig),
     "clothes":{k:evaluated(v) for k,v in sorted(clothes.items())}})
  result[name]=samples
 check_observation(result)
 return result
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=("baseline","forward"),required=True)
 p.add_argument("--scene",required=True);p.add_argument("--out",required=True)
 p.add_argument("--baseline",default="");p.add_argument("--target-version",default="")
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 version=".".join(str(x) for x in bpy.app.version)
 if a.stage=="baseline" and version!="4.5.16":reject("RECORD_ONLY_IN_4_5_16")
 if a.stage=="forward" and version!=a.target_version:reject("WRONG_EXACT_TARGET_VERSION")
 source_sha=sha(a.scene)
 obs=observe()
 if a.stage=="baseline":
  out={"schema":"scp.r094.blender-4-5-native-scene-baseline.v1",
   "scene_sha256":source_sha,"blender_version":version,"observations":obs,
   "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0_AND_EXACT_CC0_WARDROBE",
   "release_authorized":False}
  print("R094_SOURCE_BLENDER45_SNAPSHOT",json.dumps({"scene":source_sha,"actors":list(obs),"frame_count":len(FRAMES)},sort_keys=True),flush=True)
 else:
  origin=json.loads(Path(a.baseline).read_text())
  compare(origin,obs,source_sha)
  print("R094_FORWARD_NATIVE_GEOMETRY_COMPARE_PASS",source_sha,version,flush=True)
  sc=bpy.context.scene
  if sc.camera is None or sc.camera.type!="CAMERA":reject("RENDER_CAMERA_FROM_SOURCE_MISSING")
  sc.render.engine="CYCLES"
  sc.cycles.device="CPU"
  sc.cycles.samples=4
  sc.render.image_settings.file_format="PNG"
  sc.render.resolution_x=320;sc.render.resolution_y=180;sc.render.resolution_percentage=100
  sc.frame_set(35)
  png=Path(a.out).with_suffix(".png")
  sc.render.filepath=str(png)
  bpy.ops.render.render(write_still=True)
  if not png.exists() or png.stat().st_size<1024:reject("TARGET_NATIVE_RENDER_MISSING")
  # PNG is a private ephemeral diagnostic; no public artifact upload.
  out={"schema":"scp.r094.blender-4-5-to-new-native-scene-forward.v1","scene_sha256":source_sha,
   "source_blender":"4.5.16","target_blender":version,"actors":list(ACTORS),
   "frame_count":len(FRAMES),"all_native_body_and_cc0_garment_meshes_bit_equal":True,
   "rig_pose_samples_bit_equal":True,"native_cycles_cpu_render_succeeded":True,
   "renderer_png_source_published":False,"backward_read_to_4_5_tested":False,
   "full_visual_equivalence_accepted":False,"natural_gait_accepted":False,
   "source_licensing":"CC0_MPF_AND_GARMENTS",
   "release_authorized":False,"status":"PASS_NARROW_FORWARD_OPEN_NATIVE_RIG_GEOMETRY_ONLY"}
  print("R094_FORWARD_SOURCE_BOUND_PASS",json.dumps(out,sort_keys=True),flush=True)
 Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
if __name__=="__main__":main()
