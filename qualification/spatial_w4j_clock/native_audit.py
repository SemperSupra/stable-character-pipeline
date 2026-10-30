"""Offline source-only native PCM comparison: no absolute cross-renderer delay inference."""
import array,hashlib,json,math,sys,zipfile
from pathlib import Path
SOURCES=("d9572958f15fb4e94f60a30b7cad5d2ab4ac1add83c983d71496ff940e399643",
         "02cbe3d3727f6603c93c8ed0713d96af42e23bbece36b2425dda6ec1e8a673d3")
def pcm(z,name,nch):
 b=z.read(name);a=array.array("f")
 if len(b)%4 or sys.byteorder!="little":raise ValueError("PCM_ENCODING")
 a.frombytes(b)
 if len(a)%nch or any(not math.isfinite(x) for x in a):raise ValueError("PCM_SHAPE_NONFINITE")
 return a
def measure(a,b,start,end,nch):
 if len(a)!=len(b):raise ValueError("CHANNEL_OR_LENGTH_MISMATCH")
 prefix=max(abs(a[i]-b[i]) for i in range(start*nch))
 delta=math.sqrt(math.fsum((a[i]-b[i])**2 for i in range(start*nch,end*nch))/((end-start)*nch))
 if prefix!=0 or delta<=1e-5:raise ValueError("PRECHANGE_OR_POSTCHANGE_ORACLE")
 return {"prechange_max_error":prefix,"changed_rms":delta}
def audit(h,s):
 for p,digest in zip((h,s),SOURCES):
  if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=digest:raise ValueError("ARCHIVE_SHA_NOT_PINNED")
 with zipfile.ZipFile(h) as z:
  a=pcm(z,"static_left.f32",2)
  out={"openal_dynamic":{name:measure(a,pcm(z,name+".f32",2),4096,16384,2) for name in ("dynamic_source_lrl","dynamic_listener_yaw")}}
 with zipfile.ZipFile(s) as z:
  rows=[]
  for hop in (128,256,512):
   for ir in (256,512,1024):
    a=pcm(z,f"saf_h{hop}_ir{ir}_static.f32",1)
    b=pcm(z,f"saf_h{hop}_ir{ir}_on_off.f32",1)
    rows.append(dict(hop=hop,ir=ir,**measure(a,b,12*hop,24*hop,1)))
  out["saf_pairs"]=rows
 out.update(schema="scp.w4j_pcm_native_separate_sources.v1",status="PASS_SOURCE_SPECIFIC_PCM",same_input_across_engines=False,absolute_delay_comparison="ABSTAIN")
 return out
if __name__=="__main__":
 if len(sys.argv)!=4:raise SystemExit("usage: native_audit.py HRTF_ZIP SAF_ZIP OUT_JSON")
 r=audit(sys.argv[1],sys.argv[2]);Path(sys.argv[3]).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W4J_NATIVE_PCM_AUDIT_PASS",len(r["saf_pairs"]))
