"""R089 actual pinned Diffeomorphic BVH->MPFB Blender operator execution.
Conservatively fail on no native keys/geometry change; no contact or visual acceptance.
"""
import argparse, hashlib, json, math, struct, sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,SOURCES,SOURCE_COMMIT

PLUGIN_COMMIT="a4f2a394901d043457a9426f0d9e2ade9cda702c"

def abort(msg):raise RuntimeError(msg)
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def observed(body):
 bpy.context.view_layer.update()
 ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 try:
  h=hashlib.sha256()
  for v in mesh.vertices:h.update(struct.pack("<3f",v.co.x,v.co.y,v.co.z))
  return {"sha256":h.hexdigest(),"vertices":len(mesh.vertices)}
 finally:ev.to_mesh_clear()
def pose_fingerprint(rig):
 h=hashlib.sha256()
 for bone in rig.pose.bones:
  for row in bone.matrix:
   for x in row:h.update(struct.pack("<f",float(x)))
 return h.hexdigest()
def source_clip(src,out):
 data=Path(src).read_bytes()
 if Path(src).name!="Neutral_FW.bvh" or git_blob_sha(data)!=SOURCES["Neutral_FW.bvh"]:abort("FORGED_100STYLE_BVH")
 bvh=parse_bvh(data)
 if bvh["count"]!=2400:abort("UNEXPECTED_REAL_BVH_DURATION")
 lines=data.decode("ascii").splitlines()
 try: idx=lines.index("MOTION")
 except ValueError:abort("MISSING_BVH_HEADER")
 head=lines[:idx]; f=lines[idx+3:]
 if len(f)!=bvh["count"]:abort("SOURCE_FRAME_COUNT_MISMATCH")
 # Derived, bounded 1.2s window of actual measured source keys, not synthesized animation.
 clipped="\n".join(head+["MOTION","Frames: 72",lines[idx+2]]+f[120:192])+"\n"
 Path(out).write_text(clipped)
 if parse_bvh(clipped.encode())["count"]!=72:abort("CLIP_EXTRACTION_CHANGED_HIERARCHY")
 return {"original_bvh_sha256":digest(src),"candidate_bvh_sha256":digest(out),
         "source_frames":[120,191],"frames":72,"source_fps":round(1/bvh["frame_time"],6)}

