"""W8-D independent original-source camera/clock falsifier; no markers in beauty video."""
import argparse,hashlib,json,math
from pathlib import Path
EYES={"OriginalFront":((0.,-8.5,2.8),(0.,0.,1.15)),
      "OriginalOblique":((7.5,-7.,3.1),(0.,0.,1.15))}
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
def length(v):return math.sqrt(sum(x*x for x in v))
def norm(v):
 l=length(v)
 if not math.isfinite(l) or l<=1e-10:raise ValueError("W8D_CAMERA_DEGENERATE")
 return [x/l for x in v]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def uv(xyz,cam):
 eye,target=EYES[cam]
 front=norm(sub(target,eye))
 right=norm(cross(front,[0.,0.,1.]))
 up=norm(cross(right,front))
 d=sub(xyz,eye)
 return [.5+dot(d,right)/5.75,.5+dot(d,up)/(5.75*360./640.)]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def audit(source,render):
 if source.get("schema")!="scp.walk_w7a_original_approach.v1" or source.get("rights")!=RIGHTS or source.get("fps_num")!=12 or source.get("fps_den")!=1 or len(source.get("actors",[]))!=2:
  raise ValueError("W8D_SOURCE_RIGHTS_CLOCK")
 probes=[]
 for camera in render.get("cameras",[]):
  name=camera["camera"]
  if name not in EYES:raise ValueError("W8D_UNKNOWN_CAMERA")
  # Native W6 camera probe is at tick0 for front, tick23 for oblique:
  # original renderer advanced scene while creating its prior camera video.
  tick=0 if name=="OriginalFront" else 23
  for item in camera["core_body_camera_projection"]:
   a=next((x for x in source["actors"] if x["id"]==item["actor"]),None)
   if a is None or len(a["frames"])!=24:raise ValueError("W8D_ACTOR_OR_CLOCK")
   f=a["frames"][tick]
   if (f["index"],f["time_num"],f["time_den"])!=(tick,tick,12):
    raise ValueError("W8D_CAMERA_PROBE_SOURCE_TICK")
   height={"Head":2.17,"Torso":1.50,"Pelvis":1.09}.get(item["part"])
   if height is None:raise ValueError("W8D_BODY_PROBE")
   predicted=uv((f["root_x"],f["root_y"],height),name)
   err=math.dist(predicted,item["uv"])
   if err>.0001:raise ValueError("W8D_INDEPENDENT_CAMERA_PROJECTION")
   probes.append({"camera":name,"native_probe_tick":tick,"actor":a["id"],
      "part":item["part"],"max_uv_error":err,
      "native_uv":item["uv"],"independent_uv":predicted})
 if len(probes)!=12 or {x["camera"] for x in probes}!=set(EYES):
  raise ValueError("W8D_MISSING_PROBES")
 for a in source["actors"]:
  for i,f in enumerate(a["frames"]):
   if (f["index"],f["time_num"],f["time_den"])!=(i,i,12):
    raise ValueError("W8D_SOURCE_TIMECODE_DRIFT")
 grid=[]
 for camera in EYES:
  for x in range(-2,3):
   for y in range(-2,3):
    grid.append({"camera":camera,"xyz":[float(x),float(y),0.],
     "qa_only":True,"uv":uv((float(x),float(y),0.),camera)})
 return {"schema":"scp.visualqa_w8d.calibration.v1",
  "native_probe_frame_asymmetry":"OBSERVED_FRONT_TICK0_OBLIQUE_TICK23",
  "source_rig_clock":"24_FRAMES_AT_12FPS",
  "rights":RIGHTS,"verified_original_probe_count":len(probes),
  "max_uv_residual":max(x["max_uv_error"] for x in probes),
  "probes":probes,"qa_only_ground_grid":grid,
  "same_tick_source_projection":"AVAILABLE_IN_INDEPENDENT_GRID",
  "same_tick_NATIVE_camera_probe_pair":"NOT_AVAILABLE_PROBE_TICKS_DIFFER",
  "physical_camera_calibration":"NOT_APPLICABLE_SYNTHETIC",
  "human_behavior":"NOT_TESTED"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--artifact",required=True);p.add_argument("--out",required=True)
 a=p.parse_args();root=Path(a.artifact);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 source=json.loads((root/"source.json").read_text())
 native=json.loads((root/"rendered"/"native_render_receipt.json").read_text())
 if native.get("rights")!=RIGHTS or native.get("source_motion_sha256")!=sha(root/"source.json"):
  raise ValueError("W8D_NATIVE_SOURCE_CUSTODY")
 result=audit(source,native)
 result["source_sha256"]=sha(root/"source.json")
 (out/"camera_calibration.json").write_text(json.dumps(result,sort_keys=True,indent=2)+chr(10))
 print("W8D_REPROJECTION_PROBES_VERIFIED_WITH_HISTORIC_TICK_ASYMMETRY",result["max_uv_residual"])
if __name__=="__main__":main()
