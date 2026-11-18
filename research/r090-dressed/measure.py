"""Actual CC0 evaluated shoe mesh contact, both unmodified and retargeted."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent.parent/"r084-shoe-contact"))
from native_shoe_contact import sole_sample,height_ground
from shoe_contact import quantify
def fail(s):raise RuntimeError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for s in ("scene","sha","wardrobe","retarget","out"):p.add_argument("--"+s,default="")
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if sha(a.scene)!=a.sha:fail("INVALID_SAVED_SCENE_SHA")
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or sc.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":fail("SOURCE_RIGHTS_OR_CC0_WARDROBE_MARKER")
 if sc.render.fps!=12 or sc.frame_end<71:fail("NOT_ACTUAL_72F_12FPS_SCENE")
 ground=bpy.data.objects.get("R078_Original_FlatParkProxy")
 if not ground or abs(height_ground(ground))>0.0001:fail("ACTUAL_GROUND_PLANE_LOST")
 ward=json.loads(Path(a.wardrobe).read_text())
 if ward["schema"]!="scp.r082.mpfb-cc0-native-outfit.v1":fail("BAD_WARDROBE_MANIFEST")
 mode="recorded" if a.retarget else "authored"
 if a.retarget:
  record=json.loads(Path(a.retarget).read_text())
  if record["schema"]!="scp.r090.sixsecond-dressed-real-retarget.v1" or record["candidate_blend_sha256"]!=a.sha:fail("RECORDED_SOURCE_SCENE_MISMATCH")
  if record["input_scene_sha256"]!=ward["blend_sha256"]:fail("RECORDED_NOT_SAME_WARDROBE")
  if any(row["target_action_frame_range"][1]<70 for row in record["actors"]):fail("MOTION_BARELY_ONE_SECOND")
 elif ward["blend_sha256"]!=a.sha:fail("AUTHORED_SOURCE_SHA_MISMATCH")
 rows=[]
 for actor in ward["characters"]:
  name=actor["name"]
  if name not in ("AsterOriginal","JuniperOriginal"):fail("UNKNOWN_ACTOR")
  shoes=[g for g in actor["garments"] if g["pack"]=="shoes01"]
  if len(shoes)!=1:fail("MISSING_SINGLE_ACTUAL_SHOE_ASSET")
  shoe=bpy.data.objects.get(shoes[0]["native_object"]);rig=bpy.data.objects.get(name+"_MPFBRig")
  if not shoe or not rig or len(rig.data.bones)!=163:fail("NATIVE_ACTOR_SHOES_NOT_FOUND")
  if not any(md.type=="ARMATURE" and md.object==rig for md in shoe.modifiers):fail("SHOES_NOT_BOUND_TO_ACTOR")
  tracks={"x_negative":[],"x_positive":[]}
  for frame in range(72):
   sc.frame_set(frame)
   samples=sole_sample(shoe,rig)
   for side in tracks:tracks[side].append(samples[side])
  rows.append({"actor":name,"shoe":shoes[0]["asset"],
   "world_x_partitions":{side:quantify(points,12) for side,points in tracks.items()},
   "anatomical_side_verified":False})
 out={"schema":"scp.r090.72f-real-shoe-contact.v1","mode":mode,"scene_sha256":a.sha,
  "wardrobe_base_sha256":ward["blend_sha256"],"fps":12,"frames":72,"actors":rows,
  "source_origin":"ORIGINAL_FICTIONAL_AND_SOURCE_RIGHTS_PINNED",
  "physical_contact_accepted":False,"gait_accepted":False,"mvp_accepted":False}
 Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print("R090_ACTUAL_SOLE_CONTACT",json.dumps(out,sort_keys=True,allow_nan=False),flush=True)
if __name__=="__main__":main()
