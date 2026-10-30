"""Independent actual pinned OpenAL Soft HRTF impulse-onset / late-tail audit.
Records observed onset and output tail, not claimed fixed latency.
"""
import array,hashlib,json,math,pathlib,struct,sys
FS=48000
NIN=16384
NOUT=32768
CH=2
LIMIT=1e-7
NAMES=("off_left","on_left","on_front","on_right")
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def pcm(p):
 b=pathlib.Path(p).read_bytes()
 if len(b)!=NOUT*CH*4 or sys.byteorder!="little":raise ValueError("PCM float buffer size/platform")
 a=array.array("f");a.frombytes(b)
 if len(a)!=NOUT*CH or any((not math.isfinite(v) or abs(v)>1) for v in a):
  raise ValueError("nonfinite/clipped native PCM")
 return a
def inspect(root,out):
 root=pathlib.Path(root)
 original=(root/"original_impulses_s16le.raw").read_bytes()
 if len(original)!=NIN*2:raise ValueError("invalid original PCM16")
 positive=[(i,struct.unpack_from("<h",original,2*i)[0]) for i in range(NIN)
           if original[2*i:2*i+2]!=b"\0\0"]
 if positive!=[(0,12000),(4096,15000),(8192,10000)]:
  raise ValueError("source provenance/expected impulses not matching original")
 native={}
 for line in (root/"actual_native_states.tsv").read_text().splitlines():
  v=line.split("\t")
  if len(v)!=7:raise ValueError("native measurements fields")
  name,status,first,last,peak,energy,tail=v
  if name not in NAMES or name in native:return_error()
  native[name]=(int(status),int(first),int(last),float(peak),float(energy),float(tail))
 if set(native)!=set(NAMES):raise ValueError("missing renderer modes")
 observations=[]
 rendered={}
 for name in NAMES:
  samples=pcm(root/(name+".f32"))
  rendered[name]=samples
  above=[i for i in range(NOUT) if max(abs(samples[i*2]),abs(samples[i*2+1]))>LIMIT]
  if not above:raise ValueError("actual sound silent")
  first,last=above[0],above[-1]
  peak=max(abs(v) for v in samples)
  energy=sum(v*v for v in samples)
  tail=sum(v*v for v in samples[NIN*CH:])
  status,f0,l0,p0,e0,t0=native[name]
  if status!=(1 if name.startswith("on_") else 0):
   raise ValueError("HRTF ON/OFF status mismatch")
  if first!=f0 or last!=l0 or abs(peak-p0)>1e-7 or abs(energy-e0)>1e-5 or abs(tail-t0)>1e-5:
   raise ValueError("native measurements inconsistent with original floating samples")
  if first<0 or last>=NOUT or peak<1e-7 or energy<=1e-10:
   raise ValueError("unbounded/empty impulse output")
  observations.append(dict(mode=name,hrtf_status=status,
      first_significant_output_sample=first,last_significant_output_sample=last,
      sample_threshold=LIMIT,source_impulses=[0,4096,8192],
      post_input_end_tail_energy=tail,peak=peak,energy=energy,
      output_sha256=sha(root/(name+".f32"))))
 off=rendered["off_left"];on=rendered["on_left"]
 deviation=math.sqrt(sum((x-y)**2 for x,y in zip(off,on))/len(off))
 if deviation<=1e-6:raise ValueError("HRTF ON/OFF output indistinguishable")
 result=dict(schema="spatial_audio.w4g_openal_native_onset_tail.v1",
  status="PASS_PINNED_REAL_RENDERER_ONSET_OBSERVED",
  source_pin="kcat/openal-soft@b7463649fd73188146e3b1467a91e7f0926a6d04",
  original_rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
  rate=FS,original_input_frames=NIN,actual_output_frames=NOUT,
  source_sha256=hashlib.sha256(original).hexdigest(),
  measured=observations,on_vs_off_left_rms=deviation,
  frozen_threshold=LIMIT,
  not_qualified=["PRODUCTION_DEVICE_LATENCY","SAMPLE_CONTINUOUS_SOURCE",
   "PSYCHOACOUSTIC_LOCALIZATION","HRTF_INTERPOLATION_QUALITY","VIDEO_SYNC_HIL",
   "ROOM_PROPAGATION","PERSONALIZED_DATASETS"])
 pathlib.Path(out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
 print("W4G_OPENAL_NATIVE_ONSET_INDEPENDENT_PASS modes=4 on_off_rms",deviation,
       "onset_samples",[(x["mode"],x["first_significant_output_sample"]) for x in observations])
def return_error():raise ValueError("duplicate/malformed native mode")
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: observe_openal_w4g.py ORIGINAL OUTPUT.json")
 try:inspect(sys.argv[1],sys.argv[2])
 except Exception as e:
  pathlib.Path(sys.argv[2]).write_text(json.dumps(dict(status="FAIL",first_failure=str(e)),indent=2)+"\n")
  print("W4G_OPENAL_FIRST_FAILURE",e,file=sys.stderr);raise
