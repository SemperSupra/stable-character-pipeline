"""Read-only actual 5-bone MPFB IK using evaluated CC0 sole support-Z feedback.
Hypothesis test: planted-foot support anchor; no saved corrected animation, stance unknown.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from support import bounded_sole_z,outcome
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample
sys.path.insert(0,str(Path(__file__).parent.parent/"n03c-native-ik"))
from ik_contract import chain,validate_parents

def fail(s):raise RuntimeError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def world_tail(rig,bone):return rig.matrix_world @ rig.pose.bones[bone].tail
def world_root(rig):return rig.matrix_world @ rig.pose.bones["root"].head

def probe_window(rig,shoe,part,side,start=12,end=18):
 foot=rig.pose.bones.get("foot."+side)
 if not foot:fail("SOURCE_FOOT_BONE_UNKNOWN")
 bones=chain(side)
 parent={name:(rig.data.bones[name].parent.name if rig.data.bones.get(name) and rig.data.bones[name].parent else None) for name in bones}
 validate_parents(side,parent)
 sc=bpy.context.scene
 times=[start+i*.5 for i in range((end-start)*2+1)]
 before=[]
 for t in times:
  sc.frame_set(int(t),subframe=t%1);bpy.context.view_layer.update()
  p=stable_sole_sample(shoe)[part]
  before.append({"frame":t,"min_z_m":float(p["z_m"]),"xy_m":list(p["xy_m"]),
   "foot_tail":world_tail(rig,bones[0]).copy(),"root":world_root(rig).copy()})
 initial=before[0]
 correction=bounded_sole_z(initial["min_z_m"])
 target=bpy.data.objects.new("N03D_F2_ephemeral_"+rig.name+"_"+side,None)
 sc.collection.objects.link(target)
 # Fixed-world planted-contact hypothesis: source foot-tail anchor translated ONLY
 # by the minimum required measured shoe support rise, capped at 40mm.
 # This does not assume tail itself contacts the floor.
 position=initial["foot_tail"]+Vector((0.,0.,correction))
 target.location=position
 con=foot.constraints.new("IK")
 con.target=target;con.chain_count=5;con.iterations=100
 con.use_stretch=False;con.use_rotation=False;con.use_location=True
 after=[];max_root=0.;max_tail_target_error=0.
 try:
  for entry in before:
   t=entry["frame"]
   sc.frame_set(int(t),subframe=t%1);bpy.context.view_layer.update()
   s=stable_sole_sample(shoe)[part]
   foot_world=world_tail(rig,bones[0])
   dr=float((world_root(rig)-entry["root"]).length)
   max_root=max(max_root,dr)
   max_tail_target_error=max(max_tail_target_error,float((foot_world-position).length))
   after.append({"frame":t,"min_z_m":float(s["z_m"]),
    "xy_m":list(s["xy_m"]), "root_head_world_drift_m":round(dr,9)})
  valid=outcome([x["min_z_m"] for x in before],[x["min_z_m"] for x in after],max_root,correction)
  # Hard safety: actual root position must stay source; contact solution may fail.
  if max_root>.001:fail("UNEXPECTED_ROOT_DISPLACEMENT")
  return {"source_foot_chain":list(bones),"rest_partition":part,
    "source_rig_side":side,"frames_half_step":[float(v) for v in times],
    "source_shoe_support_z_at_anchor_m":initial["min_z_m"],
    "fixed_world_target_xyz_m":[round(float(x),6) for x in position],
    "bounded_support_z_raise_m":round(correction,6),
    "max_foot_tail_target_error_m":round(max_tail_target_error,6),
    "max_actual_root_drift_m":round(max_root,9),
    "actual_cc0_sole_z_before_after":valid,
    "initial_foot_tail_support_is_not_surface_contact":True,
    "candidate_sole_contact_not_verified":True,
    "anatomical_joint_axes_verified":False,
    "stance_window_is_forced_hypothesis_not_detected_plant":True,
    "physical_gait_accepted":False,"before":before_json(before),
    "after":after}
 finally:
  foot.constraints.remove(con)
  bpy.data.objects.remove(target,do_unlink=True)

def before_json(rows):
 return [{"frame":v["frame"],"min_z_m":v["min_z_m"],
   "xy_m":v["xy_m"]} for v in rows]

def main():
 p=argparse.ArgumentParser()
 for x in ("scene","sha","wardrobe","retarget","trace","correspondence","out"):
  p.add_argument("--"+x,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if sha(a.scene)!=a.sha:fail("SOURCE_SCENE_SHA_INVALID")
 sc=bpy.context.scene
 if sc.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or sc.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":fail("PUBLIC_ORIGINAL_CC0_RIGHTS_NOT_VERIFIED")
 w=json.loads(Path(a.wardrobe).read_text());r=json.loads(Path(a.retarget).read_text())
 tr=json.loads(Path(a.trace).read_text());corr=json.loads(Path(a.correspondence).read_text())
 if r.get("candidate_blend_sha256")!=a.sha or r.get("input_scene_sha256")!=w.get("blend_sha256"):fail("RETARGET_RIGHTS_SOURCE_JOIN")
 if tr.get("source_scene_sha256")!=a.sha or corr.get("source_scene_sha256")!=a.sha or corr.get("source_trace_sha256")!=sha(a.trace):fail("N03D_OBSERVER_CORRESPONDENCE_JOIN")
 if sorted(x["actor"] for x in corr["actors"])!=["AsterOriginal","JuniperOriginal"]:fail("ACTOR_MATCH_FAILURE")
 actors=[]
 for row in corr["actors"]:
  name=row["actor"]
  rig=bpy.data.objects.get(name+"_MPFBRig")
  outfit=next(x for x in w["characters"] if x["name"]==name)
  shoe_row=[x for x in outfit["garments"] if x["pack"]=="shoes01"]
  if not rig or len(rig.data.bones)!=163 or len(shoe_row)!=1:fail("NATIVE_SOURCE_RIG_OR_SHOE_INVALID")
  shoe=bpy.data.objects.get(shoe_row[0]["native_object"])
  if not shoe or not any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers):fail("NATIVE_SHOE_SKIN_DRIFT")
  results=[]
  for partition in row["partitions"]:
   side=partition["candidate_rig_side"]["label"]
   if side not in ("L","R") or partition["candidate_rig_side"]["dominance"]<.95:
    results.append({"rest_partition":partition["rest_local_partition"],"status":"UNKNOWN_UNMAPPED_RIG_SIDE"})
    continue
   results.append(probe_window(rig,shoe,partition["rest_local_partition"],side))
  actors.append({"actor":name,"hypotheses":results})
 output={"schema":"scp.n03d-f2.actual-bounded-support-z-ik.v1",
   "source_blend_sha256":a.sha,"source_correspondence_sha256":sha(a.correspondence),
   "source_trace_sha256":sha(a.trace),
   "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0","blender":bpy.app.version_string,
   "actors":actors,"source_scene_modified":False,
   "source_after_ik_saved":False,"natural_gait_accepted":False,
   "anatomical_side_mapping_accepted":False,
   "all_stance_windows_hypothesis_only":True,"mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(output,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_F2_ACTUAL_5BONE_SOLE_SUPPORT_PROBE",json.dumps({
  "actors":[{"actor":v["actor"],"hypotheses":[{"part":q.get("rest_partition"),"side":q.get("source_rig_side"),
   "support_correction_m":q.get("bounded_support_z_raise_m"),
   "actual_contact":q.get("actual_cc0_sole_z_before_after")} for q in v["hypotheses"]]} for v in actors],
  "mvp_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
