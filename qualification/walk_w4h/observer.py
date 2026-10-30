"""Independent complete original Blender-3D pixel and PCM decoder (not biomechanical oracle)."""
import array,hashlib,json,math,pathlib,subprocess,sys,wave

FS,FPS,FRAMES=48000,12,72
CUES=[12000+24000*i for i in range(12)]
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def command(parts):
 return subprocess.check_output(parts,stderr=subprocess.PIPE,timeout=120)
def raw_frames(path,still=False):
 parts=["ffmpeg","-hide_banner","-loglevel","error"]
 if still:parts+=["-framerate","12"]
 parts+=["-i",str(path),"-f","rawvideo","-pix_fmt","rgb24","-fps_mode","passthrough","pipe:1"]
 return command(parts)
def inspect(directory,receipt_path):
 root=pathlib.Path(directory)
 r=json.loads((root/"w4h_3d_source_receipt.json").read_text())
 if r["schema"]!="scp.spatial_w4h_original_3d_av.v1" or r["source_rights"]!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
  raise ValueError("SOURCE_RIGHTS_SCHEMA")
 if r["contact_authority"]!="SELF_AUTHORED_ANNOTATION_NOT_GEOMETRY_DETECTED":
  raise ValueError("CONTACT_ORIGIN_FALSE_CLAIM")
 if r["video_frames"]!=FRAMES or r["audio_hz"]!=FS or r["audio_samples"]!=FS*6 or r["stereo_foley_source_samples"]!=CUES:
  raise ValueError("TIMEBASE_OR_CUE_PLAN")
 positions=r["actor_root_x"]
 if len(positions)!=FRAMES or not all(a[0]<a[1] for a in positions):
  raise ValueError("3D_SOURCE_ROLES")
 if not all(positions[i+1][0]>positions[i][0] and positions[i+1][1]<positions[i][1] for i in range(FRAMES-1)):
  raise ValueError("WORLD_APPROACH_MOTION")
 media=root/"original_3d_camera_foley_master.mkv"
 source_audio=root/"original_stereo_foley.wav"
 if digest(media)!=r["actual_media_sha256"] or digest(source_audio)!=r["source_audio_sha256"]:
  raise ValueError("SOURCE_CONTENT_HASH")
 video=raw_frames(media)
 source=raw_frames(root/"frames"/"%04d.png",True)
 expected=FRAMES*160*90*3
 if len(video)!=expected or len(source)!=expected or video!=source:
  raise ValueError("LOSSLESS_INDEPENDENT_RGB_FRAME_MISMATCH")
 if video[:160*90*3]==video[-160*90*3:]:
  raise ValueError("NO_VISIBLE_3D_ACTOR_MOVEMENT")
 pts=json.loads(command(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
 "frame=best_effort_timestamp_time","-of","json",str(media)]))
 timestamps=[float(f["best_effort_timestamp_time"]) for f in pts["frames"]]
 if len(timestamps)!=FRAMES or max(abs(v-i/FPS) for i,v in enumerate(timestamps))>0.0011:
  raise ValueError("VIDEO_FRAME_PTS")
 with wave.open(str(source_audio),"rb") as w:
  if w.getnchannels()!=2 or w.getsampwidth()!=2 or w.getframerate()!=FS or w.getnframes()!=FS*6:
   raise ValueError("SOURCE_AUDIO_CONTRACT")
  source_pcm=w.readframes(w.getnframes())
 decoded_pcm=command(["ffmpeg","-hide_banner","-loglevel","error","-i",str(media),
 "-map","0:a:0","-f","s16le","-acodec","pcm_s16le","pipe:1"])
 if len(decoded_pcm)!=FS*6*2*2 or source_pcm!=decoded_pcm:raise ValueError("AUDIO_PCM_NOT_BYTE_IDENTICAL")
 pcm=array.array("h");pcm.frombytes(decoded_pcm)
 if sys.byteorder!="little":raise ValueError("PCM_PLATFORM_ENDIAN")
 active=[(sample,ch) for sample in range(FS*6) for ch in range(2) if pcm[2*sample+ch]!=0]
 expected_active={(start+j,i%2) for i,start in enumerate(CUES) for j in range(32)}
 if set(active)!=expected_active:raise ValueError("FOLEY_SAMPLE_OR_STEREO_CHANNEL_MISMATCH")
 result={"schema":"scp.w4h_3d_av_independent.v1","status":"PASS_NATIVE_3D_CAMERA_ANNOTATED_FOLEY_REAL_AV",
 "frame_count":FRAMES,"pcm_samples":FS*6,"event_count":len(CUES),
 "pcm_byte_identical":True,"all_video_pixels_identical":True,
 "max_pts_error_sec":max(abs(v-i/FPS) for i,v in enumerate(timestamps)),
 "lossless_media_sha256":digest(media),
 "limitations":["ANNOTATED_CONTACT_ONLY","NO_HEEL_TOE_GEOMETRY_OR_IK_EQUIVALENCE","NOT_PRIVATE_MVP"]}
 pathlib.Path(receipt_path).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 print("W4H_INDEPENDENT_NATIVE_3D_CAMERA_FOLEY_PASS frames=72 events=12 sample_drift=0")
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: observer.py SOURCE_FOLDER OUTPUT.json")
 try:inspect(sys.argv[1],sys.argv[2])
 except Exception as e:
  pathlib.Path(sys.argv[2]).write_text(json.dumps({"status":"FAIL","first_failure":str(e)})+"\n")
  print("W4H_A0_FIRST_FAILURE",e,file=sys.stderr);raise
