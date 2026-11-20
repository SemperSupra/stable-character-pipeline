"""Actual original BVH FK to native MPFB root/foot heldout Sim2 diagnostic, no mutations."""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from planar import fit,transform,error
sys.path.insert(0,str(Path(__file__).parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,SOURCES,fk
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-m-source-target"))
from alignment import original_index,sample_interpolated
def require(x,msg):
 if not x:raise RuntimeError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def xy(p):return (float(p.x),float(p.y))
def main():
 p=argparse.ArgumentParser()
 for n in ("scene","sha","wardrobe","retarget","source","out"):p.add_argument("--"+n,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 require(sha(a.scene)==a.sha,"SOURCE_BLEND_SHA")
 sc=bpy.context.scene
 require(sc.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and sc.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","UNADMITTED_ASSETS")
 w=json.loads(Path(a.wardrobe).read_text());r=json.loads(Path(a.retarget).read_text())
 require(r.get("candidate_blend_sha256")==a.sha and r.get("input_scene_sha256")==w.get("blend_sha256"),"SOURCE_MANIFEST_DRIFT")
 require((sc.frame_start,sc.frame_end,sc.render.fps)==(0,71,12),"SOURCE_CLOCK_DRIFT")
 raw=Path(a.source).read_bytes()
 require(Path(a.source).name=="Neutral_FW.bvh" and git_blob_sha(raw)==SOURCES["Neutral_FW.bvh"],"BVH_SOURCE_DRIFT")
 bvh=parse_bvh(raw);require(bvh["count"]==2400,"SOURCE_FRAMES_DRIFT")
 cache={}
 def get(i):
  if i not in cache:cache[i]=fk(bvh,i)
  return cache[i]
 source={k:[] for k in ("Hips","LeftAnkle","RightAnkle")}
 for i in range(143):
  for name in source:
   pos=sample_interpolated(get,original_index(i),name)
   source[name].append((.01*pos[0],.01*pos[2]))
 out=[]
 for char in w["characters"]:
  name=char["name"];require(name in ("AsterOriginal","JuniperOriginal"),"PROTECTED_IDENTITY")
  rig=bpy.data.objects.get(name+"_MPFBRig");require(rig and len(rig.data.bones)==163,"MISSING_RIG")
  target={x:[] for x in ("Hips","L","R")}
  for i in range(143):
   sc.frame_set(i//2,subframe=(i%2)*.5);bpy.context.view_layer.update()
   h=(rig.matrix_world@rig.pose.bones["pelvis.L"].head+rig.matrix_world@rig.pose.bones["pelvis.R"].head)*.5
   target["Hips"].append(xy(h))
   for s in ("L","R"):target[s].append(xy(rig.matrix_world@rig.pose.bones["foot."+s].head))
  fitted=fit(source["Hips"][:71],target["Hips"][:71])
  root=transform(fitted,source["Hips"])
  feet=[]
  for side in ("L","R"):
   direct="LeftAnkle" if side=="L" else "RightAnkle"
   opposite="RightAnkle" if side=="L" else "LeftAnkle"
   feet.append({"rig_side":side,
    "direct_heldout_rmse_m":error(transform(fitted,source[direct])[71:],target[side][71:]),
    "opposite_control_heldout_rmse_m":error(transform(fitted,source[opposite])[71:],target[side][71:]),
    "biological_correspondence_verified":False})
  out.append({"actor":name,"fit":{"scale":round(fitted["scale"],8),
    "yaw_rad":round(__import__("math").atan2(fitted["sin"],fitted["cos"]),6),
    "training_hip_rmse_m":error(root[:71],target["Hips"][:71]),
    "heldout_hip_rmse_m":error(root[71:],target["Hips"][71:])},
    "source_to_foot_residuals":feet})
 report={"schema":"scp.n03d-s.actual-heldout-sim2-root-foot.v1",
  "source_scene_sha256":a.sha,"source_bvh_git_blob":SOURCES["Neutral_FW.bvh"],
  "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
  "fit_train_indices":[0,70],"heldout_indices":[71,142],
  "clock_hz":24,"actors":out,"source_to_native_rig_accepted":False,
  "physical_contact_accepted":False,"naturalness_accepted":False,
  "mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print("N03D_S_ACTUAL_ROOT_FOOT_HELDOUT",json.dumps({"actors":out,"mvp_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
