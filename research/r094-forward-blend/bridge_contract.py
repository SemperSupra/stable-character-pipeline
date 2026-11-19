"""R094 narrow source-safe version bridge contract; stdlib only."""
import copy
ACTORS=("AsterOriginal","JuniperOriginal")
FRAMES=(0,35,71)
def require(condition,tag):
 if not condition:raise ValueError(tag)
def check_observation(obs):
 require(isinstance(obs,dict) and set(obs)==set(ACTORS),"WRONG_ACTORS")
 for name in ACTORS:
  p=obs[name]
  require(len(p)==3 and [x["frame"] for x in p]==list(FRAMES),"FRAME_SET_OR_ORDER_CHANGED")
  shapes=[x["body"]["sha256"] for x in p]
  require(len(set(shapes))>=2,"STATIC_BODY_NOT_ANIMATED")
  poses=[x["rig_pose_sha256"] for x in p]
  require(len(set(poses))>=2,"STATIC_NATIVE_POSE")
  for sample in p:
   require(sample["native_rig_bones"]==163,"NOT_NATIVE_163_RIG")
   require(sample["body"]["n"]>5000,"EMPTY_NATIVE_BODY")
   clothes=sample["clothes"]
   require(len(clothes)==3,"MISSING_CC0_WARDROBE")
   require(all(v["n"]>100 for v in clothes.values()),"INVALID_CC0_GARMENT")
def compare(baseline,obs,sha):
 require(baseline["schema"]=="scp.r094.blender-4-5-native-scene-baseline.v1","NOT_PINNED_BASELINE")
 require(baseline["blender_version"]=="4.5.16","NOT_4_5_16_SOURCE")
 require(sha==baseline["scene_sha256"],"SAVED_SCENE_SHA_MISMATCH")
 check_observation(baseline["observations"])
 check_observation(obs)
 require(baseline["observations"]==obs,"NATIVE_MESH_POSE_OR_GARMENT_DRIFT")
 return True
