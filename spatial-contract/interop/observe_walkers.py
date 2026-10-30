"""Independent decoder audit of all 144 synthetic 2D walking frames and
12 original stereo foot-contact audio samples. Not a perceptual test.
"""
import hashlib,json,pathlib,struct,subprocess,sys,wave
FPS=24;FRAMES=144;RATE=48000;WIDTH=160;HEIGHT=90
LEFT=tuple(range(12,144,24));RIGHT=tuple(range(6,144,24))
def run(*args):
 r=subprocess.run(args,capture_output=True,timeout=100)
 if r.returncode:raise ValueError("FIRST_FAILURE "+repr(args)+" "+r.stderr.decode(errors="replace")[-1200:])
 return r.stdout
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def wave_pcm(path):
 with wave.open(str(path),"rb") as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(2,2,RATE,288000):
   raise ValueError("not original six-second stereo 48k PCM16")
  return w.readframes(288000)
def inspect(root,out):
 root=pathlib.Path(root);m=json.loads((root/"manifest.json").read_text())
 if m["schema"]!="spatial_audio.w4g_animated_walkers.v1" or m["source_rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC":
  raise ValueError("source rights/schema")
 original=root/"original_two_walkers.rgb"
 wav=root/"original_stereo_contacts.wav"
 master=root/"two_walkers_lossless.mkv"
 mobile=root/"two_walkers_mobile.mp4"
 for p,key in ((original,"original_raw_rgb_sha256"),(wav,"original_source_wav_sha256"),
  (master,"lossless_master_sha256"),(mobile,"mobile_candidate_sha256")):
  if sha(p)!=m[key]:raise ValueError("source/input/output SHA drift")
 origpcm=wave_pcm(wav)
 decoded=run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i",str(master),
  "-map","0:a:0","-ac","2","-ar","48000","-acodec","pcm_s16le","-f","s16le","-")
 if decoded!=origpcm:raise ValueError("lossless mux changed contact samples")
 events=[]
 for sample in range(288000):
  a,b=struct.unpack_from("<hh",decoded,4*sample)
  if a:events.append((sample,0,a))
  if b:events.append((sample,1,b))
 expected=sorted([(f*2000,0,16000) for f in LEFT]+[(f*2000,1,12000) for f in RIGHT])
 if events!=expected:raise ValueError(f"wrong exact sample/channels {events[:15]}")
 raw=run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i",str(master),
  "-map","0:v:0","-pix_fmt","rgb24","-f","rawvideo","-")
 originalRGB=original.read_bytes()
 pixels=WIDTH*HEIGHT*3
 if len(raw)!=FRAMES*pixels or raw!=originalRGB:
  raise ValueError("lossless decoded 144 frame pixels differ from authored frames")
 markerLeft=[];markerRight=[];leftheads=[];rightheads=[]
 for f in range(FRAMES):
  frame=raw[f*pixels:(f+1)*pixels]
  leftpixel=tuple(frame[(3*WIDTH+3)*3:(3*WIDTH+3)*3+3])
  rightpixel=tuple(frame[(3*WIDTH+156)*3:(3*WIDTH+156)*3+3])
  if leftpixel==(0,255,255):markerLeft.append(f)
  elif leftpixel!=(20,31,44):raise ValueError("unexpected left top marker")
  if rightpixel==(255,0,255):markerRight.append(f)
  elif rightpixel!=(20,31,44):raise ValueError("unexpected right top marker")
  # Independently inspect actual head position from rendered pixels.
  ly=[x for x in range(0,80) if tuple(frame[(33*WIDTH+x)*3:(33*WIDTH+x)*3+3])==(100,210,250)]
  ry=[x for x in range(80,WIDTH) if tuple(frame[(33*WIDTH+x)*3:(33*WIDTH+x)*3+3])==(255,160,180)]
  if not ly or not ry:raise ValueError("missing actual actor head geometry")
  leftheads.append(round(sum(ly)/len(ly)));rightheads.append(round(sum(ry)/len(ry)))
 if markerLeft!=list(LEFT) or markerRight!=list(RIGHT):raise ValueError("one or more frame contact markers missing")
 if not(leftheads[-1]>leftheads[0]+25 and rightheads[-1]<rightheads[0]-25):
  raise ValueError("actual two walkers failed to move towards each other")
 probe=json.loads(run("ffprobe","-hide_banner","-loglevel","error","-select_streams","v:0",
  "-show_streams","-show_frames",
  "-show_entries","stream=codec_name,width,height:frame=media_type,best_effort_timestamp_time",
  "-of","json",str(master)))
 vframes=[x for x in probe["frames"] if x.get("media_type")=="video"]
 if len(vframes)!=FRAMES or probe["streams"][0]["codec_name"]!="ffv1":
  raise ValueError("wrong actual lossless video frame count")
 pts=[float(x["best_effort_timestamp_time"]) for x in vframes]
 err=max(abs(pts[i]-i/FPS) for i in range(FRAMES))
 if err>0.0011:raise ValueError("video PTS mismatch")
 streams=json.loads(run("ffprobe","-v","error","-show_streams","-of","json",str(mobile)))["streams"]
 if not {"h264","aac"}.issubset(set(x["codec_name"] for x in streams)):
  raise ValueError("mobile codec candidate wrong")
 result=dict(schema="spatial_audio.w4g_walking_contact_independent.v1",
  status="PASS_SYNTHETIC_TWO_WALKERS_REAL_AV",
  source_rights=m["source_rights"],video_frames=FRAMES,frame_rate=24,
  PCM_sample_rate=RATE,PCM_contact_event_count=len(events),
  exact_stereo_contact_sample_error=0,
  left_contact_frames=markerLeft,right_contact_frames=markerRight,
  left_head_start_end=[leftheads[0],leftheads[-1]],
  right_head_start_end=[rightheads[0],rightheads[-1]],
  max_video_pts_error_seconds=err,
  original_rgb_sha256=sha(original),
  lossless_decoded_rgb_sha256=hashlib.sha256(raw).hexdigest(),
  lossless_decoded_pcm_sha256=hashlib.sha256(decoded).hexdigest(),
  mp4_mobile_candidate_sha256=sha(mobile),
  not_qualified=["REAL_MMD_RIG","TRUE_WALK_KINEMATICS","GROUND_REACTION_FORCE",
  "FOLEY_ACOUSTIC_REALISM","HRTF","REAL_CHARACTER_IDENTITY","IPHONE_LISTENING"])
 pathlib.Path(out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("W4G_WALKING_INDEPENDENT_REAL_AV_PASS frames=144 contacts=12 sample_error=0",flush=True)
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: observe_walkers.py ORIGINAL_DIR RECEIPT.json")
 try:inspect(sys.argv[1],sys.argv[2])
 except Exception as e:
  pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(status="FAIL",first_failure=str(e)),indent=2)+"\n")
  print("W4G_WALKER_FIRST_FAILURE",e,file=sys.stderr);raise
