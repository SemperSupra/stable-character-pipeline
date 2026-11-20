"""Temporary actual five-bone IK targets from recorded relative ankle motion; unsaved."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from target import target,bounded_delta,reachability
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-s-planar-align"))
from planar import fit
sys.path.insert(0,str(Path(__file__).parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,SOURCES,fk
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-m-source-target"))
from alignment import original_index,sample_interpolated
sys.path.insert(0,str(Path(__file__).parent.parent/"r090-dressed"))
from measure import stable_sole_sample
def require(ok,s):
 if not ok:raise RuntimeError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def xyz(v):return tuple(float(x) for x in v)
def posepoint(rig,name,tail=False):
 b=rig.pose.bones.get(name)
 require(b is not None,"MISSING_POSE_BONE_"+name)
 return rig.matrix_world@(b.tail if tail else b.head)
def restpoint(rig,name):
 b=rig.data.bones.get(name);require(b is not None,"SOURCE_REST_BONE_MISSING_"+name)
 return rig.matrix_world@b.head_local
def chain(rig,side):
 names=[x+"."+side for x in ("foot","lowerleg02","lowerleg01","upperleg02","upperleg01")]
 for index in range(4):
  require(rig.data.bones[names[index]].parent.name==names[index+1],"FIVE_LINK_PARENT_DRIFT")
 require(rig.data.bones[names[-1]].parent.name=="pelvis."+side,"HIP_RIG_CHAIN_DRIFT")
 return names
def main():
 parser=argparse.ArgumentParser()
 for k in ("scene","sha","wardrobe","retarget","source","out"):parser.add_argument("--"+k,required=True)
 a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
 require(sha(a.scene)==a.sha,"SOURCE_SCENE_SHA_DRIFT")
 scene=bpy.context.scene
 require(scene.get("r078_source")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and scene.get("r082_wardrobe")=="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL","RIGHTS_OR_WARDROBE_INVALID")
 ward=json.loads(Path(a.wardrobe).read_text());rec=json.loads(Path(a.retarget).read_text())
 require(rec.get("candidate_blend_sha256")==a.sha and rec.get("input_scene_sha256")==ward.get("blend_sha256"),"SOURCE_SCENE_JOIN")
 require((scene.frame_start,scene.frame_end,scene.render.fps)==(0,71,12),"SOURCE_NATIVE_CLOCK")
 data=Path(a.source).read_bytes()
 require(Path(a.source).name=="Neutral_FW.bvh" and git_blob_sha(data)==SOURCES["Neutral_FW.bvh"],"SOURCE_MOTION_BLOB_UNPINNED")
 bvh=parse_bvh(data);require(bvh["count"]==2400,"SOURCE_BVH_CLOCK_DRIFT")
 cached={}
 def fk_at(index):
  if index not in cached:cached[index]=fk(bvh,index)
  return cached[index]
 def point_at(i,name):
  return tuple(.01*x for x in sample_interpolated(fk_at,original_index(i),name))
 source_hips=[point_at(i,"Hips") for i in range(143)]
 source_xy=[(p[0],p[2]) for p in source_hips]
 src_rest=fk_at(120)
 actors=[]
 for person in ward["characters"]:
  name=person["name"];require(name in ("AsterOriginal","JuniperOriginal"),"PROTECTED_CHARACTER")
  rig=bpy.data.objects.get(name+"_MPFBRig");require(rig and len(rig.data.bones)==163,"RIG_SOURCE_NOT_163")
  shoes=[g for g in person["garments"] if g["pack"]=="shoes01"]
  require(len(shoes)==1,"SOURCE_SHOE_NOT_SINGLE")
  shoe=bpy.data.objects.get(shoes[0]["native_object"])
  require(shoe and any(m.type=="ARMATURE" and m.object==rig for m in shoe.modifiers),"ACTUAL_SHOE_SKIN_NOT_RIGGED")
  hips=[]
  for i in range(71):
   scene.frame_set(i//2,subframe=(i%2)*.5);bpy.context.view_layer.update()
   hips.append(posepoint(rig,"pelvis.L").lerp(posepoint(rig,"pelvis.R"),.5))
  m=fit(source_xy[:71],[(float(x.x),float(x.y)) for x in hips])
  yaw=math.atan2(m["sin"],m["cos"])
  # Four 24Hz points over 125ms, treated as forced feasibility only, NOT measured stance.
  samples=[24,25,26,27]
  baseline=[]
  legs={}
  for side,src_side in (("L","Left"),("R","Right")):
   bones=chain(rig,side)
   hip=restpoint(rig,"upperleg01."+side);knee=restpoint(rig,"lowerleg01."+side);ankle=restpoint(rig,"foot."+side)
   thigh=float((knee-hip).length);shin=float((ankle-knee).length)
   src_pose=src_rest
   s_thigh=math.dist(src_pose[src_side+"Hip"],src_pose[src_side+"Knee"])*.01
   s_shin=math.dist(src_pose[src_side+"Knee"],src_pose[src_side+"Ankle"])*.01
   scale=(thigh+shin)/(s_thigh+s_shin)
   require(.3<=scale<=2.,"MORPHOLOGY_SCALE_OUT_OF_RANGE")
   legs[side]={"bone_names":bones,"source_side":src_side,"scale":scale,
    "thigh":thigh,"shin":shin}
  for i in samples:
   scene.frame_set(i//2,subframe=(i%2)*.5);bpy.context.view_layer.update()
   pelvis=posepoint(rig,"pelvis.L").lerp(posepoint(rig,"pelvis.R"),.5)
   shoesource=stable_sole_sample(shoe)
   datum={"i":i,"root":pelvis.copy(),"sole":shoesource,"legs":{}}
   for side in ("L","R"):
    foot_head=posepoint(rig,"foot."+side).copy()
    foot_tail=posepoint(rig,"foot."+side,True).copy()
    original=point_at(i,legs[side]["source_side"]+"Ankle")
    hip_src=source_hips[i]
    desired=Vector(target(hip_src,original,xyz(pelvis),legs[side]["scale"],yaw))
    d=Vector(bounded_delta(xyz(foot_head),xyz(desired),.04))
    reach=reachability(xyz(pelvis),xyz(desired),legs[side]["thigh"],legs[side]["shin"])
    datum["legs"][side]={"before_head":foot_head,"before_tail":foot_tail,
      "desired":desired,"bounded_delta":d,"reach":reach}
   baseline.append(datum)
  constraints=[];targets=[]
  try:
   for side in ("L","R"):
    obj=bpy.data.objects.new("N03D_U_ephemeral_"+name+"_"+side,None)
    scene.collection.objects.link(obj);targets.append(obj)
    con=rig.pose.bones["foot."+side].constraints.new("IK")
    con.target=obj;con.chain_count=5;con.iterations=100
    con.use_stretch=False;con.use_rotation=False;con.use_location=True
    constraints.append((rig.pose.bones["foot."+side],con))
   checks=[]
   for datum in baseline:
    i=datum["i"]
    for side,ob in zip(("L","R"),targets):
     b=datum["legs"][side]
     ob.location=b["before_tail"]+b["bounded_delta"]
    scene.frame_set(i//2,subframe=(i%2)*.5);bpy.context.view_layer.update()
    newsole=stable_sole_sample(shoe)
    root=posepoint(rig,"pelvis.L").lerp(posepoint(rig,"pelvis.R"),.5)
    row={"sample_index":i,"t_s":round(i/24,6),"actual_root_drift_m":round(float((root-datum["root"]).length),6),
      "leg_comparisons":{}}
    for side in ("L","R"):
     b=datum["legs"][side]
     newhead=posepoint(rig,"foot."+side)
     part="rest_local_x_positive" if side=="L" else "rest_local_x_negative"
     row["leg_comparisons"][side]={
      "source_ankle_target_error_before_m":round(float((b["before_head"]-b["desired"]).length),6),
      "source_ankle_target_error_after_m":round(float((newhead-b["desired"]).length),6),
      "requested_foot_head_change_m":round(float(b["bounded_delta"].length),6),
      "source_limb_reachability":b["reach"],
      "source_shoe_proxy_min_z_before_m":round(float(datum["sole"][part]["z_m"]),6),
      "source_shoe_proxy_min_z_after_m":round(float(newsole[part]["z_m"]),6),
      "anatomical_side_verified":False,"support_patch_anatomy_verified":False}
    checks.append(row)
   actors.append({"actor":name,"source_hip_yaw_rad":round(yaw,6),
     "source_limb_scale_ratios":{side:round(legs[side]["scale"],6) for side in legs},
     "forced_window_24hz_samples":samples,"before_after":checks,
     "source_ankle_target_is_not_shoe_sole":True,"source_ankle_alignment_not_biomechanical_proof":True,
     "planted_contact_accepted":False})
  finally:
   for foot,con in constraints:foot.constraints.remove(con)
   for ob in targets:bpy.data.objects.remove(ob,do_unlink=True)
 result={"schema":"scp.n03d-u.actual-recorded-relative-ankle-bounded-fivebone-ik.v1",
  "source_scene_sha256":a.sha,"source_bvh_blob":SOURCES["Neutral_FW.bvh"],
  "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
  "correction_max_per_sample_m":.04,"forced_window_duration_s":.125,
  "actors":actors,"source_scene_saved":False,"source_action_changed":False,
  "physical_shoe_contact_accepted":False,"joint_pole_axes_calibrated":False,
  "biological_naturalness_accepted":False,"mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")
 print("N03D_U_REAL_SOURCE_RELATIVE_NATIVE_IK",json.dumps({"actors":[{"actor":x["actor"],"scale":x["source_limb_scale_ratios"],
 "checks":[{"i":v["sample_index"],"root_drift":v["actual_root_drift_m"],
 "legs":v["leg_comparisons"]} for v in x["before_after"]]} for x in actors],
 "mvp_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
