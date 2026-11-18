"""R087 Go/Blender neutral chain QA: source-safe rig anatomy is not automatically human joint truth."""
import math
def finite_vec(v):
 return isinstance(v,list) and len(v)==3 and all(type(x) in (int,float) and math.isfinite(x) for x in v)
def lineage(bones,name,limit=32):
 out=[];seen=set()
 for _ in range(limit):
  if name is None:return out
  if name in seen:raise ValueError("RIG_PARENT_CYCLE")
  if name not in bones:raise ValueError("RIG_PARENT_ABSENT")
  seen.add(name);out.append(name);name=bones[name]["parent"]
 raise ValueError("RIG_PARENT_OVERDEPTH")
def check_side(bones,side):
 names=["upperleg01."+side,"lowerleg01."+side,"foot."+side]
 if not all(n in bones for n in names):raise ValueError("REQUIRED_LEG_BONE_MISSING")
 for n in names:
  row=bones[n]
  if not finite_vec(row["head"]) or not finite_vec(row["tail"]):raise ValueError("BAD_JOINT_COORDINATE")
  if type(row["length"]) not in (int,float) or not math.isfinite(row["length"]) or row["length"]<=1e-6:raise ValueError("BAD_RIG_BONE_LENGTH")
 foot_to_root=lineage(bones,names[2])
 valid=all(n in foot_to_root for n in names) and foot_to_root.index(names[2])<foot_to_root.index(names[1])<foot_to_root.index(names[0])
 return {"bone_names":names,"chain_to_root":foot_to_root[:20],"native_hierarchy_contiguous":valid,
         "status":"STRUCTURAL_CHAIN_CANDIDATE_NOT_ANATOMICAL_IK" if valid else "HOLD_RIG_CHAIN_HIERARCHY",
         "true_joint_centres_accepted":False,"contact_ik_accepted":False}
