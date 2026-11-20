"""Actual Blender per-material ID Jacobian vs moving support-patch Jacobian."""
import bpy,sys,argparse,json,hashlib,math
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from compare import error,classify
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-y-material"))
from material import select_ids,snapshot
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-x-sole-jacobian"))
from jacobian import jacobian,update
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get_dynamic(shoe,side):
 p=stable_sole_sample(shoe)[side]
 return [float(p["xy_m"][0]),float(p["xy_m"][1]),float(p["z_m"])]
def meshworld(shoe):
 e=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
 try:
  require(len(m.vertices)==len(shoe.data.vertices),"EVALUATED_TOPOLOGY_DRIFT")
  return [tuple(float(v) for v in (e.matrix_world@x.co)) for x in m.vertices]
 finally:e.to_mesh_clear()
def cohort(shoe,part,world):
 xs=[float(v.co.x) for v in shoe.data.vertices];mid=(min(xs)+max(xs))*.5
 candidates=[i for i,x in enumerate(xs) if (x<mid)==(part=="rest_local_x_negative")]
 return select_ids(world,candidates)
def get_fixed(shoe,ids):
 return snapshot(meshworld(shoe),ids)["centroid_xyz_m"]
def main():
 p=argparse.ArgumentParser()
 for k in ("scene","sha","wardrobe","retarget","trace","correspondence","out"):p.add_argument("--"+k,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 require(sha(a.scene)==a.sha,"SOURCE_SCENE_SHA")
 sc=bpy.context.scene
 require(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","SOURCE_NOT_PUBLIC_CC0")
 w=json.loads(Path(a.wardrobe).read_text());r=json.loads(Path(a.retarget).read_text())
 t=json.loads(Path(a.trace).read_text());c=json.loads(Path(a.correspondence).read_text())
 require(r.get("candidate_blend_sha256")==a.sha and r.get("input_scene_sha256")==w.get("blend_sha256"),"SOURCE_MANIFEST_JOIN")
 require(t.get("source_scene_sha256")==a.sha and c.get("source_scene_sha256")==a.sha and c.get("source_trace_sha256")==sha(a.trace),"SOURCE_TRACE_JOIN")
 require(t.get("frame_rate_hz")==24 and t.get("sample_count_per_side")==143,"TIMEBASE_DRIFT")
 require((sc.frame_start,sc.frame_end,sc.render.fps)==(0,71,12),"BLENDER_CLOCK_DRIFT")
 actors=[]
 for item in t["actors"]:
  name=item["actor"];require(name in ("AsterOriginal","JuniperOriginal"),"PROTECTED_CHARACTER")
  rig=bpy.data.objects.get(name+"_MPFBRig")
  require(rig and len(rig.data.bones)==163,"NATIVE_163BONE_RIG")
  wr=next(row for row in w["characters"] if row["name"]==name)
  outfits=[row for row in wr["garments"] if row["pack"]=="shoes01"]
  require(len(outfits)==1,"SHOE_NOT_ADMITTED")
  shoe=bpy.data.objects.get(outfits[0]["native_object"])
  require(shoe and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),"CC0_SHOE_NOT_SKINNED")
  corr=next(row for row in c["actors"] if row["actor"]==name)
  for part in corr["partitions"]:
   rigside="R" if part["rest_local_partition"]=="rest_local_x_negative" else "L"
   require(part["candidate_rig_side"]["label"]==rigside and part["candidate_rig_side"]["dominance"]>.95,"SIDE_UNQUALIFIED")
  cases=[]
  for frame in (24,48):
   for rigside,part in (("L","rest_local_x_positive"),("R","rest_local_x_negative")):
    sc.frame_set(0)
    for i in range(frame+1):
     sc.frame_set(i//2,subframe=(i%2)*.5)
     bpy.context.view_layer.update()
    source=t["actors"][0] if False else item
    trace=source["sides"][part]["samples"][frame]
    original=get_dynamic(shoe,part)
    ground=[float(trace["xy_m"][0]),float(trace["xy_m"][1]),float(trace["z_m"])]
    require(error(original,ground)<.0005,"NULL_ACTUATOR_DRIFT_"+name+"_"+part)
    ids=cohort(shoe,part,meshworld(shoe))
    base_fixed=get_fixed(shoe,ids)
    foot=rig.pose.bones["foot."+rigside]
    chain=[x+"."+rigside for x in ("foot","lowerleg02","lowerleg01","upperleg02","upperleg01")]
    require(all(rig.data.bones[chain[k]].parent.name==chain[k+1] for k in range(4)),"LEG_CHAIN_CHANGED")
    tail=(rig.matrix_world@foot.tail).copy()
    obj=bpy.data.objects.new("N03D_AA_ephemeral_"+name+"_"+rigside,None);sc.collection.objects.link(obj)
    ik=foot.constraints.new("IK");ik.target=obj;ik.chain_count=5;ik.iterations=100
    ik.use_stretch=False;ik.use_rotation=False;ik.use_location=True
    try:
     obj.location=tail;bpy.context.view_layer.update()
     nominal_fixed=get_fixed(shoe,ids)
     nominal_dynamic=get_dynamic(shoe,part)
     plus_f=[];minus_f=[];plus_d=[];minus_d=[];step=.002
     for axis in range(3):
      v=Vector((step if axis==0 else 0,step if axis==1 else 0,step if axis==2 else 0))
      obj.location=tail+v;bpy.context.view_layer.update()
      plus_f.append(get_fixed(shoe,ids));plus_d.append(get_dynamic(shoe,part))
      obj.location=tail-v;bpy.context.view_layer.update()
      minus_f.append(get_fixed(shoe,ids));minus_d.append(get_dynamic(shoe,part))
     fixed_j=jacobian(plus_f,minus_f,step)
     dynamic_j=jacobian(plus_d,minus_d,step)
     source_error=[nominal_fixed[0]-base_fixed[0],nominal_fixed[1]-base_fixed[1],nominal_fixed[2]]
     proposal=update(fixed_j,source_error,.1,.01)
     delta=Vector(proposal["target_delta_m"])
     obj.location=tail+delta;bpy.context.view_layer.update()
     actual_f=get_fixed(shoe,ids);actual_d=get_dynamic(shoe,part)
     predict_f=[nominal_fixed[d]+sum(fixed_j[d][k]*delta[k] for k in range(3)) for d in range(3)]
     predict_d=[nominal_dynamic[d]+sum(dynamic_j[d][k]*delta[k] for k in range(3)) for d in range(3)]
     fgap=error(actual_f,predict_f);dgap=error(actual_d,predict_d)
     cases.append({"sample":frame,"rig_side":rigside,"mesh_part":part,
       "cohort_vertex_count":len(ids),"same_source_mesh_vertex_indices":ids,
       "source_zero_ik_material_mismatch_m":error(nominal_fixed,base_fixed),
       "source_zero_ik_dynamic_mismatch_m":error(nominal_dynamic,original),
       "material_jacobian":fixed_j,"moving_patch_jacobian":dynamic_j,
       "trust_delta_m":list(delta),
       "fixed_material_prediction_error_m":fgap,"moving_patch_prediction_error_m":dgap,
       "comparison":classify(fgap,dgap),
       "after_fixed_material_height_m":actual_f[2],
       "after_dynamic_patch_height_m":actual_d[2],
       "persistent_cohort_not_anatomical_heel_or_toe":True,
       "source_plant_accepted":False})
    finally:
     foot.constraints.remove(ik)
     bpy.data.objects.remove(obj,do_unlink=True)
     bpy.context.view_layer.update()
  actors.append({"actor":name,"probes":cases})
 output={"schema":"scp.n03d-aa.actual-persistent-material-ik-jacobian.v1",
   "source_scene_sha256":a.sha,"source_trace_sha256":sha(a.trace),
   "original_fictional_cc0_only":True,"blender":bpy.app.version_string,
   "actors":actors,"source_action_modified":False,"corrected_blend_saved":False,
   "persistent_ids_only_within_probe":True,"physical_contact_accepted":False,
   "natural_gait_accepted":False,"mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(output,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_AA_PERSISTENT_MATERIAL_IK_JACOBIAN",json.dumps({"actors":[{"actor":x["actor"],
  "probes":[{"frame":p["sample"],"side":p["rig_side"],
    "fixed_gap_m":p["fixed_material_prediction_error_m"],
    "changing_gap_m":p["moving_patch_prediction_error_m"],
    "fixed_more_accurate":p["comparison"]["fixed_material_prediction_more_accurate"]}
    for p in x["probes"]]} for x in actors],
   "contact_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
