"""Independent stdlib camera observer on native Blender W9-C receipt.
Uses source XYZ, frozen camera parameters and own orthographic math, not bpy.
"""
import argparse,copy,hashlib,json,math
from pathlib import Path
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
CAMERAS={"OriginalFront":((0.,-8.5,2.8),(0.,0.,1.15)),
         "OriginalOblique":((7.5,-7.,3.1),(0.,0.,1.15))}
ACTORS=("CobaltOriginal","MarigoldOriginal")
PARTS={"Head":2.17,"Torso":1.5,"Pelvis":1.09}
def sha(b):return hashlib.sha256(b).hexdigest()
def minus(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(x):
 n=math.sqrt(sum(z*z for z in x))
 if n<=1e-8 or not math.isfinite(n):raise ValueError("W9C_INVALID_CAMERA")
 return tuple(z/n for z in x)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def uv(pos,cam):
 eye,target=CAMERAS[cam]
 f=unit(minus(target,eye));right=unit(cross(f,(0.,0.,1.)));up=unit(cross(right,f))
 p=minus(pos,eye)
 return (.5+dot(p,right)/5.75,.5+dot(p,up)/(5.75*360./640.))
def audit(source_raw,receipt):
 s=json.loads(source_raw)
 if s.get("schema")!="scp.walk_w7a_original_approach.v1" or s.get("rights")!=RIGHTS or s.get("fps_num")!=12 or s.get("fps_den")!=1 or len(s.get("actors",[]))!=2:
  raise ValueError("W9C_SOURCE_RIGHTS_OR_CLOCK")
 if receipt.get("schema")!="scp.visualqa.w9c_native_same_tick.v1" or receipt.get("source_sha256")!=sha(source_raw) or receipt.get("rights")!=RIGHTS:
  raise ValueError("W9C_NATIVE_SOURCE_SHA")
 if receipt.get("frames")!=24 or receipt.get("fps_num")!=12 or receipt.get("fps_den")!=1 or receipt.get("same_tick_camera_pairs") is not True:
  raise ValueError("W9C_NATIVE_CLOCK_OR_PAIR")
 rows=receipt.get("samples",[])
 expected=24*2*2*3
 if len(rows)!=expected:raise ValueError("W9C_INCOMPLETE_TICK_CAMERAS")
 indexed={(r.get("tick"),r.get("camera"),r.get("actor"),r.get("part")):r for r in rows}
 if len(indexed)!=expected:raise ValueError("W9C_DUPLICATE_FRAME_CAMERA_ACTOR_PART")
 maxXYZ=0.;maxUV=0.
 for tick in range(24):
  for cam in CAMERAS:
   for ai,actor in enumerate(ACTORS):
    original=s["actors"][ai]
    if original.get("id")!=actor or len(original.get("frames",[]))!=24:raise ValueError("W9C_WRONG_ACTOR_ID")
    f=original["frames"][tick]
    if (f.get("index"),f.get("time_num"),f.get("time_den"))!=(tick,tick,12):
     raise ValueError("W9C_GT_CLOCK")
    for part,z in PARTS.items():
     key=(tick,cam,actor,part)
     if key not in indexed:raise ValueError("W9C_MISSING_SAME_TICK_WITNESS")
     r=indexed[key]
     if (r.get("time_num"),r.get("time_den"))!=(tick,12):raise ValueError("W9C_NATIVE_CLOCK_MISMATCH")
     xyz=r.get("xyz");measured=r.get("uv")
     if not isinstance(xyz,list) or len(xyz)!=3 or not all(isinstance(v,(float,int)) and math.isfinite(v) for v in xyz):
      raise ValueError("W9C_NATIVE_XYZ_BAD")
     if not isinstance(measured,list) or len(measured)!=2 or not all(isinstance(v,(float,int)) and math.isfinite(v) for v in measured):
      raise ValueError("W9C_NATIVE_UV_BAD")
     truth=(f["root_x"],f["root_y"],z)
     delta=math.dist(xyz,truth);maxXYZ=max(maxXYZ,delta)
     if delta>1e-5:raise ValueError("W9C_NATIVE_ROOT_DIFFERENT_FROM_ORIGINAL_SOURCE")
     error=math.dist(measured,uv(truth,cam));maxUV=max(maxUV,error)
     if error>1e-5:raise ValueError("W9C_INDEPENDENT_CAMERA_REPROJECTION_DISAGREES")
 return {"schema":"scp.visualqa.w9c_independent_clock_projection.v1",
   "source_sha256":sha(source_raw),"profile":s["profile"],
   "native_synchronized_camera_sample_count":len(rows),
   "same_tick_pair_count":24,
   "max_xyz_error":maxXYZ,"max_uv_error":maxUV,
   "status":"PASS_SYNCHRONIZED_SOURCE_PROJECTION_ONLY",
   "old_native_W7_W8_cam_probe_skew":"REMAINS_HISTORICAL_FAIL_NOT_REWRITTEN",
   "exact_W8_201_pixel_correspondence":"NOT_RUN_DIFFERENT_NATIVE_MODEL_BINARY",
   "human_behavior":"UNKNOWN_NOT_A_NORMATIVE_ORACLE"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--original",required=True);p.add_argument("--native",required=True);p.add_argument("--out",required=True)
 x=p.parse_args()
 source=(Path(x.original)/"source.json").read_bytes()
 receipt=json.loads(Path(x.native).read_text())
 o=audit(source,receipt)
 Path(x.out).write_text(json.dumps(o,indent=2,sort_keys=True)+"\n")
 print("W9C_FRESH_OBSERVER_SYNCHRONIZED_PROJECTION_ONLY",o["max_xyz_error"],o["max_uv_error"])
if __name__=="__main__":main()
