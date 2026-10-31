#!/usr/bin/env python3
"""R21 source-bound original synthetic 2D actor approach witness (NOT gait QA).

Read original public-synthetic W7A 24-frame source plus two R9 H264 images.
Match per-frame colour identities as source-safe fixtures only; no arbitrary
human/identity recognition, anatomical JCS, fullbody or photoreal acceptance.
"""
import argparse,json,subprocess,sys
from pathlib import Path
ACTORS=("CobaltOriginal","MarigoldOriginal")
CAMERAS=("OriginalFront","OriginalOblique")
class MotionError(ValueError):pass
def need(x,code):
 if not x:raise MotionError(code)
def centroid(frame,width,height,actor,min_pixels=500):
 need(len(frame)==width*height*3,"RAW_RGB_SIZE_INVALID")
 total=0;acc=0
 for i in range(width*height):
  r,g,b=frame[3*i],frame[3*i+1],frame[3*i+2]
  if actor=="blue":yes=b>r*1.22 and b>g*1.08 and b>70 and g>30
  elif actor=="brown":yes=r>g*1.25 and r>b*1.21 and r>65 and g>24
  else:raise MotionError("UNKNOWN_SYNTHETIC_COLOUR")
  if yes:
   total+=1;acc+=i%width
 need(total>=min_pixels,"INSUFFICIENT_OR_MISSING_SYNTHETIC_ACTOR_PIXELS")
 return acc/total
def geometry(source):
 need(source.get("rights")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC" and
  source.get("fps_num")==12 and source.get("fps_den")==1,
  "WRONG_ORIGINAL_SOURCE_OR_CLOCK")
 actors=source.get("actors")
 need(type(actors) is list and [a.get("id") for a in actors]==list(ACTORS),
  "SOURCE_ACTOR_IDENTITY_NOT_BOUND")
 for a in actors:
  frames=a.get("frames")
  need(type(frames) is list and len(frames)==24 and
   all(fr.get("index")==i and fr.get("time_num")==i and fr.get("time_den")==12 for i,fr in enumerate(frames)),
   "INCOMPLETE_SOURCE_FRAME_CLOCK")
 gaps=[]
 for frame in (0,23):
  a,b=(float(x["frames"][frame]["root_x"]) for x in actors)
  gaps.append(abs(a-b))
 need(gaps[0]-gaps[1]>0.5,"NO_SIGNIFICANT_ROOT_APPROACH")
 return gaps
def raw_h264(video):
 meta=json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
  "-show_entries","stream=width,height,nb_frames,r_frame_rate,codec_name","-of","json",str(video)],timeout=15))
 x=meta["streams"][0]
 need((x.get("width"),x.get("height"),x.get("nb_frames"),x.get("r_frame_rate"),x.get("codec_name"))
      ==(640,360,"24","12/1","h264"),"ORIGINAL_VIDEO_CODEC_FRAME_CLOCK")
 raw=subprocess.check_output(["ffmpeg","-hide_banner","-loglevel","error","-i",str(video),
  "-f","rawvideo","-pix_fmt","rgb24","-"],timeout=50)
 size=640*360*3
 need(len(raw)==24*size,"DECODED_FRAME_COUNT_MISMATCH")
 return [raw[:size],raw[23*size:24*size]]
def source_bound_approach(source,video_paths):
 roots=geometry(source)
 cameras={}
 for name in CAMERAS:
  frames=raw_h264(video_paths[name])
  gap=[]
  for frame in frames:
   blue=centroid(frame,640,360,"blue")
   brown=centroid(frame,640,360,"brown")
   need(blue<brown,"SOURCE_SYNTHETIC_COLOUR_ORDER_CHANGED")
   gap.append(brown-blue)
  change=gap[0]-gap[1]
  need(change>40,"ORIGINAL_TWO_VIEW_PIXEL_APPROACH_UNQUALIFIED")
  cameras[name]={"first_pixel_gap":round(gap[0],3),
    "last_pixel_gap":round(gap[1],3),"pixel_convergence":round(change,3)}
 return {"schema":"scp.r21.synthetic_2d_approach.v1","scope":"PUBLIC_ORIGINAL_SYNTHETIC_ONLY",
  "root_world_gap":roots,"views":cameras,
  "visual_evidence":"PASS_SYNTHETIC_TWO_COLOUR_APPROACH_ONLY",
  "human_behavior":"FAIL_ABSTRACT_LIMBS_ONLY",
  "biological_jcs_rom":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM",
  "r009_private":"HELD_R009_NOT_RUN_NOT_ADMITTED"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--source",type=Path,required=True)
 p.add_argument("--media",type=Path,required=True)
 a=p.parse_args()
 try:
  source=json.loads(a.source.read_bytes())
  report=source_bound_approach(source,{cam:a.media/"r9-cli"/"attempt-0001"/"forward"/"rendered"/(cam+".mp4") for cam in CAMERAS})
 except (OSError,MotionError,subprocess.CalledProcessError,ValueError,KeyError,IndexError) as exc:
  print("R21_FAIL_CLOSED:"+str(exc),file=sys.stderr);return 2
 print(json.dumps(report,sort_keys=True,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
