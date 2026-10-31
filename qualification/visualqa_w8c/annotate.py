"""W8-C disposable GT annotation of original CLEAN video, never an acceptance oracle."""
import argparse,hashlib,json,math,subprocess,tempfile
from pathlib import Path
import cv2,numpy as np

CAMERAS={"OriginalFront":((0,-8.5,2.8),(0,0,1.15)),
         "OriginalOblique":((7.5,-7,3.1),(0,0,1.15))}
EXPECTED={
 "forward":{"OriginalFront":"8da6f11403972d772af36a2b2a76435994f7699839bab43839cd1cfaad12af84","OriginalOblique":"1109a06cecb7edd53a59bd7d02433a683897eef541ecfb1ed43c586bea0bf"},
 "outward":{"OriginalFront":"03b2cb6d26ff044f942773b83961d44bb03dfdbdf776017d254ab04c430dc3a2","OriginalOblique":"e5d557423538e59e9b4cd035ad0cc5538152822895901e309a01bc3f2dea05bf"}}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def unit(x):
 n=math.sqrt(sum(v*v for v in x))
 if not math.isfinite(n) or n<1e-9:raise ValueError("W8C_INVALID_CAMERA")
 return tuple(v/n for v in x)
def minus(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def project(p,camera):
 eye,target=CAMERAS[camera]
 forward=unit(minus(target,eye));right=unit(cross(forward,(0,0,1)));up=unit(cross(right,forward))
 offset=minus(p,eye)
 # Blender orthographic scale = horizontal sensor width at landscape aspect 640/360.
 u=.5+dot(offset,right)/5.75
 v=.5+dot(offset,up)/(5.75*360/640)
 return (u,v)
def camera_receipt(source,render):
 if source.get("schema")!="scp.walk_w7a_original_approach.v1" or source.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or len(source.get("actors",[]))!=2:
  raise ValueError("W8C_SOURCE_ID_RIGHTS")
 report={}
 for c in render["cameras"]:
  name=c["camera"]
  if name not in CAMERAS:raise ValueError("W8C_CAMERA_ID")
  for item in c["core_body_camera_projection"]:
   actor=next((x for x in source["actors"] if x["id"]==item["actor"]),None)
   if actor is None:raise ValueError("W8C_ACTOR_ID")
   z={"Head":2.17,"Torso":1.5,"Pelvis":1.09}.get(item["part"])
   if z is None:raise ValueError("W8C_BODY_PROBE")
   f=actor["frames"][0 if name=="OriginalFront" else 23]
   uv=project((f["root_x"],f["root_y"],z),name)
   error=math.dist(uv,item["uv"])
   if error>.002:raise ValueError("W8C_SOURCE_CAMERA_CALIBRATION_MISMATCH")
   report[name]=max(report.get(name,0),error)
 if set(report)!=set(CAMERAS):raise ValueError("W8C_REQUIRED_TWO_CAMERAS")
 return report
def sidecar(source,camera):
 rows=[]
 for tick in range(24):
  row={"schema":"scp.visualqa_w8c.gt_frame.v1","camera":camera,"tick":tick,
   "pts_num":tick,"pts_den":12,"ground_truth_only":True,
   "independent_detector":"NOT_USED_FOR_OVERLAY","occlusion":"UNKNOWN_NO_SOURCE_DEPTH_TEST","actors":[]}
  for a in source["actors"]:
   if len(a["frames"])!=24:raise ValueError("W8C_FRAME_COUNT")
   f=a["frames"][tick]
   if (f["index"],f["time_num"],f["time_den"])!=(tick,tick,12):raise ValueError("W8C_SOURCE_CLOCK")
   body={"id":a["id"],"root":[f["root_x"],f["root_y"],0],"legs":[]}
   if [leg["id"] for leg in f["legs"]]!=["Left","Right"]:raise ValueError("W8C_SWAPPED_LR")
   for leg in f["legs"]:
    points={}
    for key in ("hip","knee","ankle","heel","toe","pole"):
     pos=leg[key]
     if len(pos)!=3 or not all(math.isfinite(v) for v in pos):raise ValueError("W8C_BAD_JOINT")
     uv=project(pos,camera)
     points[key]={"xyz":pos,"uv":uv,
       "visibility":"IN_FRAME_OCCLUSION_UNKNOWN" if 0<=uv[0]<=1 and 0<=uv[1]<=1 else "OFFSCREEN"}
    body["legs"].append({"id":leg["id"],"stance_label":leg["state"],
      "points":points,"anatomical_jcs":"UNKNOWN_SOURCE_POLE_NOT_BIOLOGICAL"})
   row["actors"].append(body)
  rows.append(row)
 return rows
def px(uv):return (int(round(uv[0]*640)),int(round((1-uv[1])*360)))
def draw(frame,datum):
 cv2.putText(frame,"SOURCE GT / DEBUG ONLY - NOT BEHAVIOR PASS",(12,24),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),1,cv2.LINE_AA)
 cv2.putText(frame,f"{datum['camera']}  frame {datum['tick']:02}/23  t={datum['tick']/12:.3f}s",(12,345),cv2.FONT_HERSHEY_SIMPLEX,.47,(255,255,255),1,cv2.LINE_AA)
 for actor in datum["actors"]:
  root=actor["root"];base=px(project(root,datum["camera"]))
  for offset,color,axis in (((.2,0,0),(0,0,255),"X"),((0,.2,0),(0,255,0),"Y"),((0,0,.2),(255,0,0),"Z")):
   end=px(project(tuple(root[i]+offset[i] for i in range(3)),datum["camera"]))
   cv2.line(frame,base,end,color,1);cv2.putText(frame,axis,end,cv2.FONT_HERSHEY_SIMPLEX,.3,color,1)
  for leg in actor["legs"]:
   points=leg["points"]
   curve=[px(points[x]["uv"]) for x in ("hip","knee","ankle")]
   color=(100,250,250) if leg["id"]=="Left" else (250,180,80)
   cv2.polylines(frame,[np.array(curve,dtype=np.int32)],False,color,2)
   for key in ("hip","knee","ankle","heel","toe"):
    spot=px(points[key]["uv"]);cv2.circle(frame,spot,3,color,-1)
    if key=="knee":cv2.putText(frame,leg["id"][0]+"K",spot,cv2.FONT_HERSHEY_SIMPLEX,.36,(255,255,255),1)
   cv2.line(frame,px(points["heel"]["uv"]),px(points["toe"]["uv"]),color,2)
   if leg["stance_label"]=="stance":cv2.circle(frame,px(points["heel"]["uv"]),6,(255,0,255),1)
 return frame
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--artifact",required=True);a.add_argument("--profile",choices=sorted(EXPECTED),required=True);a.add_argument("--out",required=True)
 o=a.parse_args();root=Path(o.artifact);out=Path(o.out);out.mkdir(parents=True,exist_ok=True)
 source_file=root/"source.json";source=json.loads(source_file.read_text())
 native=json.loads((root/"rendered"/"native_render_receipt.json").read_text())
 if native.get("source_motion_sha256")!=sha(source_file) or native.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
  raise ValueError("W8C_GT_SOURCE_CUSTODY")
 residuals=camera_receipt(source,native)
 for camera in CAMERAS:
  clean=root/"rendered"/(camera+".mp4")
  if sha(clean)!=EXPECTED[o.profile][camera]:raise ValueError("W8C_CLEAN_VIDEO_SHA")
  cap=cv2.VideoCapture(str(clean));rows=sidecar(source,camera)
  review=out/(camera+"-QA-only.mp4")
  with tempfile.TemporaryDirectory(prefix="w8cqa-") as temp:
   for i,row in enumerate(rows):
    ok,frame=cap.read()
    if not ok or frame.shape[:2]!=(360,640):raise ValueError("W8C_CLEAN_DECODE_OR_CLOCK")
    if not cv2.imwrite(str(Path(temp)/f"frame_{i:03d}.png"),draw(frame,row)):raise ValueError("W8C_QA_FRAME_WRITE")
   if cap.read()[0]:raise ValueError("W8C_EXTRA_CLEAN_FRAMES")
   cap.release()
   subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-framerate","12",
     "-i",str(Path(temp)/"frame_%03d.png"),"-c:v","libx264","-pix_fmt","yuv420p",str(review)],check=True,timeout=90)
  if sha(review)==sha(clean):raise ValueError("W8C_QA_OUTPUT_SAME_AS_CLEAN")
  (out/(camera+".jsonl")).write_text(chr(10).join(json.dumps(x,sort_keys=True) for x in rows)+chr(10))
  (out/(camera+"-manifest.json")).write_text(json.dumps({
   "schema":"scp.visualqa_w8c.debug_manifest.v1","profile":o.profile,
   "camera":camera,"source_sha256":sha(source_file),"clean_video_sha256":sha(clean),
   "qa_only_video_sha256":sha(review),"clean_input_modified":False,
   "camera_independent_xyz_to_uv_max_error":residuals[camera],
   "original_native_camera_probe_tick":0 if camera=="OriginalFront" else 23,
   "rendered_behavior":"NOT_EVALUATED_USING_OVERLAY",
   "anatomy":"UNKNOWN_NO_APPROVED_HUMAN_JCS_OR_RIG"},indent=2,sort_keys=True)+chr(10))
 print("W8C_ANNOTATED_QA_ONLY_NOT_ACCEPTANCE",o.profile,residuals)
if __name__=="__main__":main()
