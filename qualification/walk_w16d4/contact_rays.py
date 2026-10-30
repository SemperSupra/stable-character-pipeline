"""W16-D4 original synthetic heel/toe sole event and ACTUAL C2 GLB ray checks.

Two evidence domains must never be joined without owner/source geometry:
- independent explicit fabricated heel/toe source tags, tested as a new primitive
- real sampled C2 weighted mesh with NO such tags; native contact ABSTAIN.
"""
import argparse,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w16d3"))
from mesh_checks import read_geometry,ray_triangle,CAMERA,ACTORS,FRAMES
SINGLE_GROUND=1e-4
STANCE_SLIP=1e-3
SWING_CLEARANCE=.025
def near(a,b):return math.dist(a,b)
def validate_sole(stream):
 if stream.get("schema")!="scp.walk_d4_explicit_original_sole.v1":raise ValueError("SOLE_SCHEMA")
 if stream.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":raise ValueError("SOLE_RIGHTS")
 if stream.get("source")!="UNRELATED_EXPLICIT_SYNTHETIC_PRIMITIVE":raise ValueError("SOLE_FALSE_NATIVE_SOURCE")
 samples=stream.get("frames")
 if not isinstance(samples,list) or len(samples)!=5:raise ValueError("SOLE_FRAME_COUNT")
 previous=None;observed_stance=0;observed_swing=0
 for index,f in enumerate(samples):
  if f.get("index")!=index or f.get("time_num")!=index or f.get("time_den")!=12:raise ValueError("SOLE_CLOCK")
  state=f.get("state")
  pts=f.get("landmarks")
  if not isinstance(pts,dict) or set(pts)!={"heel","toe"}:raise ValueError("SOLE_MISSING_HEEL_OR_TOE")
  for name,v in pts.items():
   if len(v)!=3 or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in v):
    raise ValueError("SOLE_LANDMARK_NONFINITE")
   if v[2]<-SINGLE_GROUND:raise ValueError("SOLE_GROUND_PENETRATION")
  if state=="stance":
   if any(abs(v[2])>SINGLE_GROUND for v in pts.values()):raise ValueError("SOLE_FALSE_STANCE_HOVER")
   if previous:
    if any(near(previous[k],pts[k])>STANCE_SLIP for k in pts):raise ValueError("SOLE_ANCHOR_SLIP")
   previous=pts;observed_stance+=1
  elif state=="swing":
   if any(v[2]<SWING_CLEARANCE for v in pts.values()):raise ValueError("SOLE_FALSE_SWING_CLEARANCE")
   previous=None;observed_swing+=1
  else:raise ValueError("SOLE_INVALID_CONTACT")
 if observed_stance!=3 or observed_swing!=2:raise ValueError("SOLE_EVENT_SEQUENCE")
 return {"stance":observed_stance,"swing":observed_swing,"maximum_ground_error":SINGLE_GROUND}

def separate_sole():
 frames=[]
 for i in range(5):
  state="stance" if i<=2 else "swing"
  z=0. if state=="stance" else .05+.01*(i-3)
  y=0. if state=="stance" else .03*(i-2)
  frames.append({"index":i,"time_num":i,"time_den":12,"state":state,
   "landmarks":{"heel":[0.,y,z],"toe":[.20,y,z]}})
 return {"schema":"scp.walk_d4_explicit_original_sole.v1","rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
  "source":"UNRELATED_EXPLICIT_SYNTHETIC_PRIMITIVE","frames":frames}

def occlusion(sampled,faces):
 """ACTUAL source triangles and camera ray from CAMERA to original 3D world vert.
 Return opposing actor occlusion counts (not self-occlusion/pixel visibility).
 """
 observations=0;counts={a:0 for a in ACTORS};min_depth=math.inf
 for f in FRAMES:
  row=sampled[str(f)]
  for actor in ACTORS:
   other=ACTORS[1] if actor==ACTORS[0] else ACTORS[0]
   for vertex in row[actor]:
    ray=tuple(vertex[j]-CAMERA[j] for j in range(3))
    if math.sqrt(sum(v*v for v in ray))<1e-9:raise ValueError("CAMERA_SAME_AS_VERTEX")
    observations+=1
    for i,j,k in faces[other]:
     vs=row[other]
     depth=ray_triangle(CAMERA,ray,vs[i],vs[j],vs[k])
     if depth is not None and 1e-6<depth<1-1e-6:
      counts[actor]+=1;min_depth=min(min_depth,depth);break
 return {"opposing_actor_occluded_vertex_count":counts,"ray_vertex_observations":observations,
  "nearest_occluder_ray_fraction":None if math.isinf(min_depth) else min_depth}

def run(glb,truth,profile):
 if profile not in ("forward","outward"):raise ValueError("PROFILE")
 s,faces,sha=read_geometry(glb,truth)
 native_min=min(v[2] for row in s["world_vertices"].values() for pts in row.values() for v in pts)
 if native_min<-.0001:raise ValueError("NATIVE_GROUND_PENETRATION")
 sole=validate_sole(separate_sole())
 rays=occlusion(s["world_vertices"],faces)
 if rays["ray_vertex_observations"]!=784:raise ValueError("NATIVE_INDEXED_VERTEX_COVERAGE")
 if native_min<.025:raise ValueError("NATIVE_GROUND_CLASSIFICATION_REQUIRES_REVIEW")
 return {"schema":"scp.walk_w16d4_separate_contact_and_native_ray.v1",
  "status":"PASS_EXPLICIT_ARTIFICIAL_SOLE_AND_NATIVE_OPPOSING_RAYS",
  "profile":profile,"glb_sha256":sha,"native_source_min_mesh_height":native_min,
  "actual_native_contact":"ABSTAIN_NATIVE_FOUR_BONE_MESH_UNLABELED_HOVERS_ABOVE_GROUND",
  "sole_test_scope":"UNRELATED_SYNTHETIC_HEEL_TOE_NOT_RIG_BOUND",
  "pixel_visibility":"NOT_QUALIFIED_RAY_VERTEX_SAMPLES_ONLY",
  "full_swept_triangles":"NOT_QUALIFIED",
  "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
  "synthetic_sole":sole,**rays}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--glb",required=True);p.add_argument("--truth",required=True)
 p.add_argument("--profile",choices=("forward","outward"),required=True)
 p.add_argument("--out",required=True);a=p.parse_args()
 r=run(a.glb,a.truth,a.profile)
 Path(a.out).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W16D4_NATIVE_RAY_SEPARATE_SOLE_PASS",json.dumps(r,sort_keys=True))
if __name__=="__main__":main()
