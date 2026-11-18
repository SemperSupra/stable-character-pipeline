"""Source-bound native five-bone Blender IK actuator probe on existing R090 public CC0 scene.
A temporary foot-tail target is NOT a validated sole-contact anchor or full gait cure.
No scene, source assets or modified rig are saved.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from ik_contract import chain,validate_parents,classify
from measure import stable_sole_sample,sha as sha_file
from shoe_contact import quantify

def fail(code):raise RuntimeError(code)
def world_tail(rig,bone):return rig.matrix_world @ rig.pose.bones[bone].tail
def world_head(rig,bone):return rig.matrix_world @ rig.pose.bones[bone].head
def sample_all(scene,rig,shoe,side,frames):
 foot=chain(side)[0]
 output=[]
 for f in frames:
  scene.frame_set(f);bpy.context.view_layer.update()
  p=world_tail(rig,foot).copy()
  root=world_head(rig,"root").copy()
  sole=stable_sole_sample(shoe)
  output.append({"frame":f,"foot_tail_world":p,"root_head_world":root,"sole":sole})
 return output
def actor_probe(scene,actor):
 name=actor["name"]
 if name not in ("AsterOriginal","JuniperOriginal"):fail("NOT_ORIGINAL_SYNTHETIC_ACTOR")
 rig=bpy.data.objects.get(name+"_MPFBRig")
 if rig is None or len(rig.data.bones)!=163:fail("NATIVE_RIG_NOT_163")
 shoes=[g for g in actor["garments"] if g["pack"]=="shoes01"]
 if len(shoes)!=1:fail("MISSING_CC0_SHOES")
 shoe=bpy.data.objects.get(shoes[0]["native_object"])
 if shoe is None or not any(md.type=="ARMATURE" and md.object==rig for md in shoe.modifiers):fail("SHOE_RIG_SOURCE_JOIN")
 sides=[]
 for side in ("L","R"):
  bone_names=chain(side)
  parents={name:rig.data.bones[name].parent.name if rig.data.bones.get(name) and rig.data.bones[name].parent else None for name in (*bone_names,)}
  validate_parents(side,parents)
  # The source native-action is evaluated BEFORE adding the IK constraint.
  frames=list(range(12,19))
  before=sample_all(scene,rig,shoe,side,frames)
  anchor=before[0]["foot_tail_world"].copy()
  target=bpy.data.objects.new("N03C_temporary_"+name+"_"+side,None)
  bpy.context.scene.collection.objects.link(target)
  target.location=anchor
  foot=rig.pose.bones[bone_names[0]]
  con=foot.constraints.new("IK")
  con.target=target
  con.chain_count=5
  con.iterations=100
  con.use_stretch=False
  con.use_rotation=False
  con.use_location=True
  rows=[]
  try:
   for f,b in zip(frames,before):
    scene.frame_set(f);bpy.context.view_layer.update()
    p=world_tail(rig,bone_names[0])
    root=world_head(rig,"root")
    sole=stable_sole_sample(shoe)
    rows.append({"before_target_error_m":float((b["foot_tail_world"]-anchor).length),
                 "after_target_error_m":float((p-anchor).length),
                 "root_pose_drift_m":float((root-b["root_head_world"]).length),
                 "shoe_min_z_m":float(min(v["z_m"] for v in sole.values()))})
   verdict=classify(rows)
   if not verdict["native_ik_effect_observed"]:fail("NATIVE_IK_TARGET_NO_EFFECT")
   def side_metrics(samples):
    parts=("rest_local_x_negative","rest_local_x_positive")
    return {k:quantify([s["sole"][k] for s in samples],12) for k in parts}
   after_samples=[]
   # Revisit for the candidate surface with the temporary IK still applied.
   for f in frames:
    scene.frame_set(f);bpy.context.view_layer.update()
    after_samples.append({"sole":stable_sole_sample(shoe)})
   metrics={"before":side_metrics(before),"after":side_metrics(after_samples)}
   sides.append({"foot_rig_label":side,"rig_label_is_authoritative_anatomical_side":False,
     "chain_count":con.chain_count,"actual_bone_chain":list(bone_names),
     "static_foot_tail_target_world_m":[float(x) for x in anchor],
     "sampled_frames":frames,"witness":verdict,
     "target_errors":rows,"actual_evaluated_cc0_shoe":metrics,
     "joint_rom_validated":False,"contact_accepted":False})
  finally:
   foot.constraints.remove(con)
   bpy.data.objects.remove(target,do_unlink=True)
 return {"actor":name,"native_rig_163":True,"legs":sides}
def main():
 p=argparse.ArgumentParser()
 for k in ("scene","sha","wardrobe","retarget","out"):p.add_argument("--"+k,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if sha_file(a.scene)!=a.sha:fail("SOURCE_SCENE_SHA_MISMATCH")
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":fail("SOURCE_RIGHTS_INVALID")
 if scene.render.fps!=12 or scene.frame_end<71:fail("SOURCE_72F_CLOCK_INVALID")
 ward=json.loads(Path(a.wardrobe).read_text())
 recorded=json.loads(Path(a.retarget).read_text())
 if ward.get("schema")!="scp.r082.mpfb-cc0-native-outfit.v1" or recorded.get("schema")!="scp.r090.sixsecond-dressed-real-retarget.v1" or recorded.get("candidate_blend_sha256")!=a.sha or recorded.get("input_scene_sha256")!=ward.get("blend_sha256"):fail("INVALID_NATIVE_SOURCE_LINEAGE")
 actors=[actor_probe(scene,v) for v in ward["characters"]]
 if sorted(x["actor"] for x in actors)!=["AsterOriginal","JuniperOriginal"]:fail("INVALID_ACTOR_SET")
 report={"schema":"scp.n03c.real-native-5bone-target-probe.v1","status":"PASS_NARROW_IK_ACTUATOR_NOT_CONTACT_ACCEPTANCE",
   "source_scene_sha256":a.sha,"frames":list(range(12,19)),"fps":12,
   "actors":actors,"source_asset_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
   "soles_still_diagnostic_not_anatomical":True,"heel_toe_anchors_validated":False,
   "source_scene_saved":False,"full_gait_contact_accepted":False,
   "mvp_accepted":False,"release_authorized":False}
 target=Path(a.out)
 target.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03C_ACTUAL_NATIVE_5BONE_IK",json.dumps(report,sort_keys=True,allow_nan=False),flush=True)
if __name__=="__main__":
 try:main()
 except (ValueError,RuntimeError,TypeError,KeyError,OSError) as e:
  print("N03C_FAIL_CLOSED",repr(e),file=sys.stderr);sys.exit(12)
