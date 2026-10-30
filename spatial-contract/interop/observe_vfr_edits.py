"""Separate-worker decoded full VFR video, PTS and original PCM source edit oracle."""
import hashlib,json,pathlib,struct,subprocess,sys,wave
from fractions import Fraction
RATE=48000
ORIGINAL=[24000,48000,84000,108000,156000]
AMPS=[10000,12000,14000,16000,18000]
DEST=[24000,48000,84000,132000]
def run(*args):
 r=subprocess.run(args,capture_output=True,timeout=100)
 if r.returncode:raise ValueError("FIRST_FAILURE "+repr(args)+" "+r.stderr.decode(errors="replace")[-1200:])
 return r.stdout
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def getwave(p,frames):
 with wave.open(str(p),"rb") as w:
  if (w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes())!=(1,2,RATE,frames):
   raise ValueError("bad original PCM framing")
  b=w.readframes(frames)
 if len(b)!=frames*2:raise ValueError("truncated audio")
 return b
def inspect(root,out):
 root=pathlib.Path(root)
 m=json.loads((root/"source_manifest.json").read_text())
 if m["schema"]!="spatial_audio.w4g_vfr_cut_native.v1" or m["source_rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC":
  raise ValueError("source rights/schema mismatch")
 src=root/"original_4s.wav";edit=root/"cut_only_3s.wav";mux=root/"vfr_cut_master.mkv"
 for path,key in ((src,"original_sha256"),(edit,"edited_sha256"),(mux,"master_sha256")):
  if sha(path)!=m[key]:raise ValueError("source/media hash")
 original=getwave(src,192000);reference=getwave(edit,144000)
 if reference!=original[:72000*2]+original[96000*2:168000*2]:raise ValueError("cut-only byte provenance not exact")
 nonzero=[(i,struct.unpack_from("<h",original,i*2)[0]) for i in range(192000)
          if original[i*2:i*2+2]!=b"\0\0"]
 if nonzero!=list(zip(ORIGINAL,AMPS)):raise ValueError("invalid original event inventory")
 decoded=run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i",str(mux),
             "-map","0:a:0","-ac","1","-ar","48000","-acodec","pcm_s16le","-f","s16le","-")
 if decoded!=reference:raise ValueError("decoded AV lost exact original PCM sample")
 actual=[(i,struct.unpack_from("<h",decoded,2*i)[0]) for i in range(144000)
       if decoded[2*i:2*i+2]!=b"\0\0"]
 if actual!=list(zip(DEST,(10000,12000,16000,18000))):raise ValueError("drop/rebase of cue incorrect")
 v=json.loads(run("ffprobe","-v","error","-select_streams","v:0","-show_streams","-show_frames",
   "-show_entries","stream=codec_name,width,height:frame=media_type,best_effort_timestamp_time",
   "-of","json",str(mux)))
 frames=[f for f in v["frames"] if f.get("media_type")=="video"]
 if len(frames)!=50 or len(v["streams"])!=1 or v["streams"][0]["codec_name"]!="ffv1":
  raise ValueError("wrong actual VFR video frames / codec")
 pts=[float(x["best_effort_timestamp_time"]) for x in frames]
 ref_pts=[Fraction(x,1000) for x in m["video_frame_pts_ms"]]
 if len(ref_pts)!=50 or ref_pts[0]!=0:raise ValueError("bad expected PTS grid")
 errs=[abs(pts[i]-float(ref_pts[i])) for i in range(50)]
 if max(errs)>0.0011:raise ValueError("timebase PTS drift")
 deltas=[round((pts[i+1]-pts[i])*1000) for i in range(49)]
 if not {40,80}.issubset(set(deltas)) or any(abs((pts[i+1]-pts[i])*1000-m["video_frame_durations_ms"][i])>1.1 for i in range(49)):
  raise ValueError("not truly time-varying PTS")
 raw=run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-i",str(mux),
       "-map","0:v:0","-pix_fmt","gray","-f","rawvideo","-")
 frame_size=160*90
 if len(raw)!=frame_size*50:raise ValueError("decoded pixel count")
 white=[i for i in range(50) if sum(raw[i*frame_size:(i+1)*frame_size])/frame_size>128]
 wanted=[min(range(50),key=lambda i:abs(float(ref_pts[i])-s/RATE)) for s in DEST]
 if white!=wanted or white!=m["marker_frames"]:raise ValueError("VFR flash cannot follow audio edit cues")
 visual_errors=[abs(pts[i]-s/RATE) for i,s in zip(white,DEST)]
 if any(x>0.06+0.0011 for x in visual_errors):raise ValueError("visual cue exceeds 60ms VFR bound")
 receipt=dict(schema="spatial_audio.w4g_vfr_cut_independent.v1",
  status="PASS_ACTUAL_VFR_WITH_CUT_AUDIO",source_rights=m["source_rights"],
  original_sha256=m["original_sha256"],lossless_master_sha256=sha(mux),
  decoded_pcm_sha256=hashlib.sha256(decoded).hexdigest(),
  original_events=len(ORIGINAL),retained_events=len(actual),dropped_events=[84000],
  destination_samples=DEST,max_audio_sample_error=0,frames=len(frames),
  actual_video_pts_seconds=pts,frame_intervals_ms=sorted(set(deltas)),
  marked_video_frames=white,maximum_pts_error_seconds=max(errs),
  maximum_visual_nearest_frame_error_seconds=max(visual_errors),
  not_tested=["TIME_STRETCH","PHYSICAL_VFR_DEVICE_PLAYBACK","PERCEPTUAL_SYNC",
              "MMD_RIG","PRIVATE_CHARACTERS","AAC_PRIMING"])
 pathlib.Path(out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W4G_INDEPENDENT_VFR_AV_PASS frames=50 intervals=[40,80] cues=4 dropped=1 pcm_error=0 max_pts_error",max(errs))
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: observe_vfr_edits.py NATIVE_DIR RESULT_JSON")
 try:inspect(sys.argv[1],sys.argv[2])
 except Exception as e:
  pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(status="FAIL",first_failure=str(e)),indent=2)+"\n")
  print("W4G_VFR_FIRST_FAILURE",str(e),file=sys.stderr);raise
