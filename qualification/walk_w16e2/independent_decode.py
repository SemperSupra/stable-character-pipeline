"""Independent ffmpeg decoded source RGB, PCM and Decimal frame PTS verification."""
import argparse,hashlib,json,subprocess
from decimal import Decimal
from pathlib import Path
W,H=128,72
def call(args):return subprocess.check_output(args,stderr=subprocess.PIPE)
def verify(path):
 p=Path(path);src=json.loads((p/"source_manifest.json").read_text())
 if src["source_rights"]!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":raise ValueError("SOURCE_RIGHTS")
 mux=p/"original_mux.mkv"
 i=json.loads(call(["ffprobe","-v","error","-show_streams","-of","json",str(mux)]))["streams"]
 vs=[x for x in i if x["codec_type"]=="video"]
 als=[x for x in i if x["codec_type"]=="audio"]
 if len(vs)!=1 or len(als)!=1:raise ValueError("STREAM_COUNT")
 v,a=vs[0],als[0]
 if v["codec_name"]!="ffv1" or (v["width"],v["height"])!=(W,H) or v["avg_frame_rate"]!="24/1":
  raise ValueError("VIDEO_CODEC_CLOCK")
 if a["codec_name"]!="pcm_s16le" or a["sample_rate"]!="48000" or a["channels"]!=1:
  raise ValueError("PCM_CODEC_CLOCK")
 rgb=call(["ffmpeg","-hide_banner","-loglevel","error","-i",str(mux),"-map","0:v:0",
 "-fps_mode","passthrough","-pix_fmt","rgb24","-f","rawvideo","-"])
 n=W*H*3
 if len(rgb)!=48*n:raise ValueError("FRAME_COUNT")
 digests=[hashlib.sha256(rgb[i*n:(i+1)*n]).hexdigest() for i in range(48)]
 if digests!=src["frame_rgb_sha256"]:raise ValueError("DECODED_PIXEL_MISMATCH")
 for i in range(2,48,2):
  if digests[i]==digests[i-2] or digests[i]!=digests[i+1]:raise ValueError("SOURCE_FREEZE_OR_DUPLICATE")
 pcm=call(["ffmpeg","-hide_banner","-loglevel","error","-i",str(mux),"-map","0:a:0",
 "-ac","1","-ar","48000","-c:a","pcm_s16le","-f","s16le","-"])
 if len(pcm)!=192000 or hashlib.sha256(pcm).hexdigest()!=src["source_pcm_sha256"]:
  raise ValueError("PCM_BYTE_MISMATCH")
 frames=json.loads(call(["ffprobe","-v","error","-select_streams","v:0",
 "-show_frames","-show_entries","frame=best_effort_timestamp_time","-of","json",str(mux)]))["frames"]
 if len(frames)!=48:raise ValueError("PTS_COVERAGE")
 errors=[abs(Decimal(f["best_effort_timestamp_time"])-Decimal(i)/Decimal(24)) for i,f in enumerate(frames)]
 if max(errors)>Decimal("0.0000005"):raise ValueError("PTS_DRIFT")
 r={"schema":"scp.walk_w16e2_decode.v1","status":"PASS_SOURCE_ONLY_REAL_FFV1_PCM_MUX",
 "source_rights":src["source_rights"],"profile":src["profile"],
 "rgb_frames":48,"decoded_pcm_samples":96000,"source_motion_frames":24,
 "maximum_pts_error_decimal":str(max(errors)),
 "native_mux_sha256":hashlib.sha256(mux.read_bytes()).hexdigest(),
 "scope":"NOT_C3_VIDEO_NOT_SPEECH_NOT_REAL_LIP_SYNC_NOT_PRIVATE"}
 (p/"decoded_receipt.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
 print("W16E2_EXACT_DECODE_PASS",json.dumps(r,sort_keys=True))
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--folder",required=True)
 verify(ap.parse_args().folder)
