"""Compare actual worn CC0 shoes' skinned vertex-group weights and foot-bone geometry.
This is a reversible read-only native source mapping preflight for N03D-F, not IK.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from correspondence import choose_side
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample

def fail(reason):raise RuntimeError(reason)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
FOOT_CHAIN=("foot","lowerleg02","lowerleg01","upperleg02","upperleg01")

def group_partition(shoe):
 xs=[float(v.co.x) for v in shoe.data.vertices]
 if len(xs)<600 or not all(math.isfinite(x) for x in xs) or max(xs)-min(xs)<.05:
  fail("SOURCE_SHOE_MESH_INVALID")
 split=(max(xs)+min(xs))/2
 groups={"rest_local_x_negative":[],"rest_local_x_positive":[]}
 for i,x in enumerate(xs):
  groups["rest_local_x_negative" if x<split else "rest_local_x_positive"].append(i)
 if min(len(v) for v in groups.values())<80:fail("SOURCE_SIDE_CANNOT_PARTITION")
 return groups
def weight_masses(shoe,part):
 group_names={g.index:g.name for g in shoe.vertex_groups}
 results={"L":0.,"R":0.}
 by_bone={}
 total=0.
 for i in part:
  for g in shoe.data.vertices[i].groups:
   name=group_names.get(g.group)
   if name and (name.endswith(".L") or name.endswith(".R")):
    family=name[:-2]
    if family not in FOOT_CHAIN and not family.startswith("toe"):
     continue
    side=name[-1]
    value=float(g.weight)
    if not math.isfinite(value) or value<0:fail("SOURCE_VERTEX_WEIGHT_BAD")
    results[side]+=value
    by_bone[name]=by_bone.get(name,0.)+value
    total+=value
 return results,by_bone,total
def main():
 p=argparse.ArgumentParser()
 for s in ("scene","sha","wardrobe","retarget","trace","out"):p.add_argument("--"+s,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if sha(a.scene)!=a.sha:fail("BLEND_HASH_CHANGED")
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or sc.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":fail("SOURCE_RIGHTS_CHANGED")
 ward=json.loads(Path(a.wardrobe).read_text())
 rec=json.loads(Path(a.retarget).read_text())
 observed=json.loads(Path(a.trace).read_text())
 if observed.get("schema")!="scp.n03d-g.evaluated-foot-contact-observer.v1" or observed.get("source_scene_sha256")!=a.sha or observed.get("source_wardrobe_sha256")!=ward.get("blend_sha256"):fail("INDEPENDENT_TRACE_SOURCE_JOIN")
 if rec.get("candidate_blend_sha256")!=a.sha or rec.get("input_scene_sha256")!=ward["blend_sha256"]:fail("SOURCE_SCENE_OR_RECORDING_DRIFT")
 actors=[]
 for actor in ward["characters"]:
  name=actor["name"]
  rig=bpy.data.objects.get(name+"_MPFBRig")
  if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=163:fail("ACTUAL_MPF_RIG_MISSING")
  shoe_rec=[g for g in actor["garments"] if g["pack"]=="shoes01"]
  if len(shoe_rec)!=1:fail("ACTUAL_SHOE_SOURCE_NOT_SINGLE")
  shoe=bpy.data.objects.get(shoe_rec[0]["native_object"])
  if shoe is None or not any(x.type=="ARMATURE" and x.object==rig for x in shoe.modifiers):fail("SOURCE_SHOE_RIG_ATTACHMENT_MISSING")
  for side in ("L","R"):
   for bone in FOOT_CHAIN:
    if rig.pose.bones.get(bone+"."+side) is None:fail("ACTUAL_FIVE_BONE_CHAIN_CHANGED")
  partitions=group_partition(shoe)
  results=[]
  for part,ids in partitions.items():
   masses,by_bone,total=weight_masses(shoe,ids)
   choice=choose_side(masses)
   frames=[]
   for frame in (0,12,35,60,71):
    sc.frame_set(frame);bpy.context.view_layer.update()
    sole=stable_sole_sample(shoe)[part]
    center=Vector((sole["xy_m"][0],sole["xy_m"][1],sole["z_m"]))
    foot_world={}
    for side in ("L","R"):
     world=rig.matrix_world @ rig.pose.bones["foot."+side].tail
     foot_world[side]=world
    distances={side:round(float((foot_world[side]-center).length),6) for side in ("L","R")}
    offset=None
    if choice["label"] in ("L","R"):
     d=foot_world[choice["label"]]-center
     offset=[round(float(x),6) for x in d]
    frames.append({"frame":frame,"source_sole_world_m":[round(float(x),6) for x in center],
     "distance_to_foot_tail_m":distances,"source_sole_to_chosen_foot_tail_offset_m":offset})
   positional=""
   max_offset_drift=None
   label=choice["label"]
   if label in ("L","R"):
    positional=sum(1 for row in frames if row["distance_to_foot_tail_m"][label]+.01<row["distance_to_foot_tail_m"]["R" if label=="L" else "L"])
    offsets=[row["source_sole_to_chosen_foot_tail_offset_m"] for row in frames]
    max_offset_drift=max(math.dist(o,offsets[0]) for o in offsets)
   results.append({"rest_local_partition":part,"source_shoe_vertices":len(ids),
     "weighted_lower_limb_mass":{k:round(v,6) for k,v in masses.items()},
     "five_bone_and_toe_group_weights":{k:round(v,6) for k,v in sorted(by_bone.items())},
     "candidate_rig_side":choice,"samples":frames,
     "weight_to_geometry_consistent_frames":positional,
     "max_sole_to_foot_tail_offset_drift_m":round(max_offset_drift,6) if max_offset_drift is not None else None,
     "anatomical_foot_side_accepted":False,"sole_target_ik_accepted":False})
  actors.append({"actor":name,"shoe":shoe_rec[0]["asset"],"native_163_bone_source_rig":True,
   "partitions":results})
 status="MEASURED_SIDE_INFLUENCE_WITHOUT_CONTACT_IK"
 report={"schema":"scp.n03d-f1.native-shoe-foot-weights.v1","status":status,
  "source_scene_sha256":a.sha,"source_trace_sha256":sha(a.trace),
  "measured_blender_version":bpy.app.version_string,
  "foot_chain":list(FOOT_CHAIN),
  "actors":actors,"source_wardrobe_cc0":True,
  "anatomical_side_verified":False,"rig_joint_axes_calibrated":False,
  "physically_valid_foot_support_anchor":False,"gait_contact_accepted":False,
  "mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_F1_ACTUAL_SOURCE_SHOE_WEIGHTS",json.dumps({
  "scene_sha256":a.sha,"actors":[{"actor":x["actor"],"shoe":x["shoe"],"partition_side_candidates":[y["candidate_rig_side"] for y in x["partitions"]]} for x in actors],
  "anatomical_side_verified":False,"natural_gait_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
