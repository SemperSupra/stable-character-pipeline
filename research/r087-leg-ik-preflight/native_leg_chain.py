"""R087 actual Blender/MPFB 163-bone leg chain rig-control preflight.
No synthetic replacement for source rig; no anatomical joint centre acceptance.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from ik_contract import check_side,finite_vec
def fail(code):print("R087_NATIVE_RED",code,flush=True);raise RuntimeError(code)
def digest(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for buf in iter(lambda:f.read(1<<20),b""):h.update(buf)
 return h.hexdigest()
def xyz(v):return [round(float(v[i]),9) for i in range(3)]
def rig_bones(rig):
 result={}
 for b in rig.data.bones:
  result[b.name]={"parent":b.parent.name if b.parent else None,
    "head":xyz(b.head_local),"tail":xyz(b.tail_local),
    "length":float(b.length),"roll_rad":float(b.matrix_local.to_euler().z),
    "use_deform":bool(b.use_deform),"connected_to_parent":bool(b.use_connect)}
 return result
def witness(a):
 if digest(a.scene)!=a.sha:fail("PINNED_SCENE_SHA_UNVERIFIED")
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0":fail("PROTECTED_SOURCE_NOT_ADMITTED")
 if (sc.frame_start,sc.frame_end,sc.render.fps)!=(0,71,12):fail("ORIGINAL_FRAME_CLOCK_DRIFT")
 actors=[]
 for name in ("AsterOriginal","JuniperOriginal"):
  rig=bpy.data.objects.get(name+"_MPFBRig")
  body=bpy.data.objects.get(name+"_MPFBBody")
  if rig is None or body is None or rig.type!="ARMATURE" or len(rig.data.bones)!=163:fail("NATIVE_RIG_NOT_163")
  if not any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers):fail("NATIVE_SKIN_RIG_LINK_LOST")
  bones=rig_bones(rig)
  sides=[]
  for side in ("L","R"):
   info=check_side(bones,side)
   samples=[]
   for frame in (0,18,35,53,71):
    sc.frame_set(frame)
    pose=[]
    for bn in info["bone_names"]:
     p=rig.pose.bones.get(bn)
     if not p:fail("POSE_BONE_NOT_FOUND")
     h=xyz(rig.matrix_world @ p.head)
     t=xyz(rig.matrix_world @ p.tail)
     if not finite_vec(h) or not finite_vec(t):fail("INVALID_POSE_JOINT_TRANSFORM")
     pose.append({"name":bn,"head_world_m":h,"tail_world_m":t})
    samples.append({"frame":frame,"native_pose":pose})
   info.update({"side_label":side,"side_is_authoritative_subject_left_right":False,
                "native_pose_samples":samples,
                "source_ik_pole_accepted":False,"physical_anatomy_accepted":False})
   sides.append(info)
  actors.append({"actor":name,"native_rig_bone_count":len(bones),
      "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0","leg_hierarchy":sides,
      "independent_anatomical_joint_centres_measured":False})
 receipt={"schema":"scp.r087.actual-mpfb-leg-ik-preflight.v1","source_scene_sha256":a.sha,
  "actors":actors,"status":"MEASURED_NATIVE_BONE_HIERARCHY_HOLD_JOINT_ANATOMY",
  "rig_to_ground_accepted":False,"contact_ik_accepted":False,"natural_gait_accepted":False,
  "protected_subject_identity_accepted":False,"mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(receipt,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("R087_NATIVE_LEG_CHAIN",json.dumps({"source":a.sha,"actors":[{"actor":x["actor"],"hierarchy":[{"side":y["side_label"],"state":y["status"],"chain":y["chain_to_root"]} for y in x["leg_hierarchy"]]} for x in actors]},sort_keys=True))
def parse():
 p=argparse.ArgumentParser();p.add_argument("--scene",required=True);p.add_argument("--sha",required=True);p.add_argument("--out",required=True)
 return p.parse_args(sys.argv[sys.argv.index("--")+1:])
if __name__=="__main__":
 try:witness(parse())
 except (OSError,ValueError,TypeError,RuntimeError,KeyError) as e:
  print("R087_FAIL_CLOSED",repr(e),file=sys.stderr);sys.exit(12)
