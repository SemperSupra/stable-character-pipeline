"""Independent full PCM, source-rights and transition observer of SAF resource grid."""
import array,hashlib,json,math,struct,sys
from pathlib import Path
HOPS=(128,256,512)
IRS=(256,512,1024)
MODES=("static","on_off")
MAX_PREFIX=1e-6
MIN_CHANGE=1e-5
def sha(x):return hashlib.sha256(Path(x).read_bytes()).hexdigest()
def pcm(p,frames):
 b=Path(p).read_bytes()
 if len(b)!=frames*4 or sys.byteorder!="little":raise ValueError("invalid buffer")
 x=array.array("f");x.frombytes(b)
 if len(x)!=frames or any(not math.isfinite(v) or abs(v)>1 for v in x) or sum(v*v for v in x)<=1e-10:
  raise ValueError("nonfinite, clipping or silent")
 return x
def rms(a,b,start,end):
 return math.sqrt(sum((a[i]-b[i])**2 for i in range(start,end))/(end-start))
def audit(root,out):
 root=Path(root)
 raws={}
 for hop in HOPS:
  b=(root/f"source_h{hop}.s16le").read_bytes()
  if len(b)!=32*hop*2:raise ValueError("raw source shape")
  for i in (0,1,hop,8*hop,16*hop,24*hop,32*hop-1):
   actual=struct.unpack_from("<h",b,i*2)[0]
   expected=0 if i>=24*hop else int(round((.08*math.sin(2*math.pi*410*i/48000)+(.1 if i in (8*hop,16*hop) else 0))*32767))
   if abs(actual-expected)>1:raise ValueError("rights/source drift")
  raws[hop]=sha(root/f"source_h{hop}.s16le")
 rows={};allfiles=[]
 for line in (root/"saf_w4i_transition.tsv").read_text().splitlines():
  parts=line.split("\t")
  if len(parts)!=9:raise ValueError("metadata framing")
  hop,ir,mode,n=map(int,parts[:2])+() if False else (int(parts[0]),int(parts[1]),parts[2],int(parts[3]))
  if hop not in HOPS or ir not in IRS or mode not in MODES or n!=32*hop or (hop,ir,mode) in rows:
   raise ValueError("metadata coordinates/duplicate")
  peak,energy,tail,elapsed,maxrss=map(float,parts[4:])
  if not (0<peak<=1 and energy>1e-10 and tail>=0 and math.isfinite(elapsed) and elapsed>=0 and maxrss>0):
   raise ValueError("nonfinite resource metadata")
  rows[hop,ir,mode]=dict(peak=peak,energy=energy,tail=tail,elapsed_seconds=elapsed,maxrss_kib=maxrss)
 if len(rows)!=18:raise ValueError("incomplete 18-case metadata")
 worst_prefix=0;smallest_change=float("inf")
 for hop in HOPS:
  for ir in IRS:
   a=pcm(root/f"saf_h{hop}_ir{ir}_static.f32",32*hop)
   b=pcm(root/f"saf_h{hop}_ir{ir}_on_off.f32",32*hop)
   prefix=max(abs(a[i]-b[i]) for i in range(12*hop))
   delta=rms(a,b,12*hop,24*hop)
   if prefix>MAX_PREFIX or delta<=MIN_CHANGE:
    raise ValueError(f"frozen SAF time-varying response violated hop={hop} ir={ir} prefix={prefix} delta={delta}")
   worst_prefix=max(worst_prefix,prefix)
   smallest_change=min(smallest_change,delta)
   for mode in MODES:
    path=root/f"saf_h{hop}_ir{ir}_{mode}.f32"
    signal=a if mode=="static" else b
    sig=[i for i,x in enumerate(signal) if abs(x)>1e-7]
    if not sig:raise ValueError("silent source/IR output")
    first,last=sig[0],sig[-1]
    tail_energy=sum(x*x for x in signal[24*hop:])
    if not math.isfinite(tail_energy):raise ValueError("nonfinite tail energy")
    allfiles.append(dict(first_significant_frame=first,last_significant_frame=last,
       post_source_end_tail_energy=tail_energy,hop=hop,ir_length=ir,mode=mode,sha256=sha(path),
        native_resources=rows[hop,ir,mode],pair_prefix_max_error=prefix,
        pair_changed_rms=delta))
 receipt=dict(schema="spatial_audio.saf_w4i_ir_return.v1",
  status="PASS_NATIVE_IR_ON_OFF_AND_RETURN_TO_BASELINE",
  provider="leomccormack/Spatial_Audio_Framework",
  upstream_sha="18fd5aba46e20787b51f28f7197a68506c965c07",
  source_rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
  source_sha256_by_hop={str(k):v for k,v in raws.items()},
  count=len(allfiles),max_unchanged_prefix_error=worst_prefix,
  min_changed_vs_static_rms=smallest_change,
  constraints={"prefix_max_abs":MAX_PREFIX,"change_rms_min":MIN_CHANGE},
  measurements=allfiles,
  performance_scope="OBSERVATION_ONLY_NO_CPU_QUALIFICATION_ACROSS_RUNNERS",
  not_tested=["T60","PHYSICAL_ROOM_ACCURACY","REAL_BRIR","PERSONALIZED_HRTF",
              "MEMORY_LEAK_LONG_RUN","PERCEPTUAL_AUDIO","SOURCE_RIGHTS_THIRD_PARTY"])
 Path(out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("SAF_W4I_INDEPENDENT_PCM_PASS cases",len(allfiles),
       "max_prefix",worst_prefix,"min_changed_rms",smallest_change)
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: saf_w4d_observe.py NATIVE_DIR OUT_JSON")
 audit(sys.argv[1],sys.argv[2])
