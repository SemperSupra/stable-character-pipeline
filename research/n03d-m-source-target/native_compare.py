"""Real source recorded 100STYLE FK ankle / toe vs retargeted 163 bone rig foot heads.
Compare speed magnitudes invariant to axis rotation, NOT assert raw source ankle = CC0 sole.
"""
import argparse,hashlib,json,sys,math
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from alignment import original_index,sample_interpolated,near_ground_ratio
sys.path.insert(0,str(Path(__file__).parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,SOURCES,fk
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-l-source-motion"))
from source_contact import summarize

def fail(m):raise RuntimeError(m)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def world(rig,bone):
 obj=rig.pose.bones.get(bone)
 if obj is None:fail("NATIVE_BONE_MISSING_"+bone)
 return rig.matrix_world@obj.head
def target_sample(rig,side):
 f=world(rig,"foot."+side)
 return (float(f.x),float(f.z),float(f.y))
def hip_sample(rig):
 a=world(rig,"pelvis.L");b=world(rig,"pelvis.R")
 m=(a+b)*.5
 return (float(m.x),float(m.z),float(m.y))
def shoe_sample(record,side):
 x=record["sides"][side]
 return [(s["xy_m"][0],s["z_m"],s["xy_m"][1]) for s in x["samples"]]
def main():
 ap=argparse.ArgumentParser()
 for p in ("scene","sha","wardrobe","retarget","trace","correspondence","source","out"):ap.add_argument("--"+p,required=True)
 args=ap.parse_args(sys.argv[sys.argv.index("--")+1:])
 if sha(args.scene)!=args.sha:fail("ACTUAL_SOURCE_SCENE_SHA")
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":fail("RIGHTS_OR_SCENE_INVALID")
 ward=json.loads(Path(args.wardrobe).read_text());rec=json.loads(Path(args.retarget).read_text())
 trace=json.loads(Path(args.trace).read_text());corr=json.loads(Path(args.correspondence).read_text())
 if rec.get("candidate_blend_sha256")!=args.sha or trace.get("source_scene_sha256")!=args.sha or corr.get("source_scene_sha256")!=args.sha:fail("SOURCE_SCENE_JOIN")
 if corr.get("source_trace_sha256")!=sha(args.trace) or rec.get("input_scene_sha256")!=ward.get("blend_sha256"):fail("TRACE_RIGHTS_JOIN")
 if trace.get("frame_rate_hz")!=24 or trace.get("sample_count_per_side")!=143:fail("NATIVE_TRACE_TIMEBASE_WRONG")
 raw=Path(args.source).read_bytes()
 if Path(args.source).name!="Neutral_FW.bvh" or git_blob_sha(raw)!=SOURCES["Neutral_FW.bvh"]:fail("REAL_BVH_SOURCE_BAD")
 if trace.get("source_100style_sha256")!=hashlib.sha256(raw).hexdigest():fail("BVH_TRACE_SOURCE_JOIN")
 bvh=parse_bvh(raw)
 if bvh["count"]!=2400:fail("EXPECTED_2400_FRAMES")
 cache={}
 def fk_at(i):
  if i not in cache:cache[i]=fk(bvh,i)
  return cache[i]
 reference={}
 for joint in ("Hips","LeftAnkle","RightAnkle","LeftToe","RightToe"):
  points=[]
  for i in range(143):
   xyz=sample_interpolated(fk_at,original_index(i),joint)
   points.append(tuple(.01*x for x in xyz))
  reference[joint]=summarize(points,1/24)
 actors=[]
 for person in corr["actors"]:
  name=person["actor"]
  rig=bpy.data.objects.get(name+"_MPFBRig")
  if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=163:fail("MPF_NATIVE_RIG_LOST")
  actual={}
  for i in range(143):
   scene.frame_set(i//2,subframe=(i%2)*.5);bpy.context.view_layer.update()
   for k,side in (("foot.L","L"),("foot.R","R")):
    actual.setdefault(k,[]).append(target_sample(rig,side))
   actual.setdefault("hip_proxy",[]).append(hip_sample(rig))
  observed={k:summarize(p,1/24) for k,p in actual.items()}
  side_reports=[]
  for side,sourcejoint in (("L","LeftAnkle"),("R","RightAnkle")):
   foot=observed["foot."+side]
   same=near_ground_ratio(reference[sourcejoint],foot)
   opposite=near_ground_ratio(reference["RightAnkle" if side=="L" else "LeftAnkle"],foot)
   side_reports.append({"rig_side":side,
     "source_ankle_name_assumption":sourcejoint,"source_ankle_near_p50_mps":reference[sourcejoint]["near_ground_p50_world_speed_mps"],
     "native_foot_head_near_p50_mps":foot["near_ground_p50_world_speed_mps"],
     "native_foot_head_near_p95_mps":foot["near_ground_p95_world_speed_mps"],
     "direct_label_speed_ratio":same,"opposite_label_speed_ratio":opposite,
     "source_ankle_is_not_CC0_shoe_sole":True,
     "rig_side_anatomical_orientation_accepted":False})
  native_shoe=[]
  tr=next(x for x in trace["actors"] if x["actor"]==name)
  for part in person["partitions"]:
   label=part["candidate_rig_side"]["label"]
   key=part["rest_local_partition"]
   native_shoe.append({"source_partition":key,"candidate_rig_side":label,
     "actual_synthetic_shoe_support_centroid_world":summarize(shoe_sample(tr,key),1/24)})
  actors.append({"actor":name,"source_vs_native":side_reports,
     "target_hip_proxy":observed["hip_proxy"],
     "target_shoe_support_proxies":native_shoe})
 report={"schema":"scp.n03d-m.source60hz-fk-vs-retarget-foot24hz.v1",
  "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
  "source_motion_blob":SOURCES["Neutral_FW.bvh"],"source_scene_sha256":args.sha,
  "trace_sha256":sha(args.trace),"correspondence_sha256":sha(args.correspondence),
  "source_original_reference_FK_24hz":reference,
  "actors":actors,
  "source_origin":"100STYLE CC BY 4.0; modified derivative SHA-pinned",
  "identical_ankle_to_shoe_material_semantics":False,
  "rig_to_BVH_coordinate_alignment_verified":False,
  "retarget_scaling_or_slip_causation_established":False,
  "foot_contact_accepted":False,"natural_gait_accepted":False,
  "mvp_accepted":False,"release_authorized":False}
 Path(args.out).write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_M_REAL_SOURCE_VS_TARGET_KINEMATICS",json.dumps({
 "source_near_median":{k:v["near_ground_p50_world_speed_mps"] for k,v in reference.items()},
 "actors":[{"actor":v["actor"],
   "rig_sides":[{"side":w["rig_side"],"target_foot_p50_mps":w["native_foot_head_near_p50_mps"],
   "source_ankle_p50_mps":w["source_ankle_near_p50_mps"],"speed_ratio":w["direct_label_speed_ratio"]} for w in v["source_vs_native"]]}
   for v in actors],
 "retarget_cause_proven":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
