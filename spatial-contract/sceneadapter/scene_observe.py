"""Independent analytic validation of every byte of the Go scene-to-PCM batch."""
import hashlib,json,math,struct,sys
from pathlib import Path
FRAMES=1024
RATE=48000
EMITTERS=[(2,0,0),(0,4,0),(0,0,20),(10,10,0)]
LISTENERS=[(0,0,0),(1,0,0),(-1,2,0)]
LAYOUTS={2:["FL","FR"],6:["FL","FR","FC","LFE","SL","SR"],
         8:["FL","FR","FC","LFE","SL","SR","BL","BR"]}
KINDS=("impulse","tone")
MODES=("identity","inverse_distance")
RIGHTS="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
TOL=1e-6
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_wav(path,n):
 b=Path(path).read_bytes()
 if len(b)!=44+FRAMES*n*4 or b[:4]!=b"RIFF" or b[8:16]!=b"WAVEfmt " or b[36:40]!=b"data":
  raise ValueError("wav framing")
 riff,fmtlen,fmt,ch,rate,byterate,block,bits,length=(
  struct.unpack_from("<I",b,4)[0],struct.unpack_from("<I",b,16)[0],
  struct.unpack_from("<H",b,20)[0],struct.unpack_from("<H",b,22)[0],
  struct.unpack_from("<I",b,24)[0],struct.unpack_from("<I",b,28)[0],
  struct.unpack_from("<H",b,32)[0],struct.unpack_from("<H",b,34)[0],
  struct.unpack_from("<I",b,40)[0])
 if (riff!=len(b)-8 or fmtlen!=16 or fmt!=3 or ch!=n or rate!=RATE or
  byterate!=RATE*n*4 or block!=n*4 or bits!=32 or length!=FRAMES*n*4):
  raise ValueError("wav semantic header")
 return struct.unpack_from("<"+"f"*(FRAMES*n),b,44)
def verify(root,out):
 root=Path(root)
 m=json.loads((root/"scene_batch.json").read_text())
 if m["schema"]!="spatial_audio.scene_adapter_batch.v1" or m["rights"]!=RIGHTS:raise ValueError("rights/schema")
 originals={}
 for kind in KINDS:
  path=root/f"original_{kind}.s16le"
  b=path.read_bytes()
  if len(b)!=FRAMES*2 or sha(path)!=m["source_sha256"].get(kind):raise ValueError("source SHA")
  samples=struct.unpack("<"+"h"*FRAMES,b)
  for f,v in enumerate(samples):
   expected=(12345 if f==0 else 2468 if f==255 else 0) if kind=="impulse" else int(round(.15*32767*math.sin(2*math.pi*410*f/RATE)))
   if v!=expected:raise ValueError("nonoriginal fixture")
  originals[kind]=samples
 if len(m["cases"])!=144:raise ValueError("bad case count")
 seen=set();renderids=set();worst=0.0;qual=[]
 for x in m["cases"]:
  dec=x["decision"];name=x["file"];kind=x["original_kind"]
  e=x["emitter"];l=x["listener"]
  ep=(e["East"],e["North"],e["Up"])
  lp=(l["East"],l["North"],l["Up"])
  if ep not in EMITTERS or lp not in LISTENERS:raise ValueError("unknown ENU")
  ei=EMITTERS.index(ep);li=LISTENERS.index(lp)
  n=len(dec["channel_labels"]);curve=dec["curve"]
  if n not in LAYOUTS or dec["channel_labels"]!=LAYOUTS[n] or curve not in MODES or kind not in KINDS:
   raise ValueError("layout/curve")
  expected_name=f"scene_e{ei}_l{li}_ch{n}_{curve}_{kind}.wav"
  if name!=expected_name or name in seen or Path(name).name!=name:raise ValueError("path/duplicate")
  seen.add(name)
  if (dec["schema"]!="spatial_audio.scene_plan.v1" or dec["coordinate_system"]!="ENU_METERS"
   or dec["rate_hz"]!=RATE or dec["start_frame"]!=1024 or dec["frame_count"]!=FRAMES
   or dec["rights"]!=RIGHTS or dec["source_id"]!=f"emitter_{ei}_{kind}"
   or dec["listener_id"]!=f"listener_{li}" or dec["original_source_sha256"]!=m["source_sha256"][kind]):
   raise ValueError("scene custody / frame")
  renderid=dec["render_id"]
  if len(renderid)!=64 or any(c not in "0123456789abcdef" for c in renderid) or renderid in renderids:
   raise ValueError("unstable/duplicate output identity")
  renderids.add(renderid)
  distance=math.hypot(math.hypot(ep[0]-lp[0],ep[1]-lp[1]),ep[2]-lp[2])
  gain=(1.0 if curve=="identity" else min(1.0,10/max(distance,1.0)))
  if abs(dec["distance_meters"]-distance)>1e-12 or abs(dec["gain"]-gain)>1e-12:
   raise ValueError("incorrect independently derived ENU pressure gain")
  if sha(root/name)!=x["sha256"]:raise ValueError("output source SHA")
  p=read_wav(root/name,n)
  if not any(v!=0 for v in p):raise ValueError("silence")
  local=0.0
  for fi,v in enumerate(originals[kind]):
   for ch in range(n):
    got=p[fi*n+ch]
    if not math.isfinite(got) or abs(got)>1:raise ValueError("nonfinite/clipped")
    expected=(0 if (n>=6 and ch==3) else (v/32768)*(.6/(ch+1))*gain)
    diff=abs(got-expected)
    local=max(local,diff)
    if diff>TOL:raise ValueError(f"sample oracle {name} fi{fi} ch{ch} err{diff}")
  worst=max(worst,local)
  qual.append({"file":name,"max_abs_pcm_err":local,"render_id":renderid})
 exp={f"scene_e{e}_l{l}_ch{n}_{curve}_{kind}.wav" for e in range(4) for l in range(3)
      for n in LAYOUTS for curve in MODES for kind in KINDS}
 if seen!=exp:raise ValueError("missing grid")
 receipt={"schema":"spatial_audio.w4d_scene_observer.v1","status":"PASS",
  "cases":len(qual),"max_sample_absolute_error":worst,"frozen_tolerance":TOL,
  "source_manifest_sha256":sha(root/"scene_batch.json"),"case_receipts":qual,
  "not_tested":["SPATIAL_PANNING","SAMPLE_CONTINUOUS_MOVEMENT","HRTF","AIR_ABSORPTION",
                "DOPPLER","ROOM","HUMAN_LISTENING","PRODUCTION_LICENSE_ACCEPTANCE"]}
 Path(out).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
 print("W4D_SCENE_INDEPENDENT_PCM_PASS cases",len(qual),"worst_error",worst)
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("usage: scene_observe.py SOURCE_DIR OUT_JSON")
 verify(sys.argv[1],sys.argv[2])
