"""True Blender actual CC0 shoe patch finite-difference response to native five-bone IK target."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from jacobian import jacobian,update
sys.path.insert(0,str(Path(__file__).parent))
from policy import screen,select
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample
def guard(cond,reason):
 if not cond:raise RuntimeError(reason)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def xyz(sample):return [float(sample["xy_m"][0]),float(sample["xy_m"][1]),float(sample["z_m"])]
def tail(rig,side):
 p=rig.pose.bones["foot."+side]
 return rig.matrix_world@p.tail
def get(shoe,part):
 return xyz(stable_sole_sample(shoe)[part])
def main():
 parser=argparse.ArgumentParser()
 for n in ("scene","sha","wardrobe","retarget","trace","correspondence","out"):parser.add_argument("--"+n,required=True)
 a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
 guard(sha(a.scene)==a.sha,"SOURCE_SCENE_SHA")
 sc=bpy.context.scene
 guard(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","PUBLIC_SOURCE_RIGHTS")
 w=json.loads(Path(a.wardrobe).read_text());r=json.loads(Path(a.retarget).read_text())
 t=json.loads(Path(a.trace).read_text());c=json.loads(Path(a.correspondence).read_text())
 guard(r.get("candidate_blend_sha256")==a.sha and r.get("input_scene_sha256")==w.get("blend_sha256"),"ACTUAL_RETARGET_LINEAGE")
 guard(t.get("source_scene_sha256")==a.sha and c.get("source_scene_sha256")==a.sha and c.get("source_trace_sha256")==sha(a.trace),"SOURCE_TRACE_LINEAGE")
 guard(t.get("frame_rate_hz")==24 and t.get("sample_count_per_side")==143,"SOURCE_FPS")
 guard((sc.frame_start,sc.frame_end,sc.render.fps)==(0,71,12),"SOURCE_NATIVE_CLOCK")
 actors=[]
 for item in t["actors"]:
  name=item["actor"];guard(name in ("AsterOriginal","JuniperOriginal"),"NOT_SOURCE_SAFE_ACTOR")
  rig=bpy.data.objects.get(name+"_MPFBRig")
  guard(rig and len(rig.data.bones)==163,"SOURCE_NATIVE_RIG")
  wr=next(z for z in w["characters"] if z["name"]==name)
  shoes=[z for z in wr["garments"] if z["pack"]=="shoes01"]
  guard(len(shoes)==1,"SHOE_ASSET_UNKNOWN")
  shoe=bpy.data.objects.get(shoes[0]["native_object"])
  guard(shoe and any(x.type=="ARMATURE" and x.object==rig for x in shoe.modifiers),"SHOE_NOT_SKINNED")
  mapped=next(z for z in c["actors"] if z["actor"]==name)
  for z in mapped["partitions"]:
   expected="R" if z["rest_local_partition"]=="rest_local_x_negative" else "L"
   guard(z["candidate_rig_side"]["label"]==expected and z["candidate_rig_side"]["dominance"]>.95,"FOOT_SIDE_NOT_MAPPED")
  observations=[]
  for index in (24,48):
   for side,part in (("L","rest_local_x_positive"),("R","rest_local_x_negative")):
    # The native armature world matrix is animated. NEVER freeze it across frames.
    sc.frame_set(0)
    for i in range(index+1):
     sc.frame_set(i//2,subframe=(i%2)*.5)
     measured=get(shoe,part)
    source=item["sides"][part]["samples"][index]
    expected=xyz(source)
    gap=math.dist(measured,expected)
    guard(gap<.0005,"NULL_NATIVE_SOURCE_DRIFT_"+name+"_"+part+"_m_"+str(round(gap,6)))
    foot=rig.pose.bones["foot."+side]
    seq=[x+"."+side for x in ("foot","lowerleg02","lowerleg01","upperleg02","upperleg01")]
    guard(all(rig.data.bones[seq[i]].parent.name==seq[i+1] for i in range(4)),"LEG_CHAIN_INVALID")
    original=tail(rig,side).copy()
    ob=bpy.data.objects.new("N03D_X_ephemeral_"+name+"_"+side,None)
    sc.collection.objects.link(ob)
    constraint=foot.constraints.new("IK")
    constraint.target=ob;constraint.chain_count=5;constraint.iterations=100
    constraint.use_stretch=False;constraint.use_rotation=False;constraint.use_location=True
    try:
     ob.location=original;bpy.context.view_layer.update()
     zero=get(shoe,part)
     step=.002;plus=[];minus=[]
     for axis in range(3):
      e=[0.,0.,0.];e[axis]=step
      ob.location=original+Vector(e);bpy.context.view_layer.update()
      plus.append(get(shoe,part))
      ob.location=original-Vector(e);bpy.context.view_layer.update()
      minus.append(get(shoe,part))
     J=jacobian(plus,minus,step)
     current=[zero[0]-expected[0],zero[1]-expected[1],zero[2]]
     trials=[]
     for radius in (.002,.005,.01):
      solution=update(J,current,.1,radius)
      delta=Vector(solution["target_delta_m"])
      ob.location=original+delta;bpy.context.view_layer.update()
      after=get(shoe,part)
      predicted=[zero[d]+sum(J[d][k]*solution["target_delta_m"][k] for k in range(3)) for d in range(3)]
      assessment=screen(current,[after[0]-expected[0],after[1]-expected[1],after[2]],
        [predicted[0]-expected[0],predicted[1]-expected[1],predicted[2]],
        solution["target_delta_m"],solution["jacobian_frobenius_norm"],radius)
      trials.append({"trust_radius_m":radius,"assessment":assessment,
        "after_true_shoe_xyz_m":after,
        "native_post_probe_ground_penetration_m":round(max(0.,-after[2]),6),
        "native_post_probe_hover_m":round(max(0.,after[2]),6)})
     selected=select(trials)
     observations.append({"frame_sample_24hz":index,"side_rig_label":side,"shoe_part":part,
      "source_null_trace_gap_m":round(gap,7),
      "ik_zero_target_activation_bias_m":round(math.dist(zero,measured),6),
      "base_actual_shoe_xyz_m":measured,"zero_ik_actual_shoe_xyz_m":zero,
      "finite_difference_step_m":step,"native_shoe_jacobian":J,
      "trials":trials,"selection":selected,
      "biological_contact_accepted":False})
    finally:
     foot.constraints.remove(constraint)
     bpy.data.objects.remove(ob,do_unlink=True)
     bpy.context.view_layer.update()
  actors.append({"actor":name,"probes":observations})
 report={"schema":"scp.n03d-z.actual-adaptive-trust-native-sole.v1",
  "source_scene_sha256":a.sha,"source_trace_sha256":sha(a.trace),
  "source_correspondence_sha256":sha(a.correspondence),"source_original_fictional_cc0":True,
  "actors":actors,"blender":bpy.app.version_string,
  "source_action_changed":False,"corrected_action_saved":False,
  "persistent_shoe_material_point_proven":False,"mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_Z_ACTUAL_ADAPTIVE_NATIVE_TRUST",json.dumps({"actors":[{"actor":x["actor"],
  "probes":[{"sample":q["frame_sample_24hz"],"rig_side":q["side_rig_label"],
   "zero_IK_bias_m":q["ik_zero_target_activation_bias_m"],
   "trials":[{"trust":t["trust_radius_m"],"pass_numeric":t["assessment"]["numeric_candidate_admissible"],"reason":t["assessment"]["reason"],"gap_m":t["assessment"]["prediction_gap_m"]} for t in q["trials"]],
   "selected":q["selection"]["chosen_trust_radius_m"],
   "J":q["native_shoe_jacobian"]} for q in x["probes"]]} for x in actors],
 "mvp_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
