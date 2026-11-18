"""R085 reversible minimum shoe-ground penetration mitigation, not a foot-contact or gait cure.
Source: original fictional MPFB R082 native CC0 garments, 72f/12fps only.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).parent.parent/"r084-shoe-contact"))
from native_shoe_contact import sole_sample,digest
from shoe_contact import quantify
from floor_math import lift_for_min_z
def reject(code):
 print("R085_NATIVE_RED",code,flush=True);raise RuntimeError(code)
def manifest(args):
 if digest(args.scene)!=args.source_sha:reject("SOURCE_SCENE_SHA_MISMATCH")
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":reject("SOURCE_CLOTHING_TIER_INVALID")
 if (scene.frame_start,scene.frame_end,scene.render.fps)!=(0,71,12):reject("SOURCE_FRAME_CLOCK_INVALID")
 rows=json.loads(Path(args.wardrobe).read_text())
 if rows.get("schema")!="scp.r082.mpfb-cc0-native-outfit.v1" or rows.get("blend_sha256")!=args.source_sha:reject("DRESSED_SOURCE_RECEIPT_MISMATCH")
 if len(rows.get("characters",[]))!=2:reject("ACTOR_PAIR_COUNT")
 return rows
def actors_from(rows):
 result=[]
 for row in rows["characters"]:
  actor=row["name"]
  if actor not in ("AsterOriginal","JuniperOriginal"):reject("UNKNOWN_ACTOR")
  shoes=[g for g in row["garments"] if g.get("pack")=="shoes01"]
  if len(shoes)!=1:reject("MISSING_APPROVED_CC0_SHOE")
  obj=bpy.data.objects.get(shoes[0]["native_object"])
  rig=bpy.data.objects.get(actor+"_MPFBRig")
  root=bpy.data.objects.get(actor+"_MotionRoot")
  if not all((obj,rig,root)) or len(rig.data.bones)!=163:reject("NATIVE_ACTOR_RIG_OR_ROOT_MISSING")
  if not any(m.type=="ARMATURE" and m.object==rig for m in obj.modifiers):reject("SHOE_SKIN_BINDING_LOST")
  result.append((actor,obj,rig,root))
 return result
def measured_track(shoe,rig):
 return {"x_negative":[],"x_positive":[]}
def build(a):
 rows=manifest(a)
 target=Path(a.out)
 target.mkdir(parents=True,exist_ok=False)
 before={}
 # Freeze all source observations BEFORE applying any keyframe edits.
 for actor,shoe,rig,root in actors_from(rows):
  sides=measured_track(shoe,rig)
  roots=[]
  for f in range(72):
   bpy.context.scene.frame_set(f)
   xyz=(root.location.x,root.location.y,root.location.z)
   roots.append([round(v,8) for v in xyz])
   samples=sole_sample(shoe,rig)
   for side in sides:sides[side].append(samples[side])
  lifts=[lift_for_min_z(min(sides[side][f]["z_m"] for side in sides)) for f in range(72)]
  before[actor]={"shoe_asset":shoe.name,"source_root_xyz":roots,
                 "source_ground_evidence":{side:quantify(samples,12) for side,samples in sides.items()},
                 "required_root_lift_m":lifts,"maximum_root_lift_m":round(max(lifts),8)}
 for actor,shoe,rig,root in actors_from(rows):
  initial=before[actor]
  for f in range(72):
   bpy.context.scene.frame_set(f)
   original=initial["source_root_xyz"][f]
   root.location=(original[0],original[1],original[2]+initial["required_root_lift_m"][f])
   root.keyframe_insert(data_path="location",frame=f)
 bpy.context.scene.frame_set(0)
 bpy.context.scene["r085_correction"]="SOLE_DERIVED_INTEGER_ROOT_Z_FIRST_BOUNDED_CANDIDATE"
 bpy.context.scene["r085_original_sha256"]=a.source_sha
 saved=target/"r085-floor-lift-candidate.blend"
 bpy.ops.wm.save_as_mainfile(filepath=str(saved.resolve()))
 record={"schema":"scp.r085.shoe-floor-lift-build.v1","status":"PROPOSED_GROUND_PENETRATION_CORRECTION_NOT_ACCEPTED",
         "source_sha256":a.source_sha,"candidate_sha256":digest(saved),"actors":before,
         "frames":72,"fps":12,"source_character_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
         "manual_mvp_accepted":False,"natural_gait_accepted":False,"shoe_traction_accepted":False,
         "nonpenetration_accepted":False,"release_authorized":False}
 (target/"before.json").write_text(json.dumps(record,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("R085_LIFT_BUILD",json.dumps({"sha":record["candidate_sha256"],
  "max_lift_m":{k:v["maximum_root_lift_m"] for k,v in before.items()}},sort_keys=True))
def verify(a):
 if digest(a.scene)!=a.sha:reject("CANDIDATE_SCENE_SHA_MISMATCH")
 result=json.loads(Path(a.before).read_text())
 if result["schema"]!="scp.r085.shoe-floor-lift-build.v1" or result["candidate_sha256"]!=a.sha:reject("CORRECTION_RECEIPT_SHA_MISMATCH")
 if bpy.context.scene.get("r085_original_sha256")!=result["source_sha256"]:reject("SOURCE_LINEAGE_LOST")
 if (bpy.context.scene.frame_start,bpy.context.scene.frame_end,bpy.context.scene.render.fps)!=(0,71,12):reject("CORRECTION_TIMEBASE_CHANGED")
 rows=json.loads(Path(a.wardrobe).read_text())
 observed=[]
 for actor,shoe,rig,root in actors_from(rows):
  src=result["actors"][actor]
  sides=measured_track(shoe,rig)
  for f in range(72):
   bpy.context.scene.frame_set(f)
   xyz=src["source_root_xyz"][f]
   if abs(root.location.x-xyz[0])>1e-5 or abs(root.location.y-xyz[1])>1e-5:reject("CRITICAL_APPROACH_PATH_CHANGED")
   if abs(root.location.z-(xyz[2]+src["required_root_lift_m"][f]))>1e-5:reject("ROOT_Z_CORRECTION_NOT_PERSISTED")
   samples=sole_sample(shoe,rig)
   for side in sides:sides[side].append(samples[side])
  after={side:quantify(samples,12) for side,samples in sides.items()}
  old=src["source_ground_evidence"]
  for side in sides:
   if after[side]["penetration_m"]>0.006:reject("CORRECTION_FAILED_GROUND_PENETRATION_"+actor+"_"+side)
   if old[side]["penetration_m"]>0.012 and after[side]["penetration_m"]>=old[side]["penetration_m"]:reject("NO_CORRECTION_GAIN")
  observed.append({"actor":actor,"before":old,"after":after,
    "maximum_root_lift_m":src["maximum_root_lift_m"],
    "natural_ground_contact_accepted":False})
 receipt={"schema":"scp.r085.source-bound-floor-correction-verify.v1",
          "state":"PASS_NATIVE_BELOW_GROUND_MITIGATION_ONLY_HOLD_FOOT_TRACTION",
          "source_scene_sha256":result["source_sha256"],"candidate_scene_sha256":a.sha,
          "frames":72,"fps":12,"actors":observed,"full_foot_ik_accepted":False,
          "shoe_slip_corrected":False,"natural_gait_accepted":False,"mvp_accepted":False,
          "release_authorized":False}
 pathlib=Path(a.out)
 pathlib.joinpath("after.json").write_text(json.dumps(receipt,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("R085_FLOOR_CORRECTION_VERIFIED",json.dumps({"candidate":a.sha,"deltas":[{"actor":o["actor"],"before_m":[v["penetration_m"] for v in o["before"].values()],"after_m":[v["penetration_m"] for v in o["after"].values()]} for o in observed]},sort_keys=True))
def parse():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=["build","verify"],required=True)
 p.add_argument("--scene",required=True)
 p.add_argument("--source-sha",default="")
 p.add_argument("--sha",default="")
 p.add_argument("--wardrobe",required=True)
 p.add_argument("--before",default="")
 p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
if __name__=="__main__":
 try:
  a=parse()
  if a.stage=="build":build(a)
  else:verify(a)
 except (OSError,ValueError,RuntimeError,KeyError,TypeError) as err:
  print("R085_FAIL_CLOSED",repr(err),file=sys.stderr);sys.exit(12)
