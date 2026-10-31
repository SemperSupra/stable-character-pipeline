"""W9-B: independently PRETRAINED OpenCV HOG proposals on ORIGINAL CLEAN #201 video.
No GT, synthetic sidecars, annotations or actor labels are read until AFTER detection.
A human-shaped candidate is not a human gait / anatomical / action prior.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import cv2
import numpy as np

RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
MODEL_SHA256="cb2198952eaa5bc7e43d950b9f2aa1966528063c7295c7262133e7fa0d3d564c"
EXPECTED={
 "forward":{"source":"c1ebf84b60bacaf4d1132f88dcfd588c9b94fa1790a3e48f163dfd195e22b449",
  "OriginalFront":"da7bfb7964b162547a9aad1c4f4502d64bb2bc0ebab520737e4322850f7821d8",
  "OriginalOblique":"714ab136d33b92469bb6d6608bae960825834c642f750f09f88921705889228b"},
 "outward":{"source":"ade0dad65d9ef9d9febeaf540ce453841587276888ce03b45f3cc3f6a18346fc",
  "OriginalFront":"ffaf66384af5ba5f829a113edfddfff025ae278b4d143a445435bb44df03d8a8",
  "OriginalOblique":"390e3991d06bea8f42323490d1777a3689834abb4e6487cf93f02f5e92654b39"}
}
CAMERAS=("OriginalFront","OriginalOblique")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def model():
 if cv2.__version__!="4.13.0":raise ValueError("W9_B_UNPINNED_CV_VERSION")
 weights=cv2.HOGDescriptor_getDefaultPeopleDetector()
 checksum=hashlib.sha256(weights.tobytes()).hexdigest()
 if checksum!=MODEL_SHA256:raise ValueError("W9_B_MODEL_WEIGHT_SHA_MISMATCH")
 h=cv2.HOGDescriptor()
 h.setSVMDetector(weights)
 cv2.setNumThreads(2)
 return h
def validate_boxes(rects,weights,shape):
 if len(rects)!=len(weights):raise ValueError("W9_B_DETECTOR_BOX_CONFIDENCE_COUNT")
 h,w=shape[:2];out=[]
 for rect,score in zip(rects,weights):
  x,y,bw,bh=[int(v) for v in rect]
  score=float(score)
  if not math.isfinite(score) or bw<=0 or bh<=0 or x<0 or y<0 or x+bw>w or y+bh>h:
   raise ValueError("W9_B_NONFINITE_OR_OUTSIDE_DETECTOR_BOX")
  out.append({"xywh":[x,y,bw,bh],"svm_margin":score})
 return out
def inspect(video,expected,profile,camera,hog):
 path=Path(video)
 if path.is_symlink() or not path.is_file() or not 1024<=path.stat().st_size<=100000000:
  raise ValueError("W9_B_CLEAN_VIDEO_NOT_ADMITTED")
 if len(expected)!=64 or sha(path)!=expected:
  raise ValueError("W9_B_CLEAN_VIDEO_SHA_MISMATCH")
 cap=cv2.VideoCapture(str(path))
 if not cap.isOpened():raise ValueError("W9_B_ORIGINAL_DECODE_NOT_OPEN")
 fps=float(cap.get(cv2.CAP_PROP_FPS))
 if abs(fps-12)>1e-6:raise ValueError("W9_B_RATE")
 t0=time.perf_counter()
 frames=[]
 for tick in range(25):
  ok,bgr=cap.read()
  if not ok:break
  if tick>=24 or bgr.shape[:2]!=(360,640):
   raise ValueError("W9_B_FRAME_COUNT_OR_RESOLUTION")
  boxes,scores=hog.detectMultiScale(bgr,winStride=(8,8),padding=(8,8),scale=1.05)
  candidates=validate_boxes(boxes,scores,bgr.shape)
  frames.append({"tick":tick,"pts_num":tick,"pts_den":12,
   "candidate_count":len(candidates),"candidates":candidates,
   "association":"UNKNOWN_NO_IDENTITY_OR_MULTIVIEW_TRACK"})
 cap.release()
 if len(frames)!=24:raise ValueError("W9_B_DECODE_INCOMPLETE")
 return {"schema":"scp.visualqa.w9b_clean_hog.v1","profile":profile,"camera":camera,
  "original_clean_h264_sha256":sha(path),"model_weights_sha256":MODEL_SHA256,
  "model_name":"opencv_builtin_hog_svm_default_people_detector",
  "runtime":"opencv-python-headless==4.13.0.92; numpy==2.3.5; CPU 2 threads",
  "model_source":"OpenCV built-in HOG SVM; runtime weights SHA pinned",
  "licensed_code":"OpenCV Apache-2.0 package; model weight admission limited to bundled detector",
  "human_action_prior":"NOT_RUN_NO_NORMATIVE_TEMPORAL_MODEL",
  "independent_pose_landmarks":"NOT_AVAILABLE_HOG_BOXES_ONLY",
  "gt_supplied_to_detector":False,
  "actor_identity":"UNKNOWN_CANDIDATES_NOT_TRACKED_OR_CORRESPONDED",
  "rendered_human_behavior":"UNKNOWN_NO_POSE_ROM_OR_GAIT_PRIOR",
  "frames_decoded":len(frames),"frames_with_candidates":sum(x["candidate_count"]>0 for x in frames),
  "frames_with_more_than_two_candidates":sum(x["candidate_count"]>2 for x in frames),
  "frames_without_any_candidate":sum(x["candidate_count"]==0 for x in frames),
  "cpu_seconds_observer":round(time.perf_counter()-t0,4),
  "observations":frames}
def join(root,profile,observations):
 # Called only after clean-video observations are fully complete.
 source=root/"source.json"
 native=json.loads((root/"rendered/native_render_receipt.json").read_text())
 prior=json.loads((root/"rendered/w8_behavior_receipt.json").read_text())
 item=EXPECTED[profile]
 if sha(source)!=item["source"] or native.get("source_motion_sha256")!=item["source"] or prior.get("source_sha256")!=item["source"]:
  raise ValueError("W9_B_POST_OBSERVATION_SOURCE_SHA")
 if native.get("rights")!=RIGHTS or native.get("W8_arm_motion")!="ACTUAL_KEYED_RIGID_UPPER_PROXY_24FRAME":
  raise ValueError("W9_B_POST_OBSERVATION_SOURCE_SCOPE")
 if prior.get("status")!="FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED":
  raise ValueError("W9_B_PROHIBITED_HUMAN_PROMOTION")
 cams={c["camera"]:c["video_sha256"] for c in native["cameras"]}
 if cams!={k:item[k] for k in CAMERAS}:raise ValueError("W9_B_POST_OBSERVATION_NATIVE_VIDEO_MISMATCH")
 return {"schema":"scp.visualqa.w9b_join.v1","profile":profile,"source_sha256":item["source"],
  "original_videos":cams,"detector_input_was_clean":True,"independent_model_sha256":MODEL_SHA256,
  "independent_observation_cameras":len(observations),
  "human_behavior":"FAIL_FULLBODY_HUMAN_BEHAVIOR_PROXY_UNQUALIFIED_INHERITED_SOURCE",
  "rendered_behavior":"UNKNOWN_CANNOT_INFER_GAIT_FROM_BOXES",
  "original_l1":"PASS_VIDEO_ONLY_ALREADY_VERIFIED_W8_201",
  "R009_product":"HELD"}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--artifact",required=True)
 ap.add_argument("--profile",choices=sorted(EXPECTED),required=True);ap.add_argument("--out",required=True)
 x=ap.parse_args();root=Path(x.artifact);out=Path(x.out);out.mkdir(parents=True,exist_ok=True)
 hog=model();observations=[]
 for cam in CAMERAS:
  r=inspect(root/"rendered"/(cam+".mp4"),EXPECTED[x.profile][cam],x.profile,cam,hog)
  observations.append(r)
  (out/(cam+".json")).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 receipt=join(root,x.profile,observations)
 (out/"post_observation_join.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W9_B_INDEPENDENT_PRETRAINED_CLEAN_PROPOSALS_NO_GAIT_PASS",x.profile,
       [(o["camera"],o["frames_with_candidates"],o["frames_with_more_than_two_candidates"]) for o in observations])
if __name__=="__main__":main()
