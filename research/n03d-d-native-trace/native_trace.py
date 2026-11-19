"""N03D-D: source-bound 24Hz actual evaluated shoe-world geometry observations.
No claiming physical foot plant, anatomy, or source actor identity. Native bpy only.
"""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample
from mathutils import Vector

def reject(msg):raise RuntimeError(msg)
def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def mesh_hash(mesh):
 h=hashlib.sha256()
 for v in mesh.vertices:
  h.update(struct.pack("<3f",v.co.x,v.co.y,v.co.z))
 return h.hexdigest()
def trace_scene(args):
 if file_hash(args.scene)!=args.sha:reject("SOURCE_SCENE_SHA_NOT_PINNED")
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":reject("UNTRUSTED_CHARACTER_OR_CC0_GARMENTS")
 ward=json.loads(Path(args.wardrobe).read_text())
 rec=json.loads(Path(args.retarget).read_text())
 if ward.get("schema")!="scp.r082.mpfb-cc0-native-outfit.v1" or rec.get("schema")!="scp.r090.sixsecond-dressed-real-retarget.v1":reject("SOURCE_MANIFEST_SCHEMA")
 if rec.get("candidate_blend_sha256")!=args.sha or rec.get("input_scene_sha256")!=ward.get("blend_sha256"):reject("SOURCE_SCENE_WARDROBE_JOIN")
 if rec.get("motion_source_blob_sha1")!="a534f69b1d7a867f9b7d4dccefcf3f1d255c4a61":reject("REAL_BVH_SOURCE_NOT_PINNED")
 if (scene.frame_start,scene.frame_end,scene.render.fps)!=(0,71,12):reject("NATIVE_ACTION_CLOCK_MISMATCH")
 if sorted(a["actor"] for a in rec["actors"])!=["AsterOriginal","JuniperOriginal"]:reject("PROTECTED_OR_UNKNOWN_ACTOR")
 source_witness=hashlib.sha256()
 actors=[]
 for wr in ward["characters"]:
  name=wr["name"]
  rig=bpy.data.objects.get(name+"_MPFBRig")
  if rig is None or len(rig.data.bones)!=163 or rig.animation_data is None or rig.animation_data.action is None:reject("ACTUAL_163_BONE_ACTION_NOT_PRESENT")
  dressed=[o for o in bpy.data.objects if o.type=="MESH" and o.name.startswith(name+"_CC0_")]
  if len(dressed)!=3 or any(not any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers) for o in dressed):reject("ACTUAL_CC0_DRESSED_RIG_MISSING")
  footwear=[x for x in wr["garments"] if x["pack"]=="shoes01"]
  if len(footwear)!=1:reject("SOURCE_SHOE_NOT_SINGLE")
  shoe=bpy.data.objects.get(footwear[0]["native_object"])
  if shoe is None or shoe not in dressed:reject("SOURCE_WARDROBE_SHOE_WRONG")
  source_witness.update(name.encode())
  source_witness.update(rig.animation_data.action.name.encode())
  for actor in rec["actors"]:
   if actor["actor"]==name:
    for s in actor["samples"]:source_witness.update(s["rig_pose_sha256"].encode())
  raw_hash=mesh_hash(shoe.data)
  parts={side:{"shoe_rest_mesh_sha256":raw_hash,
               "anatomical_side_verified":False,"samples":[],
               "shoe_pitch_proxy_anatomically_accepted":False}
         for side in ("rest_local_x_negative","rest_local_x_positive")}
  for i in range(143):
   scene.frame_set(i//2,subframe=(i%2)*.5)
   values=stable_sole_sample(shoe)
   for side in parts:
    point=values[side]
    if not math.isfinite(point["z_m"]) or not all(math.isfinite(v) for v in point["xy_m"]):reject("NONFINITE_EVALUATED_SHOE")
    parts[side]["samples"].append({"t_s":round(i/24.,9),
       "z_m":round(point["z_m"],9),
       "xy_m":[round(v,9) for v in point["xy_m"]]})
  actors.append({"actor":name,"native_bones":len(rig.data.bones),
                 "original_cc0_shoe":footwear[0]["asset"],"sides":parts})
 report={"schema":"scp.n03d-g.evaluated-foot-contact-observer.v1",
  "source_class":"ORIGINAL_FICTIONAL_CC0",
  "source_scene_sha256":args.sha,
  "source_wardrobe_sha256":ward["blend_sha256"],
  "source_100style_sha256":rec["source"]["original_bvh_sha256"],
  "retarget_action_sha256":source_witness.hexdigest(),
  "retarget_action_sha256_method":"SAMPLED_NATIVE_POSE_AND_ACTION_NAME_WITNESS_NOT_FULL_FCURVES",
  "frame_rate_hz":24,"sample_count_per_side":143,
  "measured_blender_version":bpy.app.version_string,
  "sampled_native_frames":"0..71 inclusive at 0.5 native frame increments",
  "side_labels":"REST_LOCAL_X_PARTITION_NOT_VERIFIED_ANATOMICAL_SIDES",
  "heel_toe_anatomy_verified":False,
  "post_ik_source_rig_verified":False,
  "root_correction_m":None,"independent_visual_review_passed":False,
  "actors":actors,"natural_gait_accepted":False,
  "mvp_accepted":False,"release_authorized":False}
 Path(args.out).write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_D_ACTUAL_24HZ_SHOE_TRACE",json.dumps({
  "source_scene_sha256":args.sha,"blender":bpy.app.version_string,
  "actors":[{"actor":a["actor"],"shoe":a["original_cc0_shoe"],
    "samples_per_side":len(a["sides"]["rest_local_x_negative"]["samples"])} for a in actors],
  "toe_heel_accepted":False,"mvp_accepted":False},sort_keys=True),flush=True)
def main():
 p=argparse.ArgumentParser()
 for name in ("scene","sha","wardrobe","retarget","out"):
  p.add_argument("--"+name,required=True)
 trace_scene(p.parse_args(sys.argv[sys.argv.index("--")+1:]))
if __name__=="__main__":main()
