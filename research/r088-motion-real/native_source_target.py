"""R088 real source 100STYLE joint lengths vs actual R078 source MPFB rigs.
No animation retarget or ground-contact promotion.
"""
import argparse, json, math, hashlib, sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).parent))
from bvh_preflight import parse_bvh, git_blob_sha, SOURCES, SOURCE_COMMIT

def fail(s):raise ValueError(s)
def length(v):return math.sqrt(sum(float(x)**2 for x in v))
def main():
 p=argparse.ArgumentParser()
 for n in ("scene","sha","source","sha1","out"):p.add_argument("--"+n,required=True)
 a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
 if hashlib.sha256(Path(a.scene).read_bytes()).hexdigest()!=a.sha:fail("PINNED_NATIVE_MPF_SCENE_DRIFT")
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0":fail("PROTECTED_SOURCE_ON_PUBLIC")
 f=Path(a.source)
 if f.name not in SOURCES or SOURCES[f.name]!=a.sha1 or git_blob_sha(f.read_bytes())!=a.sha1:fail("REAL_BVH_SOURCE_PIN_FAIL")
 src=parse_bvh(f.read_bytes())
 lookup={x["name"]:x for x in src["nodes"]}
 actors=[]
 for name in ("AsterOriginal","JuniperOriginal"):
  rig=bpy.data.objects.get(name+"_MPFBRig")
  body=bpy.data.objects.get(name+"_MPFBBody")
  if not rig or not body or rig.type!="ARMATURE" or len(rig.data.bones)!=163:fail("ACTUAL_163BONE_MPF_UNAVAILABLE")
  if not any(x.type=="ARMATURE" and x.object==rig for x in body.modifiers):fail("RIGGED_MPF_NOT_FOUND")
  sides=[]
  for side,source_side in (("L","Left"),("R","Right")):
   full=("upperleg01."+side,"upperleg02."+side,"lowerleg01."+side,"lowerleg02."+side,"foot."+side)
   if any(n not in rig.data.bones for n in full):fail("INCOMPLETE_ACTUAL_NATIVE_CHAIN")
   for i in range(1,len(full)):
    if rig.data.bones[full[i]].parent.name!=full[i-1]:fail("NATIVE_CHAIN_ANCESTRY_DRIFT")
   source_m=.01*(length(lookup[source_side+"Knee"]["offset"])+length(lookup[source_side+"Ankle"]["offset"]))
   target_m=sum(float(rig.data.bones[n].length) for n in full[:-1])
   if not 0.2<source_m<2.0 or not 0.2<target_m<3.0:fail("LEG_SCALE_RANGE")
   sides.append({"label":side,"source_hip_knee_ankle_m":round(source_m,6),
        "native_leg_bone_length_sum_m":round(target_m,6),
        "candidate_length_ratio":round(target_m/source_m,6),
        "native_chain":list(full),"axes_calibrated":False,"foot_contact_accepted":False})
  actors.append({"actor":name,"source_bvh":f.name,"native_bone_count":163,"sides":sides})
 result={"schema":"scp.r088.actual-bvh-to-mpfb-preflight.v1",
   "source_commit":SOURCE_COMMIT,"source_blob_sha1":a.sha1,
   "native_blend_sha256":a.sha,"actors":actors,
   "status":"MEASURED_SOURCE_AND_TARGET_LEG_LENGTHS_HOLD_RETARGET",
   "source_joint_semantics_accepted":False,"mpfb_retarged_motion_accepted":False,
   "source_shoe_sole_contact_accepted":False,"mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print("R088_REAL_SOURCE_TARGET_GEOMETRY",json.dumps(result,sort_keys=True),flush=True)
if __name__=="__main__":main()
