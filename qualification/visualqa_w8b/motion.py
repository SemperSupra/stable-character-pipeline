"""W8-B unannotated H264 optical flow. Observer does not consume scene truth."""
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np
EXPECTED={
 "forward":{"OriginalFront":"8da6f11403972d772af36a2b2a76435994f7699839bab43839cd1cfaad12af84","OriginalOblique":"1109a06cecb7edd53a59bd7d02433a32a683897eef541ecfb1ed43c586bea0bf"},
 "outward":{"OriginalFront":"03b2cb6d26ff044f942773b83961d44bb03dfdbdf776017d254ab04c430dc3a2","OriginalOblique":"e5d557423538e59e9b4cd035ad0cc5538152822895901e309a01bc3f2dea05bf"}}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def measure(frames):
 if len(frames)!=24:raise ValueError("W8B_FRAME_COUNT")
 if len({hashlib.sha256(f.tobytes()).hexdigest() for f in frames})<3:raise ValueError("W8B_STATIC_FRAMES")
 observations=[]
 for a,b in zip(frames,frames[1:]):
  flow=cv2.calcOpticalFlowFarneback(a,b,None,.5,3,15,3,5,1.2,0)
  mag=np.sqrt(flow[:,:,0]**2+flow[:,:,1]**2)
  delta=cv2.absdiff(a,b)
  observations.append({"median_flow_pixels":float(np.median(mag)),
   "p90_flow_pixels":float(np.percentile(mag,90)),
   "flow_active_gt_point2_fraction":float(np.mean(mag>.2)),
   "changed_luma_gt2_fraction":float(np.mean(delta>2)),
   "mean_abs_luma_delta":float(np.mean(delta))})
 return observations
def observe(path,profile,cam):
 path=Path(path)
 if path.is_symlink() or not (1024<=path.stat().st_size<100000000) or sha(path)!=EXPECTED[profile][cam]:
  raise ValueError("W8B_ORIGINAL_CLEAN_VIDEO_SHA "+str({"camera":cam,"size":path.stat().st_size,"actual":sha(path),"expected":EXPECTED[profile][cam]}))
 capture=cv2.VideoCapture(str(path))
 if not capture.isOpened():raise ValueError("W8B_VIDEO_OPEN")
 rate=capture.get(cv2.CAP_PROP_FPS);frames=[]
 while len(frames)<=24:
  ok,bgr=capture.read()
  if not ok:break
  frames.append(cv2.cvtColor(cv2.resize(bgr,(160,90)),cv2.COLOR_BGR2GRAY))
 capture.release()
 if abs(rate-12)>.001:raise ValueError("W8B_ORIGINAL_FPS")
 return {"schema":"scp.visualqa_w8b.clean_motion.v1","video_sha256":sha(path),
  "profile":profile,"camera":cam,"frame_count":len(frames),"fps":rate,
  "optical_flow":"opencv_farneback_cpu","opencv_version":cv2.__version__,
  "source_gt_available_to_observer":False,
  "archive_pointer":"REGULAR_FILE_REQUIRED","transitions":measure(frames),
  "human_pose":"NOT_RUN_UNAPPROVED_MODEL","animal_pose":"NOT_RUN_WRONG_SUBJECT",
  "rendered_behavior":"UNKNOWN_MOTION_FEATURES_NOT_GAIT_PRIOR"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--artifact",required=True);p.add_argument("--profile",choices=sorted(EXPECTED),required=True);p.add_argument("--out",required=True)
 a=p.parse_args();root=Path(a.artifact);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 observations=[observe(root/"rendered"/(c+".mp4"),a.profile,c) for c in ("OriginalFront","OriginalOblique")]
 for o in observations:(out/(o["camera"]+".json")).write_text(json.dumps(o,sort_keys=True,indent=2)+chr(10))
 # Custody join strictly AFTER independent observations; no source keypoints are fed to flow.
 native=json.loads((root/"rendered"/"native_render_receipt.json").read_text())
 source=sha(root/"source.json")
 cameras={x["camera"]:x["video_sha256"] for x in native["cameras"]}
 if native.get("source_motion_sha256")!=source or native.get("profile")!=a.profile or native.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or cameras!=EXPECTED[a.profile]:
  raise ValueError("W8B_POST_OBSERVATION_SOURCE_CUSTODY")
 receipt={"schema":"scp.visualqa_w8b.join.v1","source_sha256":source,"profile":a.profile,
  "original_clean_video_sha256":cameras,"independent_observed_cameras":2,
  "l1":"PASS_ALL_REQUIRED_VIEWS_L1_ONLY_PREVIOUSLY_VERIFIED",
  "rendered_behavior":"UNKNOWN_NO_APPROVED_POSE_OR_ACTION_PRIOR",
  "human_anatomy":"UNKNOWN_STATIC_UPPER_BODY_PROXY","gt_provided_to_model":False}
 (out/"join.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+chr(10))
 print("W8B_CLEAN_OPTICAL_OBSERVED_NOT_HUMAN_GAIT_ACCEPTED",a.profile)
if __name__=="__main__":main()
