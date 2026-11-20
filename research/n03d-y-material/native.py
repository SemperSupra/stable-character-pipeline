"""Track identical original shoe mesh vertices across true 24Hz Blender evaluations."""
import bpy,argparse,hashlib,json,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from material import select_ids,snapshot,stats,overlap
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample
SIDES=("rest_local_x_negative","rest_local_x_positive")
def check(x,why):
 if not x:raise RuntimeError(why)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(shoe):
 evaluated=shoe.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=evaluated.to_mesh()
 try:
  check(len(mesh.vertices)==len(shoe.data.vertices),"MESH_TOPOLOGY_CHANGED")
  return [tuple(float(x) for x in (evaluated.matrix_world@v.co)) for v in mesh.vertices]
 finally:evaluated.to_mesh_clear()
def sideids(shoe):
 xs=[v.co.x for v in shoe.data.vertices]
 split=(min(xs)+max(xs))*.5
 return {SIDES[0]:[i for i,x in enumerate(xs) if x<split],SIDES[1]:[i for i,x in enumerate(xs) if x>=split]}
def dynamic_indices(mesh,ids):
 return select_ids(mesh,ids)
def main():
 p=argparse.ArgumentParser()
 for k in ("scene","sha","wardrobe","retarget","trace","out"):p.add_argument("--"+k,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 check(sha(a.scene)==a.sha,"SOURCE_SCENE_SHA")
 sc=bpy.context.scene
 check(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","RIGHTS_SOURCE_INVALID")
 w=json.loads(Path(a.wardrobe).read_text());r=json.loads(Path(a.retarget).read_text());t=json.loads(Path(a.trace).read_text())
 check(r.get("candidate_blend_sha256")==a.sha and r.get("input_scene_sha256")==w.get("blend_sha256") and t.get("source_scene_sha256")==a.sha,"SOURCE_JOIN")
 check(t.get("schema")=="scp.n03d-g.evaluated-foot-contact-observer.v1" and t.get("frame_rate_hz")==24 and t.get("sample_count_per_side")==143,"SOURCE_TRACE_CLOCK")
 actors=[]
 for person in t["actors"]:
  name=person["actor"];check(name in ("AsterOriginal","JuniperOriginal"),"NOT_PUBLIC_ORIGINAL")
  rig=bpy.data.objects.get(name+"_MPFBRig");check(rig and len(rig.data.bones)==163,"RIG_163_MISSING")
  wr=next(x for x in w["characters"] if x["name"]==name)
  shoe=bpy.data.objects.get(next(x["native_object"] for x in wr["garments"] if x["pack"]=="shoes01"))
  check(shoe and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),"SOURCE_SKINNED_SHOE")
  parts=sideids(shoe);windows=[]
  # Replay sequentially once. The source armature world matrix is animated.
  sc.frame_set(0)
  for i in range(60):
   sc.frame_set(i//2,subframe=(i%2)*.5)
   bpy.context.view_layer.update()
   geom=rows(shoe)
   if i not in range(24,36) and i not in range(48,60):continue
   old=stable_sole_sample(shoe)
   witnesses={}
   for side in SIDES:
    source=person["sides"][side]["samples"][i]
    delta=math.dist([old[side]["xy_m"][0],old[side]["xy_m"][1],old[side]["z_m"]],
        [source["xy_m"][0],source["xy_m"][1],source["z_m"]])
    check(delta<.0005,"SOURCE_NULL_TRACE_MISMATCH_"+name+"_"+side+"_"+str(i))
    indices=dynamic_indices(geom,parts[side])
    witnesses[side]={"dynamic_indices":indices,"mesh":geom}
   windows.append({"index":i,"witnesses":witnesses})
  groups=[]
  for start in (24,48):
   current=[q for q in windows if start<=q["index"]<start+12]
   check(len(current)==12,"WINDOW_SAMPLE_DRIFT")
   sides={}
   for side in SIDES:
    initial=current[0]["witnesses"][side]["dynamic_indices"]
    fixed=[snapshot(q["witnesses"][side]["mesh"],initial) for q in current]
    changed=[q["witnesses"][side]["dynamic_indices"] for q in current]
    sides[side]={"persistent_material_vertex_ids":initial,
      "persistent_sample_count":len(fixed),
      "tracked_material_stats":stats(fixed,1/24),
      "support_index_overlap_first_last":overlap(initial,changed[-1]),
      "minimum_support_index_overlap":min(overlap(initial,z) for z in changed),
      "support_patch_switching_detected":any(z!=initial for z in changed),
      "dynamic_support_ids_are_not_persistent_material":True,
      "shoe_rig_part_is_not_verified_heel_or_toe":True,
      "per_sample_tracked":fixed}
   groups.append({"start_24hz":start,"sides":sides})
  actors.append({"actor":name,"windows":groups})
 out={"schema":"scp.n03d-y.persistently-identified-skinned-shoe-vertices.v1",
  "source_scene_sha256":a.sha,"source_trace_sha256":sha(a.trace),
  "source_class":"ORIGINAL_FICTIONAL_CC0","actors":actors,
  "source_100style_sha256":t["source_100style_sha256"],
  "blender":bpy.app.version_string,"source_motion_changed":False,
  "material_ids_persist_within_window_only":True,
  "plant_phase_measured":False,"physical_contact_accepted":False,"mvp_accepted":False}
 Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_Y_TRUE_PERSISTENT_SHOE_MATERIAL",json.dumps({"actors":[{"actor":a["actor"],"windows":[{"start":w["start_24hz"],
   "sides":{s:{"count":v["persistent_sample_count"],"speed":v["tracked_material_stats"],
    "support_overlap":v["minimum_support_index_overlap"],"switching":v["support_patch_switching_detected"]}
   for s,v in w["sides"].items()}} for w in a["windows"]]} for a in actors],
  "mvp_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
