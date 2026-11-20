"""Actual retarget-preprocess variant independent new-scene foot bone and CC0 sole speed."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from score import diagnostic
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-l-source-motion"))
from source_contact import summarize
def bad(s):raise RuntimeError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def head_world(rig,side):
 bone=rig.pose.bones.get("foot."+side)
 if bone is None:bad("FOOT_BONE_NOT_PRESENT")
 p=rig.matrix_world@bone.head
 return (float(p.x),float(p.z),float(p.y))
def main():
 p=argparse.ArgumentParser()
 for n in ("scene","sha","wardrobe","variant-report","baseline","variant","map-receipt","out"):p.add_argument("--"+n,required=True)
 args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if sha(args.scene)!=args.sha:bad("CANDIDATE_SCENE_SHA_DIFFERENT")
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or sc.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":bad("SOURCE_NOT_ORIGINAL_CC0")
 ward=json.loads(Path(args.wardrobe).read_text())
 rec=json.loads(Path(args.variant_report).read_text())
 baseline=json.loads(Path(args.baseline).read_text())
 mapinfo=json.loads(Path(args.map_receipt).read_text())
 if mapinfo.get("schema")!="scp.n03d-q.ephemeral-upstream-target-map-variant.v1" or mapinfo.get("variant")!=args.variant or mapinfo.get("upstream_git_blob_sha1")!="65a49435cc726f2089373caa34373909ff0f2a8e":bad("UNQUALIFIED_MAP_VARIANT_RECEIPT")
 if rec.get("candidate_blend_sha256")!=args.sha or rec.get("input_scene_sha256")!=ward.get("blend_sha256"):bad("VARIANT_RECORD_SOURCE_JOIN")
 if baseline.get("schema")!="scp.n03d-m.source60hz-fk-vs-retarget-foot24hz.v1" or sorted(x["actor"] for x in baseline["actors"])!=["AsterOriginal","JuniperOriginal"]:bad("DEFAULT_BASELINE_NOT_VERIFIED")
 if sorted(x["actor"] for x in rec["actors"])!=["AsterOriginal","JuniperOriginal"]:bad("VARIANT_RECORDED_ACTOR_MISMATCH")
 if (sc.frame_start,sc.frame_end,sc.render.fps)!=(0,71,12):bad("VARIANT_CLOCK_INVALID")
 actors=[]
 for actor in baseline["actors"]:
  name=actor["actor"]
  rig=bpy.data.objects.get(name+"_MPFBRig")
  if rig is None or len(rig.data.bones)!=163:bad("MISSING_REAL_MPF_RIG")
  entry=next(x for x in ward["characters"] if x["name"]==name)
  shoes=[x for x in entry["garments"] if x["pack"]=="shoes01"]
  if len(shoes)!=1:bad("SHOE_SOURCE_RIGHTS_INVALID")
  shoe=bpy.data.objects.get(shoes[0]["native_object"])
  if shoe is None or not any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers):bad("MISSING_SOURCE_SHOE_BIND")
  pose={s:[] for s in ("L","R")}
  soles={s:[] for s in ("rest_local_x_negative","rest_local_x_positive")}
  for i in range(143):
   sc.frame_set(i//2,subframe=(i%2)*.5);bpy.context.view_layer.update()
   for side in pose:pose[side].append(head_world(rig,side))
   v=stable_sole_sample(shoe)
   for side in soles:
    pt=v[side];soles[side].append((pt["xy_m"][0],pt["z_m"],pt["xy_m"][1]))
  result_sides=[]
  for side in ("L","R"):
   src=next(x for x in actor["source_vs_native"] if x["rig_side"]==side)
   pts=summarize(pose[side],1/24)
   result_sides.append({"rig_side":side,
    "default_native_foot_near_p50_mps":src["native_foot_head_near_p50_mps"],
    "candidate_native_foot_near_p50_mps":pts["near_ground_p50_world_speed_mps"],
    "source_ankle_near_p50_mps":src["source_ankle_near_p50_mps"],
    "candidate_vs_default":diagnostic(src["native_foot_head_near_p50_mps"],pts["near_ground_p50_world_speed_mps"]),
    "candidate_vs_original_ankle":diagnostic(src["source_ankle_near_p50_mps"],pts["near_ground_p50_world_speed_mps"])})
  actors.append({"actor":name,"rig_sides":result_sides,
    "cc0_shoe_actual_support_patch":{k:summarize(pts,1/24) for k,pts in soles.items()}})
 out={"schema":"scp.n03d-n.real-retarget-preprocess-policy-bakeoff.v1",
  "variant":args.variant,"scene_sha256":args.sha,
  "baseline_fingerprint_sha256":sha(args.baseline),
  "source_mapping_variant_sha256":mapinfo["modified_known_map_sha256"],
  "source_mapping_variant":args.variant,
  "record_sha256":sha(args.variant_report),
  "source_rights":"ORIGINAL_FICTIONAL_CC0_AND_100STYLE_CC_BY_4",
  "actors":actors,"true_anatomical_joint_alignment":False,
  "blender_version":bpy.app.version_string,
  "retarget_kinematic_improvement_not_physical_contact":True,
  "physical_foot_plant_accepted":False,"natural_gait_accepted":False,
  "protected_source_identity_accepted":False,"mvp_accepted":False,
  "release_authorized":False}
 Path(args.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_Q_VARIANT_LEG_MAP_FOOT_RESULT",json.dumps({
  "variant":args.variant,
  "actors":[{"name":x["actor"],"feet":[{"side":r["rig_side"],"default_mps":r["default_native_foot_near_p50_mps"],
     "candidate_mps":r["candidate_native_foot_near_p50_mps"],"relative_speed":r["candidate_vs_default"]["ratio"]}
     for r in x["rig_sides"]]} for x in actors],
  "contact_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
