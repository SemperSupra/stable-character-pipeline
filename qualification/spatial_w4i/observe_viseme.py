"""Independent source annotation→real lossless video, native 3D pose and PCM oracle."""
import array,hashlib,json,math,subprocess,sys,wave
from pathlib import Path
FS=48000;FPS=24;FRAMES=48
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cmd(x):return subprocess.check_output(x,stderr=subprocess.PIPE,timeout=120)
def inspect(d,out):
 root=Path(d);p=json.loads((root/"annotation.json").read_text())
 r=json.loads((root/"native_pose.json").read_text())
 if p["schema"]!="scp.av_presentation.v1" or p["rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC" or r["rights"]!=p["rights"]:
  raise ValueError("RIGHTS_CONTRACT")
 if len(p["cues"])!=9 or len(r["jaw_pose"])!=FRAMES or r["audio_samples"]!=96000 or r["frames"]!=FRAMES:raise ValueError("CLOCK_SOURCE_COUNT")
 if sha(root/"annotation.json")!=r["annotation_sha256"]:raise ValueError("SOURCE_PACKET_SHA")
 if p["source_sha256"]!=r["source_sha256"]:raise ValueError("SOURCE_ORIGIN_HASH")
 for index,pose in enumerate(r["jaw_pose"]):
  s=2000*index
  keys=p["poses"]
  if s<24000:expected=0.
  elif s<=30000:expected=(s-24000)/6000
  elif s<36000:expected=1.
  else:expected=0.
  if pose["frame"]!=index or pose["sample"]!=s or abs(pose["jaw_open"]-expected)>1e-12 or abs(pose["jaw_mesh_z"]-(.33-.22*expected))>1e-10:
   raise ValueError("SOURCE_INDEPENDENT_3D_JAW_POSE")
 media=root/"viseme_annotated_original_master.mkv"
 if sha(media)!=r["media_sha256"] or sha(root/"original_synthetic_annotated_voice.wav")!=r["wav_sha256"]:
  raise ValueError("MEDIA_BYTE_SOURCE_SHA")
 raw=cmd(["ffmpeg","-loglevel","error","-i",str(media),"-f","rawvideo","-pix_fmt","rgb24","-fps_mode","passthrough","pipe:1"])
 baseline=cmd(["ffmpeg","-loglevel","error","-framerate","24","-i",str(root/"frames"/"%04d.png"),"-f","rawvideo","-pix_fmt","rgb24","-fps_mode","passthrough","pipe:1"])
 expected_bytes=FRAMES*160*90*3
 if len(raw)!=expected_bytes or raw!=baseline:raise ValueError("ACTUAL_VIDEO_PIXELS_NOT_SOURCE")
 pix=160*90*3
 if raw[12*pix:13*pix]==raw[15*pix:16*pix] or raw[15*pix:16*pix]==raw[18*pix:19*pix]:
  raise ValueError("MOUTH_OPENING_INVISIBLE")
 v=json.loads(cmd(["ffprobe","-v","error","-select_streams","v:0","-show_entries","frame=best_effort_timestamp_time","-of","json",str(media)]))
 pts=[float(x["best_effort_timestamp_time"]) for x in v["frames"]]
 if len(pts)!=FRAMES:raise ValueError("VIDEO_FRAME_COUNT")
 error=max(abs(t-i/FPS) for i,t in enumerate(pts))
 if error>0.0011:raise ValueError("PTS_QUANTIZATION")
 with wave.open(str(root/"original_synthetic_annotated_voice.wav"),"rb") as f:
  if (f.getframerate(),f.getnchannels(),f.getsampwidth(),f.getnframes())!=(FS,1,2,96000):raise ValueError("WAV_SOURCE_FORMAT")
  b=f.readframes(96000)
 pcm=cmd(["ffmpeg","-loglevel","error","-i",str(media),"-map","0:a:0","-f","s16le","-acodec","pcm_s16le","pipe:1"])
 if pcm!=b or len(pcm)!=96000*2:raise ValueError("DECODED_PCM_NOT_BYTE_IDENTICAL")
 a=array.array("h");a.frombytes(pcm)
 if sys.byteorder!="little":raise ValueError("ENDIAN")
 if any(a[i]!=0 for i in range(0,24000)) or any(a[i]!=0 for i in range(36000,96000)):raise ValueError("SPURIOUS_SPEECH_SAMPLE")
 if not any(a[i]!=0 for i in range(24000,30000)) or not any(a[i]!=0 for i in range(30000,36000)):raise ValueError("MISSING_SOURCE_TONE")
 receipt={"schema":"scp.w4i_independent_native_viseme.v1","status":"PASS_ORIGINAL_SYNTHETIC_3D_JAW_AV","source_rights":p["rights"],"native_media_sha256":sha(media),"frames":FRAMES,"pcm_sample_frames":96000,"visible_jaw_change":True,"max_video_pts_error_seconds":error,"pcm_byte_identical":True,"pixel_byte_identical":True,"scope":"NOT_REAL_SPEECH_NOT_PERCEPTUAL_LIP_SYNC"}
 Path(out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W4I_INDEPENDENT_VISUAL_PCM_PASS frames=48 pcm=96000 diff_samples=0")
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: observe_viseme.py DIR RECEIPT")
 try:inspect(sys.argv[1],sys.argv[2])
 except Exception as e:
  Path(sys.argv[2]).write_text(json.dumps({"status":"FAIL","first_failure":str(e)})+"\n")
  print("W4I_VISUAL_PCM_FIRST_FAILURE",e,file=sys.stderr);raise
