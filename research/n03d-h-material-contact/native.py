"""Native read-only tracking of SAME CC0 shoe material vertices across 24Hz contact windows."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from material import compare_material_ids

def fail(s):raise RuntimeError(s)
def file_hash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rest_groups(obj):
 xs=[float(v.co.x) for v in obj.data.vertices]
 if len(xs)<600 or not all(math.isfinite(x) for x in xs):fail("SHOE_REST_INVALID")
 center=(min(xs)+max(xs))/2
 parts={"rest_local_x_negative":[],"rest_local_x_positive":[]}
 for i,x in enumerate(xs):parts["rest_local_x_negative" if x<center else "rest_local_x_positive"].append(i)
 if min(len(v) for v in parts.values())<80:fail("SHOE_BILATERAL_REST_INVALID")
 return parts
def frame_near_ground(shoe,parts):
 bpy.context.view_layer.update()
 ev=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh()
 try:
  if len(mesh.vertices)!=len(shoe.data.vertices):fail("SHOE_MATERIAL_INDEX_DRIFT")
  values={}
  for label,idx in parts.items():
   samples={}
   for n in idx:
    p=ev.matrix_world @ mesh.vertices[n].co
    if not all(math.isfinite(x) for x in (p.x,p.y,p.z)):fail("WORLD_SHOE_NONFINITE")
    if -.012<=p.z<=.012:samples[n]=(float(p.x),float(p.y))
   values[label]=samples
  return values
 finally:ev.to_mesh_clear()
def main():
 ap=argparse.ArgumentParser()
 for arg in ("scene","sha","wardrobe","retarget","trace","critic","out"):ap.add_argument("--"+arg,required=True)
 args=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
 if file_hash(args.scene)!=args.sha:fail("SOURCE_SCENE_TAMPER")
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":fail("PROTECTED_OR_NON_CC0_ASSET")
 ward=json.loads(Path(args.wardrobe).read_text());record=json.loads(Path(args.retarget).read_text())
 trace=json.loads(Path(args.trace).read_text());critic=json.loads(Path(args.critic).read_text())
 if record.get("candidate_blend_sha256")!=args.sha or record.get("input_scene_sha256")!=ward.get("blend_sha256") or trace.get("source_scene_sha256")!=args.sha or trace.get("source_wardrobe_sha256")!=ward.get("blend_sha256"):fail("SHA_SOURCE_LINEAGE_CHANGED")
 if trace.get("sample_count_per_side")!=143 or trace.get("frame_rate_hz")!=24 or critic.get("schema")!="scp.n03d-g.contact-admission.v1":fail("INDEPENDENT_SOURCE_CRITIC_JOIN_MISSING")
 actors=[]
 for actor in ward["characters"]:
  name=actor["name"]
  rig=bpy.data.objects.get(name+"_MPFBRig")
  if not rig or len(rig.data.bones)!=163:fail("REAL_NATIVE_RIG_LOST")
  shoes=[g for g in actor["garments"] if g["pack"]=="shoes01"]
  if len(shoes)!=1:fail("REAL_CC0_SHOE_ASSET_MISSING")
  shoe=bpy.data.objects.get(shoes[0]["native_object"])
  if not shoe or not any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers):fail("CC0_SHOE_RIG_BINDING_DRIFT")
  parts=rest_groups(shoe)
  rows={name:[] for name in parts}
  previous=None
  for i in range(143):
   scene.frame_set(i//2,subframe=(i%2)*.5)
   current=frame_near_ground(shoe,parts)
   if previous is not None:
    for label in parts:
     stats=compare_material_ids(previous[label],current[label],1/24)
     rows[label].append({"t_end_s":round(i/24,9),**stats})
   previous=current
  verdict={}
  for label,items in rows.items():
   valid=[x for x in items if x["persistent_vertices"]>=2]
   verdict[label]={"intervals_total":len(items),"intervals_with_two_or_more_persistent_contact_vertices":len(valid),
    "intervals_unknown":len(items)-len(valid),
    "highest_material_median_speed_mps":max((x["median_mps"] for x in valid),default=None),
    "highest_material_p95_speed_mps":max((x["p95_mps"] for x in valid),default=None),
    "minimum_persistent_vertices":min((x["persistent_vertices"] for x in valid),default=0),
    "samples":items,"anatomical_side_verified":False}
  actors.append({"actor":name,"shoe":shoes[0]["asset"],"partitions":verdict})
 result={"schema":"scp.n03d-h.persistent-shoe-material-world-contact.v1",
  "source_scene_sha256":args.sha,"source_trace_sha256":file_hash(args.trace),
  "source_critic_sha256":file_hash(args.critic),
  "fps":24,"actors":actors,"status":"MEASURED_MATERIAL_CONTACT_HOLD_PHYSICS",
  "dynamic_bottom_patch_centroid_same_material":False,
  "physical_stance_accepted":False,"mvp_accepted":False,"release_authorized":False}
 Path(args.out).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_H_REAL_PERSISTENT_MATERIAL_SPEED",json.dumps({
  "actors":[{"actor":x["actor"],"shoes":{k:{"intervals":z["intervals_with_two_or_more_persistent_contact_vertices"],
    "max_median_mps":z["highest_material_median_speed_mps"],"max_p95_mps":z["highest_material_p95_speed_mps"]} for k,z in x["partitions"].items()}} for x in actors],
  "mvp_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
