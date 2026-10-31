"""W9-I: independent strict evidence-typed W8 source + W9 clean-video + W9 sync arbiter.
Execution green means a FAIL is correctly adjudicated; it is never a human PASS.
"""
import argparse,hashlib,json,math,re,subprocess
from pathlib import Path
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
MODEL_SHA="cb2198952eaa5bc7e43d950b9f2aa1966528063c7295c7262133e7fa0d3d564c"
CAMERAS=("OriginalFront","OriginalOblique")
SOURCE_SHA={"forward":"c1ebf84b60bacaf4d1132f88dcfd588c9b94fa1790a3e48f163dfd195e22b449",
            "outward":"ade0dad65d9ef9d9febeaf540ce453841587276888ce03b45f3cc3f6a18346fc"}
def require(ok,code):
 if not ok:raise ValueError(code)
def sha(b):return hashlib.sha256(b).hexdigest()
def jsonfile(path):return json.loads(Path(path).read_bytes())
def readbytes(path):
 p=Path(path)
 require(p.is_file() and not p.is_symlink() and 1024<p.stat().st_size<100000000,"W9_I_VIDEO_BYTES_NOT_ADMITTED")
 return p.read_bytes()
def independent_video_decode(path):
 """Actual source-clean FFmpeg decode, no masks/GT/overlay; a separate check from source L1."""
 p=Path(path)
 j=subprocess.run(["ffprobe","-v","error","-count_frames","-select_streams","v:0",
   "-show_entries","stream=codec_name,width,height,avg_frame_rate,nb_read_frames",
   "-of","json",str(p)],capture_output=True,text=True,check=True,timeout=30)
 streams=json.loads(j.stdout).get("streams",[])
 require(len(streams)==1 and streams[0].get("codec_name")=="h264" and
  streams[0].get("width")==640 and streams[0].get("height")==360 and
  streams[0].get("avg_frame_rate")=="12/1" and streams[0].get("nb_read_frames")=="24",
  "W9_I_CLEAN_NATIVE_H264_DECODE_METADATA")
 r=subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(p),"-map","0:v:0",
   "-an","-f","framemd5","-"],capture_output=True,text=True,check=True,timeout=50)
 rows=[line for line in r.stdout.splitlines() if line and not line.startswith("#")]
 require(len(rows)==24,"W9_I_INDEPENDENT_DECODED_24_FRAME_COUNT")
 return {"frames_decoded":len(rows),"decoded_framemd5_manifest_sha256":sha(r.stdout.encode()),
  "source_sha256":sha(readbytes(p)),"codec":"h264","fps":"12/1"}
