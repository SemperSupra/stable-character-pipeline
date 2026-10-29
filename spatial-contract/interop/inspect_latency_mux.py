"""Fresh-worker full PCM + decoded FFV1 video audit of six latency/tail AV muxes."""
import hashlib,json,pathlib,struct,subprocess,sys,wave

N=480000
CUES=((96000,16000),(240000,10000),(479700,8000))
ECHO_AT=480100
DELAYS=(0,255,1024)
TAILS=(0,2048)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def cmd(*args):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
 if r.returncode:raise ValueError("FIRST_FAILURE "+repr(args)+" "+r.stderr.decode(errors="replace")[-1000:])
 return r.stdout
def readwave(path,frames):
 with wave.open(str(path),"rb") as f:
  if (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())!=(1,2,48000,frames):
   raise ValueError("source PCM framing")
  b=f.readframes(frames)
 if len(b)!=frames*2:raise ValueError("truncated source PCM")
 return b
def decaudio(path):
 return cmd("ffmpeg","-hide_banner","-loglevel","error","-nostdin",
  "-i",str(path),"-map","0:a:0","-ac","1","-ar","48000",
  "-acodec","pcm_s16le","-f","s16le","-")
def videohash(path):
 b=cmd("ffmpeg","-hide_banner","-loglevel","error","-nostdin",
  "-i",str(path),"-map","0:v:0","-pix_fmt","gray","-f","rawvideo","-")
 one=160*90
 if len(b)!=300*one:raise ValueError("video frame count wrong")
 marks=[i for i in range(300) if sum(b[i*one:(i+1)*one])/one>128]
 if marks!=[60,150,299]:raise ValueError(f"video cue markers not at canonical frames {marks}")
 return hashlib.sha256(b).hexdigest()
def probe(path):
 return json.loads(cmd("ffprobe","-hide_banner","-loglevel","error","-select_streams","v:0",
  "-show_frames","-show_entries","frame=best_effort_timestamp_time",
  "-of","json",str(path)))
def verify(root,out):
 root=pathlib.Path(root)
 m=json.loads((root/"manifest.json").read_text())
 if m["schema"]!="spatial_audio.w4f_latency_mux.v1" or m["rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC" or len(m["cases"])!=6:
  raise ValueError("wrong fixture rights or plan")
 orig=root/"original_source.wav"
 video=root/"original_video.mkv"
 if sha(orig)!=m["original_source_sha256"] or sha(video)!=m["original_video_sha256"]:
  raise ValueError("source custody drift")
 ref=readwave(orig,N)
 for sample,amplitude in CUES:
  if struct.unpack_from("<h",ref,sample*2)[0]!=amplitude:raise ValueError("wrong original click")
 count=sum(1 for i in range(N) if struct.unpack_from("<h",ref,i*2)[0]!=0)
 if count!=3:raise ValueError("original source has extra samples")
 control=root/"expected_reject_untrimmed_255.wav"
 if sha(control)!=m["negative_untrimmed_wav_sha256"]:raise ValueError("negative custody drift")
 bad=readwave(control,N+255)
 if struct.unpack_from("<h",bad,96000*2)[0]!=0 or struct.unpack_from("<h",bad,(96000+255)*2)[0]!=16000:
  raise ValueError("negative control failed to prove 255-sample delay")
 source_video_sha=videohash(video)
 seen=set();rows=[]
 for cell in m["cases"]:
  delay=int(cell["processor_delay_samples"]);tail=int(cell["keep_tail_samples"])
  if delay not in DELAYS or tail not in TAILS or (delay,tail) in seen:raise ValueError("bad/duplicate matrix")
  seen.add((delay,tail))
  name=f"d{delay:04d}_tail{tail:04d}"
  if cell["id"]!=name or cell["source_rights"]!="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC":
   raise ValueError("bad media rights or id")
  wav=root/(name+".wav")
  master=root/(name+".mkv")
  if sha(wav)!=cell["aligned_wav_sha256"] or sha(master)!=cell["sha256"]:
   raise ValueError("output SHA mismatch")
  local=readwave(wav,N+tail)
  native=decaudio(master)
  if len(native)!=len(local) or native!=local:
   raise ValueError(f"lossless actual mux failed PCM equality: {name}")
  for sample,amp in CUES:
   if struct.unpack_from("<h",native,2*sample)[0]!=amp:
    raise ValueError(f"audio cue shifted at sample {sample} {name}")
  # original silence before/after events remains zero; tail only admitted if
  # explicitly requested in the manifest.
  nonzero=[i for i in range(N+tail) if struct.unpack_from("<h",native,i*2)[0]!=0]
  expected=[x for x,_ in CUES]+([ECHO_AT] if tail else [])
  if nonzero!=expected:
   raise ValueError(f"unexpected decoded PCM samples {name} {nonzero[:10]}")
  if tail and struct.unpack_from("<h",native,ECHO_AT*2)[0]!=4000:
   raise ValueError("original synthetic echo lost")
  vsha=videohash(master)
  if vsha!=source_video_sha:raise ValueError("video frames mutated by mux")
  f=probe(master)["frames"]
  if len(f)!=300:raise ValueError("not 300 video frame PTS")
  maximum=max(abs(float(x["best_effort_timestamp_time"])-i/30) for i,x in enumerate(f))
  if maximum>0.0011:raise ValueError("video PTS drift beyond Matroska precision")
  rows.append(dict(id=name,measured_processor_latency_samples=delay,
   retained_tail_samples=tail,actual_source_clicks=[x for x,_ in CUES],
   retained_echo_sample=ECHO_AT if tail else None,
   absolute_click_error_samples=0,full_pcm_sha256=hashlib.sha256(native).hexdigest(),
   original_video_pixels_sha256=vsha,max_video_pts_error_seconds=maximum,
   master_sha256=sha(master),mux_audio_frames=N+tail))
 if seen!={(d,t) for d in DELAYS for t in TAILS}:raise ValueError("missing matrix cells")
 result=dict(schema="spatial_audio.w4f_latency_mux_observer.v1",status="PASS",
  native_outputs=len(rows),negative_untrimmed_detected=True,
  exact_audio_click_tolerance_samples=0,matched_video_timebase="30/1",
  rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
  source_manifest_sha256=sha(root/"manifest.json"),
  observations=rows,unqualified=["VARIABLE_PROCESSOR_DELAY","PERCEPTUAL_LIPSYNC",
   "AAC_CODEC_PRIMING","DEVICE_AUDIO_HARDWARE_LATENCY","ROOM_T60","REAL_CHARACTER_ASSETS"])
 pathlib.Path(out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("W4F_LATENCY_MUX_INDEPENDENT_PCM_PASS cases",len(rows),"click_error_samples=0",
       "negative_untrimmed_255_detected=True")
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: inspect_latency_mux.py ROOT OUTPUT.json")
 try:verify(sys.argv[1],sys.argv[2])
 except Exception as e:
  pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(schema="spatial_audio.w4f_latency_mux_observer.v1",status="FAIL",first_failure=str(e)),sort_keys=True,indent=2)+"\n")
  print("W4F_LATENCY_MUX_FIRST_FAILURE",e,file=sys.stderr)
  raise