def build(args):
 if digest(args.scene)!=args.sha:abort("SCENE_SOURCE_SHA_DRIFT")
 if bpy.context.scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0":abort("PROTECTED_ASSET_IN_PUBLIC_RUNNER")
 import addon_utils
 module="bl_ext.user_default.retarget_bvh"
 addon_utils.enable(module,default_set=False,persistent=False)
 if not addon_utils.check(module)[1]:abort("OFFICIAL_PINNED_RETARGETER_NOT_ENABLED")
 from importlib import import_module
 vendor=import_module(module)
 vendor.setSilentMode(True)
 from bl_ext.user_default.retarget_bvh.bsettings import BD
 from bl_ext.user_default.retarget_bvh.utils import mcpRna
 if not hasattr(bpy.ops.mcp,"load_and_retarget"):abort("REAL_VENDOR_RETARGET_OPERATOR_MISSING")
 src=source_clip(args.source,args.clip)
 actors=[]
 scene=bpy.context.scene
 for name in ("AsterOriginal","JuniperOriginal"):
  rig=bpy.data.objects.get(name+"_MPFBRig")
  body=bpy.data.objects.get(name+"_MPFBBody")
  if rig is None or body is None or len(rig.data.bones)!=163:abort("ACTUAL_NATIVE_MPF_RIG_MISSING")
  bpy.ops.object.select_all(action="DESELECT")
  rig.hide_set(False)
  rig.select_set(True);bpy.context.view_layer.objects.active=rig
  # Enforce publisher-provided MakeHuman mapping; auto rig recognition chose
  # "breast.R" as shoulder and silently returned FINISHED with a vendor error.
  BD.ensureInited(scene)
  BD.ensureTargetInited(scene)
  mcpRna(scene).TargetRig="MakeHuman"
  mcpRna(scene).TargetTPose="Default"
  prior_action=rig.animation_data.action if rig.animation_data else None
  # Third-party operator may return FINISHED even after internal MocapError.
  out=bpy.ops.mcp.load_and_retarget(
   filepath=str(Path(args.clip).resolve()),useAllFrames=False,startFrame=1,endFrame=72,
   useNLA=False,useBendPositive=False,useAutoTarget=False,
   useDefaultSS=True,useSimplify=False,useTimeScale=False)
  if "FINISHED" not in out:abort("THIRD_PARTY_OPERATOR_NOT_FINISHED_"+name)
  vendor_message=vendor.getErrorMessage()
  if vendor_message.strip()!="BVH file(s) retargeted":abort("THIRD_PARTY_REPORTED_ERROR_"+name+"_"+vendor_message)
  if rig.animation_data is None or rig.animation_data.action is None:abort("NO_RETARGETED_NATIVE_ACTION_"+name)
  if rig.animation_data.action==prior_action:abort("REUSED_OLD_ACTION_FALSE_POSITIVE_"+name)
  action=rig.animation_data.action
  first,last=tuple(float(x) for x in action.frame_range)
  expected_duration=(src["frames"]-1)/src["source_fps"]
  actual_duration=(last-first)/12.0
  if not math.isfinite(actual_duration) or not 0.25<actual_duration<2.0:abort("RETARGETED_ACTION_CLOCK_INVALID_"+name)
  if abs(actual_duration-expected_duration)>0.12:abort("RETARGETED_CLOCK_MISMATCH_"+name)
  start=int(round(first));end=int(round(last))
  if start<0 or end<=start or end>32:abort("RETARGETED_FRAME_RANGE_INVALID_"+name)
  seen=[]
  for frame in (start,(start+end)//2,end):
   scene.frame_set(frame)
   data=observed(body)
   if data["vertices"]<10000:abort("NATIVE_MPF_BODY_EVALUATION_MISSING")
   seen.append({"frame":frame,"evaluated_body":data,"rig_pose_sha256":pose_fingerprint(rig)})
  if len(set(x["evaluated_body"]["sha256"] for x in seen))<2:abort("RETARGETED_RIG_BODY_NOT_MOVING_"+name)
  if len(set(x["rig_pose_sha256"] for x in seen))<2:abort("RETARGET_RIG_HAS_NO_POSE_CHANGES_"+name)
  actors.append({"actor":name,"native_rig_bones":len(rig.data.bones),"native_action_name":action.name,
      "source_duration_seconds":round(expected_duration,6),
      "target_action_frame_range":[round(first,3),round(last,3)],
      "target_action_duration_seconds":round(actual_duration,6),
      "samples":seen,"real_animated_target_geometry":True,"foot_contact_accepted":False})
 if abs(actors[0]["target_action_frame_range"][1]-actors[1]["target_action_frame_range"][1])>1:abort("TWO_ACTOR_CLOCK_DIVERGENCE")
 scene.frame_start=int(round(actors[0]["target_action_frame_range"][0]))
 scene.frame_end=int(round(actors[0]["target_action_frame_range"][1]))
 candidate=Path(args.out).with_suffix(".blend")
 bpy.ops.wm.save_as_mainfile(filepath=str(candidate.resolve()))
 result={"schema":"scp.r089.real-thirdparty-mpfb-retarget.v1",
  "status":"NATIVE_REAL_RECORDED_INPUT_RETARGETED_STRUCTURAL_ONLY_HOLD_CONTACT",
  "input_scene_sha256":args.sha,"candidate_blend_sha256":digest(candidate),
  "plugin_git_commit":PLUGIN_COMMIT,"plugin_license":"GPL-2.0-or-later tool code, runner-only",
  "motion_git_commit":SOURCE_COMMIT,"motion_source_blob_sha1":SOURCES["Neutral_FW.bvh"],
  "source":src,"actors":actors,"full_sole_contact_accepted":False,"visual_naturalness_accepted":False,
  "protected_identity_accepted":False,"mvp_accepted":False,"release_authorized":False}
 Path(args.out).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("R089_NATIVE_RETARGET_PASS_NARROW",json.dumps(result,sort_keys=True),flush=True)

def verify(args):
 r=json.loads(Path(args.out).read_text())
 scene=Path(args.out).with_suffix(".blend")
 if digest(scene)!=r["candidate_blend_sha256"]:abort("SAVED_RETARGET_SCENE_TAMPERED")
 if len(r["actors"])!=2:abort("MISSING_REPLAYED_CHARACTER")
 for actor in r["actors"]:
  body=bpy.data.objects.get(actor["actor"]+"_MPFBBody")
  rig=bpy.data.objects.get(actor["actor"]+"_MPFBRig")
  if not body or not rig or len(rig.data.bones)!=163:abort("REOPEN_LOST_ACTOR")
  for sample in actor["samples"]:
   bpy.context.scene.frame_set(sample["frame"])
   if observed(body)!=sample["evaluated_body"]:abort("REOPEN_CHANGED_SKIN_"+actor["actor"])
   if pose_fingerprint(rig)!=sample["rig_pose_sha256"]:abort("REOPEN_CHANGED_POSE_"+actor["actor"])
 print("R089_INDEPENDENT_FRESH_PROCESS_PASS_NARROW",r["candidate_blend_sha256"],flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--stage",choices=("build","verify"),required=True)
 for n in ("scene","sha","source","clip","out"):p.add_argument("--"+n,default="")
 args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if args.stage=="build":build(args)
 else:verify(args)
if __name__=="__main__":main()
