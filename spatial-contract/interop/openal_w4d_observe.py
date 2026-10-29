"""Independent exact source-sample-switch OpenAL Soft HRTF timing observer."""
import array,hashlib,json,math,struct,sys
from pathlib import Path
OFFSETS=(0,1,255,256,1023,1024,1025)
FRAMES=8192
TOL=1e-6
RMS_MIN=1e-5
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(path):
 b=Path(path).read_bytes()
 if sys.byteorder!="little" or len(b)!=FRAMES*8:raise ValueError("incorrect stereo F32 length")
 x=array.array("f");x.frombytes(b)
 if len(x)!=FRAMES*2 or not all(math.isfinite(v) and abs(v)<=1 for v in x):
  raise ValueError("nonfinite/clipped PCM")
 if sum(v*v for v in x)<=1e-8:raise ValueError("silent native output")
 return x
def rms(a,b,first,last):
 return math.sqrt(sum((a[i]-b[i])**2 for i in range(first*2,last*2))/((last-first)*2))
def check(root,out):
 root=Path(root)
 original=(root/"original_410_mono_s16le.raw").read_bytes()
 if len(original)!=FRAMES*2:raise ValueError("source shape")
 for i in (0,1,255,256,1023,1024,1025,8191):
  got=struct.unpack_from("<h",original,i*2)[0]
  want=int(round(.12*32767*math.sin(2*math.pi*410*i/48000)))
  if got!=want:raise ValueError("source provenance mismatch")
 rows={}
 for s in (root/"offsets.tsv").read_text().splitlines():
  p=s.split("\t")
  if len(p)!=5:raise ValueError("metadata cols")
  name,offset,status,peak,energy=p
  if name in rows or status!="1" or not 0<float(peak)<=1 or float(energy)<=1e-8:
   raise ValueError("native HRTF status invalid")
  rows[name]=dict(offset=int(offset),hrtf_enabled=int(status),peak=float(peak),energy=float(energy))
 names=("static_left","static_right")+tuple(f"switch_{o:04d}" for o in OFFSETS)
 if set(rows)!=set(names) or rows["static_left"]["offset"]!=-1 or rows["static_right"]["offset"]!=-1:
  raise ValueError("incomplete schedule")
 data={n:load(root/(n+".f32")) for n in names}
 left=data["static_left"];right=data["static_right"]
 if left.tobytes()==right.tobytes():raise ValueError("left and right identical")
 measures=[]
 for offset in OFFSETS:
  name=f"switch_{offset:04d}"
  buf=data[name]
  if rows[name]["offset"]!=offset:raise ValueError("wrong source switch time")
  prefix=max((abs(left[i]-buf[i]) for i in range(offset*2)),default=0.0)
  first=max(offset+512,2048)
  if first>=FRAMES-1024:raise ValueError("insufficient post-change observation")
  late_rms=rms(left,buf,first,FRAMES)
  # Boundary discontinuity is recorded, NOT an accepted psychoacoustic metric.
  seam=max((abs(buf[i*2+c]-buf[(i-1)*2+c]) for c in range(2) for i in
      range(max(1,offset-1),min(FRAMES,offset+2))),default=0.0)
  if prefix>TOL or late_rms<=RMS_MIN:
   raise ValueError(f"frozen HRTF time-domain response failed offset={offset} prefix={prefix} late={late_rms}")
  measures.append(dict(source_change_sample=offset,prefix_max_abs_delta=prefix,
     late_moving_vs_static_rms=late_rms,near_switch_sample_step_max=seam,
     output_sha256=sha(root/(name+".f32"))))
 report=dict(schema="spatial_audio.openal_w4d_offset_timing.v1",
   status="PASS_RENDER_CALL_BOUNDARY_HRTF_CHANGES",renderer_sha="b7463649fd73188146e3b1467a91e7f0926a6d04",
   original_rights="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
   source_sha256=hashlib.sha256(original).hexdigest(),sample_rate=48000,
   frames=FRAMES,render_callback_max_frames=256,
   verified_offsets=list(OFFSETS),frozen_prefix_tolerance=TOL,
   frozen_moving_rms_min=RMS_MIN,observations=measures,
   control_sha256={n:sha(root/(n+".f32")) for n in names[:2]},
   NOT_TESTED=["SOURCE_CHANGE_WITHIN_SINGLE_RENDER_CALL","SAMPLE_CONTINUOUS_6DOF",
     "PERCEPTUAL_LOCALIZATION","ACOUSTIC_REFLECTION","PROPAGATION_DELAY","DOPPLER"])
 Path(out).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print("OPENAL_W4D_INDEPENDENT_OFFSET_PASS offsets",len(measures),
  "max_prefix",max(x["prefix_max_abs_delta"] for x in measures),
  "min_late_rms",min(x["late_moving_vs_static_rms"] for x in measures))
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: openal_w4d_observe.py OUTPUT_DIR RECEIPT.json")
 check(sys.argv[1],sys.argv[2])