def adjudicate(profile,source_raw,native,render,rollup,prior,views,hog,geometry,decodes):
 source=json.loads(source_raw);sh=sha(source_raw)
 require(profile in SOURCE_SHA and sh==SOURCE_SHA[profile],"W9_I_WRONG_AUTHORITATIVE_SOURCE")
 require(source.get("rights")==RIGHTS and source.get("schema")=="scp.walk_w7a_original_approach.v1" and
  source.get("profile")==profile and source.get("fps_num")==12 and source.get("fps_den")==1 and
  len(source.get("actors",[]))==2,"W9_I_UNQUALIFIED_SOURCE_RIGHTS_CLOCK")
 require(native.get("source_sha256")==sh and render.get("source_motion_sha256")==sh and
  rollup.get("source_motion_sha256")==sh and prior.get("source_sha256")==sh,
  "W9_I_NATIVE_AND_BEHAVIOR_SOURCE_DISAGREE")
 require(native.get("rights")==RIGHTS and render.get("rights")==RIGHTS and prior.get("rights")==RIGHTS and
  render.get("W8_arm_motion")=="ACTUAL_KEYED_RIGID_UPPER_PROXY_24FRAME" and
  render.get("torso_arm_skinning")=="NOT_DEFORM_RIGGED",
  "W9_I_SOURCE_RIGHTS_OR_PROXY_SCOPE")
 require(prior.get("status") in ("FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED",
  "FAIL_L1_AND_FULLBODY_PROXY_UNQUALIFIED") and
  prior.get("naturalness_acceptance")=="NO" and prior.get("real_person_R009")=="HELD",
  "W9_I_FORGED_BEHAVIOR_PROMOTION")
 native_cams=render.get("cameras",[])
 rollup_cams=rollup.get("cameras",[])
 require(len(native_cams)==len(rollup_cams)==2 and
  {x.get("camera") for x in native_cams}==set(CAMERAS) and
  {x.get("camera") for x in rollup_cams}==set(CAMERAS),"W9_I_REQUIRED_VIEWS")
 require(set(views)==set(CAMERAS) and set(hog)==set(CAMERAS) and set(decodes)==set(CAMERAS),
  "W9_I_MISSING_CLEAN_OBSERVER")
 fail_l1=False;results=[]
 for camera in CAMERAS:
  raw=views[camera]["video"];qa=views[camera]["qa"]
  item=next(x for x in native_cams if x["camera"]==camera)
  check=next(x for x in rollup_cams if x["camera"]==camera)
  vsha=sha(raw)
  require(vsha==item.get("video_sha256")==check.get("video_sha256")==qa.get("source_sha256"),
    "W9_I_CROSS_RUN_VIDEO_SHA_MISMATCH")
  require(qa.get("schema")=="scp.visualqa.l1_video.v1" and
    qa.get("frames_decoded")==24 and qa.get("video",{}).get("rate")=="12/1","W9_I_UNTRUSTED_L1")
  l1=qa.get("status")
  require(l1 in ("FAIL","PASS_L1_VIDEO_ONLY") and l1==check.get("status"),
    "W9_I_L1_FROZEN_STATUS_DISAGREE")
  require((l1=="FAIL" and bool(qa.get("failures"))) or
          (l1=="PASS_L1_VIDEO_ONLY" and not qa.get("failures")),
    "W9_I_L1_FALSE_PASS_OR_FAIL")
  if l1=="FAIL":fail_l1=True
  m=hog[camera]
  require(m.get("schema")=="scp.visualqa.w9b_clean_hog.v1" and m.get("profile")==profile and
    m.get("camera")==camera and m.get("original_clean_h264_sha256")==vsha and
    m.get("model_weights_sha256")==MODEL_SHA and m.get("gt_supplied_to_detector") is False and
    m.get("independent_pose_landmarks")=="NOT_AVAILABLE_HOG_BOXES_ONLY" and
    m.get("rendered_human_behavior")=="UNKNOWN_NO_POSE_ROM_OR_GAIT_PRIOR",
    "W9_I_INVALID_INDEPENDENT_MODEL_SCOPE_OR_HASH")
  rows=m.get("observations",[])
  require(len(rows)==24 and all(x.get("tick")==i and x.get("pts_num")==i and x.get("pts_den")==12
     for i,x in enumerate(rows)),"W9_I_MODEL_FRAME_CLOCK")
  require(all(x.get("candidate_count")==len(x.get("candidates",[]))
    for x in rows),"W9_I_MODEL_BOX_COUNT")
  d=decodes[camera]
  require(d.get("frames_decoded")==24 and d.get("source_sha256")==vsha and d.get("fps")=="12/1",
    "W9_I_INDEPENDENT_CODEC_DECODE")
  results.append({"camera":camera,"video_sha256":vsha,"l1":l1,
    "first_l1_failure":qa.get("failures",[]),
    "independent_framemd5_manifest_sha256":d["decoded_framemd5_manifest_sha256"],
    "pretrained_hog_frames_with_candidates":m["frames_with_candidates"],
    "more_than_two_human_candidates_frames":m["frames_with_more_than_two_candidates"],
    "person_association":"UNKNOWN_NO_CORRESPONDENCE",
    "physical_human_gait":"UNKNOWN_NOT_INFERRED_FROM_HOG"})
 require(rollup.get("status")==("FAIL_L1_ANY_REQUIRED_VIEW" if fail_l1 else "PASS_ALL_REQUIRED_VIEWS_L1_ONLY"),
   "W9_I_FALSE_REQUIRED_VIEW_ROLLUP")
 require(prior["status"]==("FAIL_L1_AND_FULLBODY_PROXY_UNQUALIFIED" if fail_l1 else "FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED"),
  "W9_I_FALSE_SOURCE_FAIL_PRESERVATION")
 require(geometry.get("schema")=="scp.visualqa.w9c_independent_clock_projection.v1" and
  geometry.get("profile")==profile and geometry.get("source_sha256")==sh and
  geometry.get("status")=="PASS_SYNCHRONIZED_SOURCE_PROJECTION_ONLY" and
  geometry.get("native_synchronized_camera_sample_count")==288 and
  geometry.get("same_tick_pair_count")==24 and
  geometry.get("exact_W8_201_pixel_correspondence")=="NOT_RUN_DIFFERENT_NATIVE_MODEL_BINARY" and
  0<=geometry.get("max_uv_error",float("inf"))<1e-5,
  "W9_I_GEOMETRY_SOURCE_OR_SCOPE_CROSSED")
 return {
  "schema":"scp.visualqa.w9i_independent_adjudicator.v1",
  "profile":profile,"source_sha256":sh,
  "source_rights_custody":"PASS_ORIGINAL_SYNTHETIC_SOURCE_ONLY",
  "original_clean_video_l1":"FAIL_ANY_REQUIRED_VIEW" if fail_l1 else "PASS_ALL_REQUIRED_VIEWS_L1_ONLY",
  "source_human_behavior":"FAIL_FULLBODY_RIGID_PROXY_NOT_HUMAN_WALK",
  "independent_clean_model":"EXECUTED_PRETRAINED_HOG_BOX_ONLY_NO_POSE_PRIOR",
  "rendered_human_behavior":"UNKNOWN_NO_FULLBODY_ACTION_MODEL",
  "physical_dynamics":"UNKNOWN_NO_TORQUE_OR_FORCE",
  "independent_same_tick_source_projection":"PASS_DIAGNOSTIC_ONLY_DIFFERENT_NATIVE_MODEL",
  "exact_video_pixel_correspondence":"UNKNOWN_NOT_PROVEN_BY_DIFFERENT_NATIVE_MODEL",
  "R009_identity_and_product":"HELD_NOT_ACCEPTED",
  "overall":"FAIL_L1_AND_FULLBODY_HUMAN_BEHAVIOR" if fail_l1 else "FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED",
  "can_merge_release_deploy_or_promote":False,
  "clean_views":results}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--original",required=True);p.add_argument("--model",required=True)
 p.add_argument("--geometry",required=True);p.add_argument("--profile",choices=sorted(SOURCE_SHA),required=True)
 p.add_argument("--out",required=True)
 x=p.parse_args();root=Path(x.original);model=Path(x.model)
 source=(root/"source.json").read_bytes()
 native=jsonfile(root/"source_motion_receipt.json")
 render=jsonfile(root/"rendered/native_render_receipt.json")
 rollup=jsonfile(root/"rendered/independent_cross_camera_rollup.json")
 prior=jsonfile(root/"rendered/w8_behavior_receipt.json")
 views={};hog={};decodes={}
 for camera in CAMERAS:
  video=root/"rendered"/(camera+".mp4")
  views[camera]={"video":readbytes(video),"qa":jsonfile(root/"rendered"/("qa-"+camera)/"video_qa.json")}
  hog[camera]=jsonfile(model/(camera+".json"))
  decodes[camera]=independent_video_decode(video)
 g=jsonfile(x.geometry)
 result=adjudicate(x.profile,source,native,render,rollup,prior,views,hog,g,decodes)
 Path(x.out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("W9I_VERIFIED_FAIL_DOMINANT_NOT_HUMAN_ACCEPTED",x.profile,result["overall"])
if __name__=="__main__":main()
