"""W6-E3 independent exact source MP4 RGB -> FFV1 24fps 2x decode and PCM."""
import hashlib,json,subprocess,sys,wave
from fractions import Fraction
from pathlib import Path
W,H=400,240
def call(args):return subprocess.check_output(args,stderr=subprocess.PIPE)
def stream(video,kind):
 return json.loads(call(["ffprobe","-v","error","-show_streams","-of","json",str(video)]))["streams"]
def rgb(video):
 return call(["ffmpeg","-v","error","-i",str(video),"-map","0:v:0","-pix_fmt","rgb24","-f","rawvideo","-"])
def pcm(video):
 return call(["ffmpeg","-v","error","-i",str(video),"-map","0:a:0","-ac","1","-ar","48000","-c:a","pcm_s16le","-f","s16le","-"])
def verify(folder):
 p=Path(folder)
 m=json.loads((p/"original_48k_clock_manifest.json").read_text())
 r=json.loads((p/"multiview_render_receipt.json").read_text())
 if m["source_rights"]!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or m["profile"]!=r["profile"] or m["source_w6_render_receipt_sha256"]!=hashlib.sha256((p/"multiview_render_receipt.json").read_bytes()).hexdigest():
  raise ValueError("E3_SOURCE_PROVENANCE")
 with wave.open(str(p/"original_48k_synthetic_clock.wav"),"rb") as f:
  if (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())!=(1,2,48000,96000):
   raise ValueError("E3_SOURCE_PCM_SETTINGS")
  source_pcm=f.readframes(96000)
 if hashlib.sha256(source_pcm).hexdigest()!=m["source_wav_pcm_sha256"]:
  raise ValueError("E3_SOURCE_PCM_SHA")
 checks={}
 n=W*H*3
 for view in ("front","oblique"):
  source=p/("original_"+view+"_surrogate.mp4")
  mux=p/("actual_"+view+"_source_AV.nut")
  if hashlib.sha256(source.read_bytes()).hexdigest()!=m["source_view_mp4_sha256"][view]:
   raise ValueError("E3_SOURCE_ACTUAL_VIDEO_SHA")
  ss=stream(source,"video");ms=stream(mux,"video")
  sv=[x for x in ss if x["codec_type"]=="video"]
  mv=[x for x in ms if x["codec_type"]=="video"]
  ma=[x for x in ms if x["codec_type"]=="audio"]
  if len(sv)!=1 or len(mv)!=1 or len(ma)!=1 or sv[0]["r_frame_rate"]!="12/1" or mv[0]["r_frame_rate"]!="24/1" or mv[0]["codec_name"]!="ffv1":
   raise ValueError("E3_REAL_VIDEO_CLOCK")
  original=rgb(source);decoded=rgb(mux)
  if len(original)!=24*n or len(decoded)!=48*n:
   raise ValueError("E3_DECODED_SOURCE_FRAME_COUNTS")
  bad=[]
  for i in range(24):
   expected=original[i*n:(i+1)*n]
   if decoded[(2*i)*n:(2*i+1)*n]!=expected or decoded[(2*i+1)*n:(2*i+2)*n]!=expected:
    bad.append(i)
  if bad:raise ValueError("E3_EXACT_SOURCE_FRAME_DUPLICATION_MISMATCH_"+str(bad[:6]))
  actual_pcm=pcm(mux)
  if actual_pcm!=source_pcm:raise ValueError("E3_DECODED_PCM_SOURCE_BYTE_MISMATCH")
  pts=json.loads(call(["ffprobe","-v","error","-select_streams","v:0","-show_frames","-show_entries","frame=best_effort_timestamp","-of","json",str(mux)]))["frames"]
  if len(pts)!=48:raise ValueError("E3_PTS_COVERAGE")
  rate=Fraction(mv[0]["time_base"])
  worst=max(abs(Fraction(int(x["best_effort_timestamp"]))*rate-Fraction(i,24)) for i,x in enumerate(pts))
  if worst>Fraction(1,2000000):
   raise ValueError("E3_NATIVE_OUTPUT_PTS_DRIFT")
  checks[view]={"video_src_sha256":m["source_view_mp4_sha256"][view],
    "mux_sha256":hashlib.sha256(mux.read_bytes()).hexdigest(),
    "decoded_source_frames":24,"decoded_output_frames":48,
    "decoded_pcm_samples":96000,"source_byte_exact_repetition":True,
    "pts_tick_max_fraction":str(worst),"video_stream_time_base":str(rate)}
 out={"schema":"scp.walk_w6e3_actual_scene_av_decode.v1",
  "status":"PASS_ACTUAL_SURROGATE_SOURCE_RGB_12_TO_24_AND_48K_PCM",
  "source_rights":m["source_rights"],"profile":m["profile"],
  "source_sha256":r["source_sha256"],"views":checks,
  "audio_source":"ARTIFICIAL_CLOCK_NOT_SPEECH_OR_FOLEY",
  "human_visual_model":"NOT_RUN_ORIGINAL_L1_STILL_RED",
  "scope":"REAL_MULTICAMERA_SOURCE_VIDEO_TIMING_NOT_HUMAN_LIPS_OR_PRIVATE_R009"}
 (p/"third_actual_multiview_av_receipt.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
 print("W6E3_ACTUAL_SOURCE_AV_AND_PCM_DECODE_PASS",m["profile"],checks)
if __name__=="__main__":verify(sys.argv[1])
