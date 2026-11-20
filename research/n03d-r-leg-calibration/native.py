"""Actually measure official MPFB rest lower-limb lengths vs 100STYLE source BVH FK."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
from lengths import segment,compare_lengths
sys.path.insert(0,str(Path(__file__).parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,SOURCES,fk
def abort(msg):raise RuntimeError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def point(rig,name):
 b=rig.data.bones.get(name)
 if b is None:abort("MISSING_RIG_BONE_"+name)
 p=rig.matrix_world@b.head_local
 return tuple(float(x) for x in p)
def main():
 parser=argparse.ArgumentParser()
 for p in ("scene","sha","wardrobe","retarget","source","out"):parser.add_argument("--"+p,required=True)
 a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
 if sha(a.scene)!=a.sha:abort("SCENE_SHA_SOURCE_FAILURE")
 scene=bpy.context.scene
 if scene.get("r078_source")!="ORIGINAL_FICTIONAL_MPFBCORE_CC0" or scene.get("r082_wardrobe")!="CC0_EXACT_ASSET_PROCEDURAL_MATERIAL":abort("NOT_ORIGINAL_CC0")
 w=json.loads(Path(a.wardrobe).read_text());r=json.loads(Path(a.retarget).read_text())
 if r.get("candidate_blend_sha256")!=a.sha or r.get("input_scene_sha256")!=w.get("blend_sha256"):abort("SOURCE_WARDROBE_SCENE_JOIN")
 raw=Path(a.source).read_bytes()
 if Path(a.source).name!="Neutral_FW.bvh" or git_blob_sha(raw)!=SOURCES["Neutral_FW.bvh"]:abort("SOURCE_BVH_NOT_PINNED")
 bvh=parse_bvh(raw);pose=fk(bvh,120)
 if bvh["count"]!=2400:abort("SOURCE_FRAME_COUNT_WRONG")
 def source_leg(side):
  hip=pose[side+"Hip"];knee=pose[side+"Knee"];ankle=pose[side+"Ankle"];toe=pose[side+"Toe"]
  # Source BVH in centimeters; copy to physical meters without target scaling.
  return {key:segment(tuple(x*.01 for x in first),tuple(x*.01 for x in second))
   for key,first,second in (("thigh",hip,knee),("shin",knee,ankle),("foot",ankle,toe))}
 src={"L":source_leg("Left"),"R":source_leg("Right")}
 actors=[]
 for row in w["characters"]:
  name=row["name"];rig=bpy.data.objects.get(name+"_MPFBRig")
  if rig is None or rig.type!="ARMATURE" or len(rig.data.bones)!=163:abort("SOURCE_NATIVE_RIG_NOT_163")
  sides=[]
  for side in ("L","R"):
   thigh=point(rig,"upperleg01."+side)
   knee=point(rig,"lowerleg01."+side)
   ankle=point(rig,"foot."+side)
   toe=point(rig,"toe1-1."+side)
   target={"thigh":segment(thigh,knee),"shin":segment(knee,ankle),"foot":segment(ankle,toe)}
   ref=src[side]
   ratio=compare_lengths(ref,target)
   sides.append({"rig_side_label":side,
    "source_BVH_side_label":"Left" if side=="L" else "Right",
    "source_segments_m":{k:round(v,6) for k,v in ref.items()},
    "target_rest_segments_m":{k:round(v,6) for k,v in target.items()},
    "mapping":"upperleg01_to_lowerleg01_thigh_lowerleg01_to_foot_shin_foot_to_toe1_1_proxy",
    "ratio":ratio,"source_to_target_anatomical_correspondence_accepted":False})
  actors.append({"actor":name,"rig_163":True,"sides":sides})
 out={"schema":"scp.n03d-r.100style-vs-mpfb-segment-morphology.v1",
   "source_100style_blob":SOURCES["Neutral_FW.bvh"],
   "source_scene_sha256":a.sha,"source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
   "blender_version":bpy.app.version_string,
   "source_fps":round(1/bvh["frame_time"],6),
   "actors":actors,"target_rig_rest_segments_not_measured_joint_centers":True,
   "source_JCS_pose_axes_calibrated":False,"retarget_contact_accepted":False,
   "mvp_accepted":False,"release_authorized":False}
 Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2,allow_nan=False)+chr(10))
 print("N03D_R_REAL_SOURCE_TARGET_SEGMENT_RATIOS",json.dumps({
  "actors":[{"actor":a["actor"],"sides":[{"side":x["rig_side_label"],
   "source_lengths":x["source_segments_m"],"target_lengths":x["target_rest_segments_m"],
   "ratios":x["ratio"]["target_to_source_length_ratios"],
   "ratio_spread":x["ratio"]["max_min_ratio_spread"]} for x in a["sides"]]} for a in actors],
  "contact_accepted":False},sort_keys=True),flush=True)
if __name__=="__main__":main()
