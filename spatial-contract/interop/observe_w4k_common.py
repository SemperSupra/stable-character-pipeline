"""Independent full-PCM original shared-source OpenAL+SAF observer.
Same input does NOT mean same convolution or valid universal output delay.
"""
import array,hashlib,json,math,struct,sys
from pathlib import Path
RATE=48000
SOURCE_FRAMES=16384
OUTPUT_FRAMES=32768
CHANNELS={"openal":2,"saf":1}
OPENAL=("static_left","dynamic_source_lrl","dynamic_listener_yaw")
SAF=("saf_static","saf_dynamic_ir")
def digest(b):return hashlib.sha256(b).hexdigest()
def source_bytes(raw):
 if len(raw)!=SOURCE_FRAMES*2:raise ValueError("SOURCE_SIZE")
 for i in range(SOURCE_FRAMES):
  expected={0:12000,4096:15000,8192:10000}.get(i,0)
  if struct.unpack_from("<h",raw,2*i)[0]!=expected:raise ValueError("SOURCE_ORIGINAL_PCM_MISMATCH")
 return digest(raw)
def floats(raw,channels):
 if len(raw)!=OUTPUT_FRAMES*channels*4 or sys.byteorder!="little":raise ValueError("RENDER_BUFFER_SIZE")
 a=array.array("f");a.frombytes(raw)
 if any(not math.isfinite(v) or abs(v)>1 for v in a):raise ValueError("NONFINITE_OR_CLIPPING")
 if math.fsum(v*v for v in a)<=1e-10:raise ValueError("SILENCE")
 return a
def response(a,channels):
 f=[i for i in range(OUTPUT_FRAMES) if any(abs(a[i*channels+c])>1e-7 for c in range(channels))]
 if not f or f[0]<0 or f[-1]>=OUTPUT_FRAMES:raise ValueError("IMPULSE_ONSET_TAIL")
 return dict(first_significant_sample=f[0],last_significant_sample=f[-1],
             post_source_tail_energy=math.fsum(v*v for v in a[SOURCE_FRAMES*channels:]),
             peak=max(map(abs,a)))
def compare(a,b,channels):
 if len(a)!=len(b):raise ValueError("PAIR_SIZE")
 prefix=max(abs(a[i]-b[i]) for i in range(4096*channels))
 delta=math.sqrt(math.fsum((a[i]-b[i])**2 for i in range(4096*channels,16384*channels))/(12288*channels))
 if prefix!=0:raise ValueError("CHANGED_BEFORE_TRIGGER")
 if delta<=1e-5:raise ValueError("INSUFFICIENT_NATIVE_IR_OR_POSE_CHANGE")
 return dict(prechange_max_abs=prefix,postchange_rms=delta)
def checks(data,channels):
 return {k:response(v,channels) for k,v in data.items()}
def audit(openal_root,saf_root,out):
 op=Path(openal_root);sf=Path(saf_root)
 a=(op/"source_s16le.raw").read_bytes();b=(sf/"source_s16le.raw").read_bytes()
 sa=source_bytes(a);sb=source_bytes(b)
 if a!=b or sa!=sb:raise ValueError("CROSS_ENGINE_SOURCE_BYTES_DIFFER")
 native_o={k:floats((op/(k+".f32")).read_bytes(),2) for k in OPENAL}
 native_s={k:floats((sf/(k+".f32")).read_bytes(),1) for k in SAF}
 o=checks(native_o,2);s=checks(native_s,1)
 pair_o={k:compare(native_o["static_left"],native_o[k],2) for k in OPENAL[1:]}
 pair_s=compare(native_s["saf_static"],native_s["saf_dynamic_ir"],1)
 for rows,path,width in ((o,op/"actual_native_states.tsv",7),(s,sf/"native_measure.tsv",6)):
  actual={}
  for line in path.read_text().splitlines():
   values=line.split("\t")
   if len(values)!=width or values[0] in actual:raise ValueError("NATIVE_METADATA_FRAMING")
   actual[values[0]]=values
  if set(actual)!=set(rows):raise ValueError("NATIVE_METADATA_MISSING_MODE")
  for k,r in rows.items():
   vals=actual[k]
   idx=2 if width==7 else 1
   if int(vals[idx])!=r["first_significant_sample"] or int(vals[idx+1])!=r["last_significant_sample"]:
    raise ValueError("NATIVE_METADATA_NOT_PCM")
 receipt=dict(schema="scp.spatial_w4k_shared_pcm_dual_native.v1",status="PASS_NATIVE_IDENTICAL_ORIGINAL_SOURCE",
 source_rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",source_hz=RATE,source_samples=SOURCE_FRAMES,
 source_sha256=sa,output_samples=OUTPUT_FRAMES,clock_event_samples=[0,4096,8192],
 openal={"renderer":"pinned_openal_soft_loopback_HRTF","channels":2,"modes":o,"changed_vs_static":pair_o},
 saf={"renderer":"pinned_SAF_TVConv","channels":1,"modes":s,"changed_vs_static":pair_s},
 measured_cross_renderer_first_onset_difference_samples=o["static_left"]["first_significant_sample"]-s["saf_static"]["first_significant_sample"],
 latency_scope="OBSERVED_ONLY_SOURCE_IDENTICAL_BUT_FILTER_CHANNELS_TOPOLOGY_DIFFER",
 not_claimed=["UNIVERSAL_LATENCY","DIRECT_PCM_EQUALITY_BETWEEN_RENDERERS","SAME_IR_OR_HRTF",
 "PHYSICAL_DEVICE_DELAY","PERCEPTUAL_QUALITY","VIDEO_MUX_PTS","VIDEOLAN_THIRD_ENGINE"])
 Path(out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W4K_COMMON_INPUT_INDEPENDENT_FULL_PCM_PASS",sa,"openal",pair_o,"saf",pair_s)
if __name__=="__main__":
 if len(sys.argv)!=4:raise SystemExit("usage OBSERVE OPENAL_DIR SAF_DIR OUT")
 audit(sys.argv[1],sys.argv[2],sys.argv[3])
