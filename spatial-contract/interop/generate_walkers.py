"""Original-public two 2D articulated synthetic walking figures and stereo
foot-contact tick waveform, one authoritative 48k/24fps scene clock.
NOT human video, rigged Blender animation or motion capture.
"""
import hashlib,json,math,pathlib,struct,subprocess,sys,wave

FPS=24;FRAMES=144;RATE=48000;CHANNELS=2;WIDTH=160;HEIGHT=90
LEFT=tuple(range(12,144,24))   # 0.5,1.5,..5.5 seconds
RIGHT=tuple(range(6,144,24))  # 0.25,1.25,..5.25 seconds
BG=(20,31,44)
def shell(*a):
 r=subprocess.run(a,capture_output=True,timeout=100)
 if r.returncode:raise RuntimeError("FIRST_FAILURE "+repr(a)+" "+r.stderr.decode(errors="replace")[-1500:])
 return r.stdout.decode(errors="replace")
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def put(img,x,y,col):
 if 0<=x<WIDTH and 0<=y<HEIGHT:
  i=(y*WIDTH+x)*3
  img[i:i+3]=bytes(col)
def line(img,x0,y0,x1,y1,color):
 x0,y0,x1,y1=map(round,(x0,y0,x1,y1))
 dx=abs(x1-x0);sx=1 if x0<x1 else -1
 dy=-abs(y1-y0);sy=1 if y0<y1 else -1
 err=dx+dy
 while True:
  put(img,x0,y0,color)
  if x0==x1 and y0==y1:break
  e2=2*err
  if e2>=dy:err+=dy;x0+=sx
  if e2<=dx:err+=dx;y0+=sy
def figure(img,at,frame,side,contact):
 # Kinematic cartoon skeleton: periodic leg/arm swing, not inferred gait.
 base=33+38*(frame/(FRAMES-1)) if side=="left" else 127-38*(frame/(FRAMES-1))
 x=round(base)
 phase=2*math.pi*((frame+(0 if side=="left" else 6))%24)/24
 swing=5*math.sin(phase)
 sign=1 if side=="left" else -1
 main=(100,210,250) if side=="left" else (255,160,180)
 line(img,x,35,x,53,main)
 for dx in (-2,-1,0,1,2):
  put(img,x+dx,33,main)
  put(img,x+dx,34,main)
 line(img,x,42,x-7+swing*.35,49,main)
 line(img,x,42,x+7-swing*.35,49,main)
 line(img,x,53,x-4+swing,70,main)
 line(img,x,53,x+4-swing,70,main)
 if contact:
  # Actual foot flash is a source-authored annotation, not observed physics.
  footx=round(x+sign*5)
  for py in range(69,73):
   for px in range(footx-3,footx+4):put(img,px,py,(70,255,100))
 return x
def generate(root):
 root=pathlib.Path(root);root.mkdir(parents=True,exist_ok=False)
 audio=[0]*(FRAMES*RATE//FPS*CHANNELS)
 events=[]
 for frame in LEFT:
  sample=frame*RATE//FPS
  audio[sample*2]=16000
  events.append(dict(actor="left",frame=frame,sample=sample,channel=0,amplitude=16000))
 for frame in RIGHT:
  sample=frame*RATE//FPS
  audio[sample*2+1]=12000
  events.append(dict(actor="right",frame=frame,sample=sample,channel=1,amplitude=12000))
 events.sort(key=lambda x:x["sample"])
 wav=root/"original_stereo_contacts.wav"
 with wave.open(str(wav),"wb") as f:
  f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
  f.writeframes(struct.pack("<"+"h"*len(audio),*audio))
 rgb=root/"original_two_walkers.rgb"
 with rgb.open("wb") as f:
  for frame in range(FRAMES):
   img=bytearray(bytes(BG)*(WIDTH*HEIGHT))
   # Stylized park-like flat original ground line, not source park footage.
   line(img,0,74,WIDTH-1,74,(85,113,90))
   for actor in ("left","right"):
    contact=frame in (LEFT if actor=="left" else RIGHT)
    figure(img,0,frame,actor,contact)
    if contact:
     xstart=0 if actor=="left" else WIDTH-8
     color=(0,255,255) if actor=="left" else (255,0,255)
     for y in range(0,8):
      for x in range(xstart,xstart+8):put(img,x,y,color)
   f.write(img)
 master=root/"two_walkers_lossless.mkv"
 mobile=root/"two_walkers_mobile.mp4"
 shell("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
  "-f","rawvideo","-pixel_format","rgb24","-video_size","160x90","-framerate","24",
  "-i",str(rgb),"-i",str(wav),"-map","0:v:0","-map","1:a:0",
  "-c:v","ffv1","-c:a","pcm_s16le",str(master))
 shell("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
  "-i",str(master),"-map","0:v:0","-map","0:a:0","-c:v","libx264",
  "-preset","ultrafast","-crf","26","-pix_fmt","yuv420p",
  "-c:a","aac","-b:a","96k","-movflags","+faststart",str(mobile))
 meta=dict(schema="spatial_audio.w4g_animated_walkers.v1",
  source_rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
  video_frames=FRAMES,frame_rate="24/1",sample_rate=RATE,
  audio_samples=FRAMES*RATE//FPS,channels=CHANNELS,dimensions=[WIDTH,HEIGHT],
  original_raw_rgb_sha256=sha(rgb),original_source_wav_sha256=sha(wav),
  lossless_master_sha256=sha(master),mobile_candidate_sha256=sha(mobile),
  contact_events=events,contact_markers=dict(left=list(LEFT),right=list(RIGHT)),
  ffmpeg_version=shell("ffmpeg","-version").splitlines()[0],
  declared_limitations=["SYNTHETIC_2D_STICK_FIGURES","NOT_BLENDER_RIG",
  "NOT_ACTUAL_MOCAP","NOT_FOOT_PRESSURE_GROUND_TRUTH","NO_PRIVATE_CHARACTER_IDENTITY",
  "NO_HUMAN_PERCEPTUAL_SYNCHRONIZATION"])
 (root/"manifest.json").write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
 print("W4G_TWO_WALKERS_NATIVE_VIDEO_PASS frames=144 stereo_contact_events=12",flush=True)
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("usage: generate_walkers.py NEW_DIR")
 generate(sys.argv[1])
