"""Source-safe actual Blender armature world root plus five-bone temporary IK.
Compare V surrogate predictions with observed skinned CC0 shoe mesh; never save rig.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-v-joint-feasibility"))
from solver import solve,SIDES
sys.path.insert(0,str(Path(__file__).parent))
from boundary import validate
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample
def guard(x,reason):
 if not x:raise RuntimeError(reason)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def worldbone(rig,name,tail=False):
 bone=rig.pose.bones[name]
 return rig.matrix_world@(bone.tail if tail else bone.head)
def shoe_xyz(sample):return [float(sample["xy_m"][0]),float(sample["xy_m"][1]),float(sample["z_m"])]
def validate_chain(rig,side):
 chain=[x+"."+side for x in ("foot","lowerleg02","lowerleg01","upperleg02","upperleg01")]
 guard(all(rig.data.bones[chain[i]].parent.name==chain[i+1] for i in range(4)),"NATIVE_FIVE_LINK_CHAIN_DRIFT")
 guard(rig.data.bones[chain[-1]].parent.name=="pelvis."+side,"SOURCE_PELVIS_DRIFT")
def main():
 parser=argparse.ArgumentParser()
 for k in ("scene","sha","wardrobe","retarget","trace","correspondence","out"):parser.add_argument("--"+k,required=True)
 a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
 guard(sha(a.scene)==a.sha,"SOURCE_SCENE_HASH")
 sc=bpy.context.scene
 guard(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","PROTECTED_OR_NON_CC0")
 ward=json.loads(Path(a.wardrobe).read_text());rec=json.loads(Path(a.retarget).read_text())
 trace=json.loads(Path(a.trace).read_text());corr=json.loads(Path(a.correspondence).read_text())
 guard(rec.get("candidate_blend_sha256")==a.sha and rec.get("input_scene_sha256")==ward.get("blend_sha256"),"SOURCE_WARDROBE_SHA")
 guard(trace.get("source_scene_sha256")==a.sha and corr.get("source_scene_sha256")==a.sha and corr.get("source_trace_sha256")==sha(a.trace),"SOURCE_TRACE_JOIN")
 guard(trace.get("frame_rate_hz")==24 and trace.get("sample_count_per_side")==143,"SOURCE_CLOCK")
 guard((sc.frame_start,sc.frame_end,sc.render.fps)==(0,71,12),"ACTION_TIMEBASE")
 actors=[]
 for person in trace["actors"]:
  name=person["actor"]
  guard(name in ("AsterOriginal","JuniperOriginal"),"PROTECTED_SOURCE_NAME")
  rig=bpy.data.objects.get(name+"_MPFBRig")
  guard(rig and len(rig.data.bones)==163,"NATIVE_163BONE_RIG")
  row=next(x for x in ward["characters"] if x["name"]==name)
  shoes=[x for x in row["garments"] if x["pack"]=="shoes01"]
  guard(len(shoes)==1,"SHOE_SOURCE_UNKNOWN")
  shoe=bpy.data.objects.get(shoes[0]["native_object"])
  guard(shoe and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),"SKINNED_SHOE_MISSING")
  mapping=next(x for x in corr["actors"] if x["actor"]==name)
  for part in mapping["partitions"]:
   label="R" if part["rest_local_partition"]=="rest_local_x_negative" else "L"
   guard(part["candidate_rig_side"]["label"]==label and part["candidate_rig_side"]["dominance"]>.95,"SHOE_RIG_SIDE_MAPPING_UNVERIFIED")
  for side in ("L","R"):validate_chain(rig,side)
  original=rig.matrix_world.copy()
  windows=[]
  for start in (24,48):
   points={s:[[float(q["xy_m"][0]),float(q["xy_m"][1]),float(q["z_m"])] for q in person["sides"][s]["samples"][start:start+4]] for s in SIDES}
   baseline=[]
   for k in range(4):
    sample=start+k
    sc.frame_set(sample//2,subframe=(sample%2)*.5)
    rig.matrix_world=original.copy();bpy.context.view_layer.update()
    baseline.append({"sole":stable_sole_sample(shoe),
      "hip":worldbone(rig,"pelvis.L").lerp(worldbone(rig,"pelvis.R"),.5).copy(),
      "tails":{side:worldbone(rig,"foot."+side,True).copy() for side in ("L","R")}})
   outcomes=[]
   for mode in ("root_only","foot_only","joint"):
    result=solve(points,mode);validate(result)
    created=[];constraints=[]
    try:
     for side in ("L","R"):
      obj=bpy.data.objects.new("N03D_W_ephemeral_"+name+"_"+side,None)
      sc.collection.objects.link(obj);created.append(obj)
      foot=rig.pose.bones["foot."+side]
      constraint=foot.constraints.new("IK")
      constraint.target=obj;constraint.chain_count=5;constraint.iterations=100
      constraint.use_stretch=False;constraint.use_location=True;constraint.use_rotation=False
      constraints.append((foot,constraint))
     observations=[]
     for k in range(4):
      sample=start+k
      sc.frame_set(sample//2,subframe=(sample%2)*.5)
      root=Vector(result["root_corrections_m"][k])
      rig.matrix_world=Matrix.Translation(root) @ original
      for side,obj in zip(("L","R"),created):
       part="rest_local_x_positive" if side=="L" else "rest_local_x_negative"
       foot=Vector(result["foot_corrections_m"][part][k])
       obj.location=baseline[k]["tails"][side]+root+foot
      bpy.context.view_layer.update()
      observed=stable_sole_sample(shoe)
      hip=worldbone(rig,"pelvis.L").lerp(worldbone(rig,"pelvis.R"),.5)
      witness={"sample_index":sample,"measured_pelvis_drift_m":round(float((hip-baseline[k]["hip"]).length),6),"parts":{}}
      for part in SIDES:
       now=shoe_xyz(observed[part]);orig=points[part][k]
       predicted=[orig[d]+result["root_corrections_m"][k][d]+result["foot_corrections_m"][part][k][d] for d in range(3)]
       anchor=points[part][0]
       witness["parts"][part]={"source_height_m":round(float(baseline[k]["sole"][part]["z_m"]),6),
        "actual_skinned_shoe_height_m":round(now[2],6),
        "actual_shoe_to_anchor_xy_error_m":round(math.hypot(now[0]-anchor[0],now[1]-anchor[1]),6),
        "linear_prediction_to_native_mesh_error_m":round(math.dist(now,predicted),6),
        "persistent_material_vertex_contact_proven":False}
      observations.append(witness)
     outcomes.append({"mode":mode,"surrogate_final_objective":result["objective_final"],
       "source_max_sole_penetration_after_true_ik_m":round(max(0.,-min(row["parts"][s]["actual_skinned_shoe_height_m"] for row in observations for s in SIDES)),6),
       "largest_linear_to_actual_mesh_error_m":round(max(row["parts"][s]["linear_prediction_to_native_mesh_error_m"] for row in observations for s in SIDES),6),
       "samples":observations,"physical_stance_accepted":False})
    finally:
     for foot,constraint in constraints:foot.constraints.remove(constraint)
     for obj in created:bpy.data.objects.remove(obj,do_unlink=True)
     rig.matrix_world=original.copy()
     bpy.context.view_layer.update()
   windows.append({"start_24hz":start,"outcomes":outcomes})
  actors.append({"actor":name,"windows":windows})
  rig.matrix_world=original.copy()
 report={"schema":"scp.n03d-w.actual-5bone-ik-world-root-cc0-shoe-witness.v1",
  "source_scene_sha256":a.sha,"source_trace_sha256":sha(a.trace),
  "source_correspondence_sha256":sha(a.correspondence),"actors":actors,
  "blender":bpy.app.version_string,"source_original_fictional_cc0":True,
  "source_action_modified":False,"corrected_action_saved":False,
  "persistent_material_contact_proven":False,"anatomical_heel_toe_accepted":False,
  "natural_gait_accepted":False,"mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_W_TRUE_NATIVE_SHOE_WITNESS",json.dumps({"actors":[{"actor":a["actor"],"windows":[{"start":w["start_24hz"],
  "modes":[{"mode":m["mode"],"actual_max_penetration":m["source_max_sole_penetration_after_true_ik_m"],
  "model_mesh_disagreement":m["largest_linear_to_actual_mesh_error_m"]} for m in w["outcomes"]]} for w in a["windows"]]} for a in actors],
  "mvp_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
