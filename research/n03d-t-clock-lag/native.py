"""Real source FK vs actual MPFB pelvis root clock-lag selection with heldout protocol."""
import argparse,json,hashlib,sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from lag import qualify
sys.path.insert(0,str(Path(__file__).parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,SOURCES,fk
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-m-source-target"))
from alignment import original_index,sample_interpolated
def require(ok,s):
 if not ok:raise RuntimeError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ("scene","sha","wardrobe","retarget","source","out"):p.add_argument("--"+n,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 require(sha(a.scene)==a.sha,"SOURCE_SCENE_HASH")
 scene=bpy.context.scene
 require(scene.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and scene.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","PUBLIC_CC0_RIGHTS")
 ward=json.loads(Path(a.wardrobe).read_text());rec=json.loads(Path(a.retarget).read_text())
 require(rec.get("candidate_blend_sha256")==a.sha and rec.get("input_scene_sha256")==ward.get("blend_sha256"),"WARDROBE_RETARGET_JOIN")
 require((scene.frame_start,scene.frame_end,scene.render.fps)==(0,71,12),"NATIVE_CLOCK_BAD")
 raw=Path(a.source).read_bytes()
 require(Path(a.source).name=="Neutral_FW.bvh" and git_blob_sha(raw)==SOURCES["Neutral_FW.bvh"],"PINNED_SOURCE_BVH_NOT_ADMITTED")
 src=parse_bvh(raw);require(src["count"]==2400,"NOT_100STYLE_2400F")
 cache={}
 def get(i):
  if i not in cache:cache[i]=fk(src,i)
  return cache[i]
 original=[]
 for i in range(143):
  p=sample_interpolated(get,original_index(i),"Hips")
  original.append((p[0]*.01,p[2]*.01))
 actors=[]
 for ainfo in ward["characters"]:
  name=ainfo["name"]
  require(name in ("AsterOriginal","JuniperOriginal"),"NOT_SOURCE_SAFE_ACTOR")
  rig=bpy.data.objects.get(name+"_MPFBRig")
  require(rig and len(rig.data.bones)==163,"NATIVE_163BONE_RIG_MISSING")
  target=[]
  for i in range(143):
   scene.frame_set(i//2,subframe=(i%2)*.5);bpy.context.view_layer.update()
   l=rig.matrix_world@rig.pose.bones["pelvis.L"].head
   r=rig.matrix_world@rig.pose.bones["pelvis.R"].head
   h=(l+r)*.5
   target.append((float(h.x),float(h.y)))
  result=qualify(original,target)
  actors.append({"actor":name,"timing_fit":result})
 report={"schema":"scp.n03d-t.actual-source-retarget-clock-offset-heldout.v1",
 "source_scene_sha256":a.sha,"source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
 "source_bvh_sha1":SOURCES["Neutral_FW.bvh"],
 "candidate_lags_in_24hz_samples":[-12,12],"heldout_root_only":True,
 "root_joint_correspondence_anatomical_validated":False,
 "actors":actors,"source_motion_mutated":False,
 "biological_foot_contact_accepted":False,"mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_T_HELDOUT_REAL_CLOCK_SCAN",json.dumps({"actors":[{"actor":x["actor"],
  "selected_offset":x["timing_fit"]["best_train_lag"],
  "baseline_offset":x["timing_fit"]["zero_lag_baseline"]} for x in actors],
  "contact_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
