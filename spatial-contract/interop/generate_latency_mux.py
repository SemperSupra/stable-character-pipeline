"""Original self-authored 48k three-event AV sync and latency/IR tail mux.
No real person, room, music, video, speech, or physical device data.
One native video build, then 3 measured-delay × 2 tail-policy mux outputs.
"""
import hashlib,json,pathlib,struct,subprocess,sys,wave

N=480000
RATE=48000
DELAYS=(0,255,1024)
TAILS=(0,2048)
CUES=((96000,16000),(240000,10000),(479700,8000))
ECHO_AT=480100
ECHO_AMPLITUDE=4000
def cmd(*args):
 r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
 if r.returncode:raise RuntimeError("FIRST_FAILURE "+repr(args)+" "+r.stderr.decode(errors="replace")[-1400:])
 return r.stdout.decode(errors="replace")
def hashfile(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def wav(path,values):
 with wave.open(str(path),"wb") as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(RATE)
  f.writeframes(b"".join(struct.pack("<h",v) for v in values))
def make(root):
 root=pathlib.Path(root);root.mkdir(parents=True,exist_ok=False)
 orig=[0]*N
 for i,v in CUES:orig[i]=v
 src=root/"original_source.wav";wav(src,orig)
 video=root/"original_video.mkv"
 cmd("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
     "-f","lavfi","-i","color=c=black:s=160x90:r=30",
     "-vf","drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='eq(n,60)+eq(n,150)+eq(n,299)'",
     "-frames:v","300","-c:v","ffv1","-level","3",str(video))
 receipts=[]
 for delay in DELAYS:
  raw=[0]*(N+delay+2048)
  for sample,amp in CUES:raw[delay+sample]=amp
  raw[delay+ECHO_AT]=ECHO_AMPLITUDE
  for keep in TAILS:
   # Explicitly measured fixed processor delay trimmed at the source clock.
   aligned=raw[delay:delay+N+keep]
   name=f"d{delay:04d}_tail{keep:04d}"
   intermediate=root/(name+".wav")
   final=root/(name+".mkv")
   wav(intermediate,aligned)
   cmd("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
       "-i",str(video),"-i",str(intermediate),
       "-map","0:v:0","-map","1:a:0","-c:v","copy",
       "-c:a","pcm_s16le","-avoid_negative_ts","disabled",str(final))
   receipts.append(dict(id=name,processor_delay_samples=delay,keep_tail_samples=keep,
     lossless_master=final.name,sha256=hashfile(final),
     aligned_wav_sha256=hashfile(intermediate),
     expected_audio_frames=N+keep,source_rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"))
   print("W4F_AV_LATENCY_NATIVE_MASTER",name,"decoded_expected_frames",N+keep,flush=True)
 # Intentional NON-CORRECTED negative control. It MUST NOT be accepted as
 # synchronized and is NOT muxed as a valid video artifact.
 bad=root/"expected_reject_untrimmed_255.wav"
 raw=[0]*(N+255)
 for sample,amp in CUES:raw[sample+255]=amp
 wav(bad,raw)
 metadata=dict(schema="spatial_audio.w4f_latency_mux.v1",
    rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
    original_video_sha256=hashfile(video),original_source_sha256=hashfile(src),
    original_video_frames=300,original_audio_frames=N,
    events=[dict(sample=i,amplitude=a) for i,a in CUES],
    late_echo_sample=ECHO_AT,late_echo_amplitude=ECHO_AMPLITUDE,
    negative_untrimmed_wav_sha256=hashfile(bad),
    ffmpeg_version=cmd("ffmpeg","-version").splitlines()[0],cases=receipts)
 (root/"manifest.json").write_text(json.dumps(metadata,sort_keys=True,indent=2)+"\n")
 print("W4F_AV_LATENCY_NATIVE_SIX_MASTERS_READY")
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("usage: generate_latency_mux.py NEW_DIR")
 make(sys.argv[1])
