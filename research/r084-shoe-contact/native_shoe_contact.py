"""Read-only native test of shoe sole proximity to R078 flat ground.
Uses actual skinned MakeHuman CC0 garment geometry, not metadata-only simulation.
"""
import argparse,hashlib,heapq,json,math,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from shoe_contact import quantify, point, SCHEMA
def reject(reason):
 print("R084_NATIVE_RED",reason,flush=True);raise RuntimeError(reason)
def digest(path):
 h=hashlib.sha256()
 with open(path,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def height_ground(obj):
 return max((obj.matrix_world @ __import__("mathutils").Vector(v)).z for v in obj.bound_box)
def sole_sample(shoe,rig):
 bpy.context.view_layer.update()
 dg=bpy.context.evaluated_depsgraph_get()
 evalshoe=shoe.evaluated_get(dg)
 mesh=evalshoe.to_mesh()
 try:
  if len(mesh.vertices)<300:reject("SHOE_MESH_NOT_PRESENT")
  origin_x=rig.matrix_world.translation.x
  left=[];right=[]
  matrix=evalshoe.matrix_world
  for vert in mesh.vertices:
   w=matrix @ vert.co
   if not all(math.isfinite(v) for v in (w.x,w.y,w.z)):reject("NONFINITE_SHOE_SURFACE")
   bucket=left if w.x<origin_x else right
   bucket.append((w.z,w.x,w.y))
  if min(len(left),len(right))<80:reject("SHOE_BILATERAL_PARTS_MISSING_OR_CENTER_UNCERTAIN")
  result={}
  for name,coords in (("x_negative",left),("x_positive",right)):
   bottom=heapq.nsmallest(max(8,len(coords)//100),coords)
   z=min(v[0] for v in bottom)
   xy=(sum(v[1] for v in bottom)/len(bottom),sum(v[2] for v in bottom)/len(bottom))
   result[name]=point(z,xy)
  return result
 finally:evalshoe.to_mesh_clear()
def execute(args):
 if digest(args.scene)!=args.sha:reject("SOURCE_SCENE_SHA_CHANGED")
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":reject("UNTRUSTED_SOURCE_OR_WARDROBE")
 if (scene.frame_start,scene.frame_end,scene.render.fps)!=(0,71,12):reject("REPRODUCED_CLOCK_MISMATCH")
 archive=Path(args.out)
 archive.mkdir(parents=True,exist_ok=False)
 manifest=json.loads(Path(args.wardrobe).read_text())
 if manifest["schema"]!="scp.r082.mpfb-cc0-native-outfit.v1" or manifest["blend_sha256"]!=args.sha:reject("WARDROBE_RECEIPT_JOIN")
 ground=bpy.data.objects.get("R078_Original_FlatParkProxy")
 if not ground or abs(height_ground(ground))>.0001:reject("INDEPENDENT_GROUND_PLANE_MISSING")
 measured=[]
 for actor in manifest["characters"]:
  name=actor["name"]
  if name not in ("AsterOriginal","JuniperOriginal"):reject("NON_ORIGINAL_PROXY")
  shoe_rows=[g for g in actor["garments"] if g["pack"]=="shoes01"]
  if len(shoe_rows)!=1:reject("NO_SINGLE_QUALIFIED_SHOE_ASSET")
  shoe=bpy.data.objects.get(shoe_rows[0]["native_object"])
  rig=bpy.data.objects.get(name+"_MPFBRig")
  if not shoe or not rig:reject("SHOE_OR_RIG_NOT_FOUND")
  if not any(md.type=="ARMATURE" and md.object==rig for md in shoe.modifiers):reject("NO_ACTUAL_SHOE_RIG_BIND")
  tracks={"x_negative":[],"x_positive":[]}
  for frame in range(scene.frame_start,scene.frame_end+1):
   scene.frame_set(frame)
   samples=sole_sample(shoe,rig)
   for side in tracks:tracks[side].append(samples[side])
  measured.append({"actor":name,"source_shoe":shoe_rows[0]["asset"],
                   "feet":{side:quantify(samples,12) for side,samples in tracks.items()},
                   "side_labels":"OBJECT_LOCAL_X_SPLIT_DIAGNOSTIC_NOT_ANATOMICAL_LEFT_RIGHT"})
 report={"schema":SCHEMA,"status":"MEASURED_NATIVE_CC0_SHOE_CONTACT_UNACCEPTED",
         "source_scene_sha256":args.sha,"frames":72,"fps":12,
         "ground_z_m":0,"actors":measured,
         "reference_identity_accepted":False,"shoe_ground_contact_accepted":False,
         "natural_gait_accepted":False,"mvp_accepted":False,"release_authorized":False}
 (archive/"shoe-contact.json").write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("R084_SHOE_CONTACT_OBSERVATION",json.dumps(report,sort_keys=True,allow_nan=False),flush=True)
def parse():
 p=argparse.ArgumentParser();p.add_argument("--scene",required=True);p.add_argument("--sha",required=True)
 p.add_argument("--wardrobe",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
if __name__=="__main__":
 try:execute(parse())
 except (RuntimeError,OSError,ValueError,KeyError,TypeError) as e:
  print("R084_FAIL_CLOSED",repr(e),file=sys.stderr);sys.exit(12)
