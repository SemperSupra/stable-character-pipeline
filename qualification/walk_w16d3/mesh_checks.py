"""W16-D3: non-Blender native W16-C2 dual-leg GLB sampled triangle, contact and camera falsifiers.

Coordinates for pre-export world truth are Blender Z-up, *not* the GLB Y-up
serialization. Tests use real evaluated W15 world XYZ and original glTF indexed
triangles; no imagined heel/toe labels, no biomechanical force claim.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w15"))
from pure_glb_reader import read_glb, accessor, evaluate

FRAMES=(0,12,24,36,48,60,71)
ACTORS=("CobaltOriginal","MarigoldOriginal")
RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
GROUND_TOL=1e-4
NEAR_SURFACE=.025
FRAME_STEP_LIMIT=4.0 # source scene units per sampled interval, NOT physical gait speed
CAMERA=(0.0,-7.0,2.0)
CAMERA_TARGET=(0.0,0.0,.75)
ORTHO_WIDTH=5.5
SCREEN_ASPECT=320/180
EPS=1e-10

def minus(a,b):return tuple(a[i]-b[i] for i in range(3))
def plus(a,b):return tuple(a[i]+b[i] for i in range(3))
def scale(a,v):return tuple(a[i]*v for i in range(3))
def dot(a,b):return sum(a[i]*b[i] for i in range(3))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def norm(a):return math.sqrt(dot(a,a))
def unit(a):
 n=norm(a)
 if n<EPS:raise ValueError("DEGENERATE_CAMERA_OR_TRIANGLE")
 return scale(a,1/n)

def read_geometry(glb,truthfile):
 raw=Path(glb).read_bytes()
 doc,blob,sha=read_glb(glb)
 t=json.loads(Path(truthfile).read_text())
 if t.get("schema")!="scp.walk_w15_source_truth.v1" or t.get("source_rights")!=RIGHTS or t.get("glb_sha256")!=sha:
  raise ValueError("SOURCE_RIGHTS_EXACT_GLB_SHA")
 if t.get("frames")!=list(FRAMES):raise ValueError("NONCANONICAL_SOURCE_FRAMES")
 if set(t.get("world_vertices",{}))!=set(map(str,FRAMES)):raise ValueError("MISSING_SOURCE_FRAMES")
 faces={}
 for node in doc["nodes"]:
  if "mesh" not in node or "skin" not in node:continue
  name=node["name"].split("_SkinnedMesh")[0]
  if name not in ACTORS or name in faces:raise ValueError("UNEXPECTED_MESH_ACTOR")
  fs=[];vertex_offset=0
  for prim in doc["meshes"][node["mesh"]]["primitives"]:
   if prim.get("mode",4)!=4 or "indices" not in prim:raise ValueError("TRIANGLE_INDEXED_MESH_REQUIRED")
   positions=accessor(doc,blob,prim["attributes"]["POSITION"])
   indices=[int(i[0]) for i in accessor(doc,blob,prim["indices"])]
   if len(indices)%3:raise ValueError("TRIANGLE_INDEX_COUNT")
   if any(i>=len(positions) or i<0 for i in indices):raise ValueError("TRIANGLE_INDEX_BOUNDS")
   fs.extend(tuple(vertex_offset+i for i in indices[k:k+3]) for k in range(0,len(indices),3))
   vertex_offset+=len(positions)
  faces[name]=fs
 if set(faces)!=set(ACTORS):raise ValueError("TWO_ACTORS_MISSING")
 for frame in FRAMES:
  observed=evaluate(doc,blob,frame/12)
  expected=t["world_vertices"][str(frame)]
  if set(expected)!=set(ACTORS) or set(observed)!=set(ACTORS):raise ValueError("SOURCE_ACTOR_SET")
  for actor in ACTORS:
   vs=expected[actor]
   if len(vs)!=56 or len(observed[actor])!=len(vs):raise ValueError("SOURCE_INDEXED_VERTEX_COVERAGE")
   if any(len(v)!=3 or any(not math.isfinite(c) for c in v) for v in vs):raise ValueError("SOURCE_NONFINITE_XYZ")
   if any(math.dist(a,b)>5e-4 for a,b in zip(vs,observed[actor])):raise ValueError("THIRD_READER_SOURCE_MISMATCH")
   if any(any(i>=len(vs) for i in tri) for tri in faces[actor]):raise ValueError("FACE_VERTEX_OUT_OF_RANGE")
 return t,faces,sha

def ray_triangle(origin,ray,a,b,c):
 ab=minus(b,a);ac=minus(c,a)
 h=cross(ray,ac);den=dot(ab,h)
 if abs(den)<EPS:return None
 inv=1/den;s=minus(origin,a);u=inv*dot(s,h)
 if u<0 or u>1:return None
 q=cross(s,ab);v=inv*dot(ray,q)
 if v<0 or u+v>1:return None
 dist=inv*dot(ac,q)
 return dist if dist>EPS else None

def point_triangle_distance(p,a,b,c):
 # Closest point on nondegenerate 3D triangle; Ericson region tests.
 ab=minus(b,a);ac=minus(c,a);ap=minus(p,a)
 d1=dot(ab,ap);d2=dot(ac,ap)
 if d1<=0 and d2<=0:return norm(ap)
 bp=minus(p,b);d3=dot(ab,bp);d4=dot(ac,bp)
 if d3>=0 and d4<=d3:return norm(bp)
 vc=d1*d4-d3*d2
 if vc<=0 and d1>=0 and d3<=0:
  v=d1/(d1-d3);return norm(minus(p,plus(a,scale(ab,v))))
 cp=minus(p,c);d5=dot(ab,cp);d6=dot(ac,cp)
 if d6>=0 and d5<=d6:return norm(cp)
 vb=d5*d2-d1*d6
 if vb<=0 and d2>=0 and d6<=0:
  w=d2/(d2-d6);return norm(minus(p,plus(a,scale(ac,w))))
 va=d3*d6-d5*d4
 if va<=0 and (d4-d3)>=0 and (d5-d6)>=0:
  w=(d4-d3)/((d4-d3)+(d5-d6))
  return norm(minus(p,plus(b,scale(minus(c,b),w))))
 denom=va+vb+vc
 if abs(denom)<EPS:return min(norm(ap),norm(bp),norm(cp))
 inv=1/denom;v=vb*inv;w=vc*inv
 return norm(minus(p,plus(a,plus(scale(ab,v),scale(ac,w)))))

def actor_surface_clearance(va,fa,vb,fb):
 # Triangle-to-opposing-vertex samples and edge-triangle crossings. This is
 # NOT continuous swept triangle-triangle distance between sampled frames.
 best=math.inf
 for points,other,tris in ((va,vb,fb),(vb,va,fa)):
  for v in points:
   for i,j,k in tris:
    a,b,c=other[i],other[j],other[k]
    dist=point_triangle_distance(v,a,b,c)
    best=min(best,dist)
    if best<NEAR_SURFACE:return best
 for v,faces,other,otherfaces in ((va,fa,vb,fb),(vb,fb,va,fa)):
  for i,j,k in faces:
   for edge in ((i,j),(j,k),(k,i)):
    e0=v[edge[0]];ev=minus(v[edge[1]],e0)
    for ia,ib,ic in otherfaces:
     hit=ray_triangle(e0,ev,other[ia],other[ib],other[ic])
     if hit is not None and hit<=1+EPS:return 0.
 return best

def camera_frame():
 forward=unit(minus(CAMERA_TARGET,CAMERA))
 right=unit(cross(forward,(0.,0.,1.)))
 up=unit(cross(right,forward))
 return forward,right,up

def camera_visible(vertex):
 forward,right,up=camera_frame();v=minus(vertex,CAMERA)
 return (dot(v,forward)>0 and abs(dot(v,right))<=ORTHO_WIDTH/2
         and abs(dot(v,up))<=ORTHO_WIDTH/SCREEN_ASPECT/2)

def swept_vertex_minimum(a0,a1,b0,b1):
 """Continuous piecewise-linear sampled vertex tracks; NOT swept triangles."""
 minimum=math.inf
 if not(len(a0)==len(a1) and len(b0)==len(b1)):
  raise ValueError("SWEPT_VERTEX_INDEX_TRACK_DISCONTINUITY")
 for i in range(len(a0)):
  for j in range(len(b0)):
   p=minus(a0[i],b0[j])
   velocity=minus(minus(a1[i],a0[i]),minus(b1[j],b0[j]))
   vv=dot(velocity,velocity)
   t=min(1.,max(0.,-dot(p,velocity)/vv)) if vv>1e-14 else 0.
   minimum=min(minimum,norm(plus(p,scale(velocity,t))))
 return minimum

def verify_frames(truth,faces):
 source=truth["world_vertices"]
 minima=[];maxstep=0.; min_separation=math.inf
 visible_by_actor={a:0 for a in ACTORS}
 swept_minimum=math.inf
 procedural_leg_min={a:{'Left':math.inf,'Right':math.inf} for a in ACTORS}
 for n,f in enumerate(FRAMES):
  frame=source[str(f)]
  for actor in ACTORS:
   pts=frame[actor]
   if len(pts)!=56:raise ValueError('PROCEDURAL_TWO_LEG_56_VERTICES_REQUIRED')
   for group,start in (('Left',0),('Right',28)):
    procedural_leg_min[actor][group]=min(procedural_leg_min[actor][group],min(v[2] for v in pts[start:start+28]))
   mn=min(v[2] for v in pts) # explicit BLENDER Z-UP source
   if mn < -GROUND_TOL:raise ValueError("SOURCE_MESH_GROUND_PENETRATION")
   minima.append(mn)
   if not any(camera_visible(v) for v in pts):raise ValueError("SOURCE_ACTOR_OUTSIDE_CAMERA_PROXY")
   visible_by_actor[actor]+=sum(camera_visible(v) for v in pts)
   if n:
    older=source[str(FRAMES[n-1])][actor]
    displacement=max(math.dist(v,w) for v,w in zip(older,pts))
    maxstep=max(maxstep,displacement)
    if displacement>FRAME_STEP_LIMIT:raise ValueError("SAMPLED_VERTEX_TELEPORT")
  a,b=ACTORS
  if n:
   previous=source[str(FRAMES[n-1])]
   sweep=swept_vertex_minimum(previous[a],frame[a],previous[b],frame[b])
   swept_minimum=min(swept_minimum,sweep)
   if sweep<NEAR_SURFACE:raise ValueError('SWEPT_VERTEX_TRACK_COLLISION')
  separation=actor_surface_clearance(frame[a],faces[a],frame[b],faces[b])
  min_separation=min(min_separation,separation)
  if separation<NEAR_SURFACE:raise ValueError("SAMPLED_TRIANGLE_SURFACE_COLLISION")
 return {"sampled_triangle_min_separation":min_separation,
         "min_mesh_ground_clearance":min(minima),"max_vertex_step":maxstep,
         "camera_proxy_vertex_count":visible_by_actor,
         "swept_linear_vertex_track_minimum":swept_minimum,
         "procedural_leg_submesh_min_z":procedural_leg_min}

def run(glb,source,profile):
 if profile not in ("forward","outward"):raise ValueError("PROFILE")
 truth,faces,sha=read_geometry(glb,source)
 stats=verify_frames(truth,faces)
 return {"schema":"scp.walk_w16d3_dual_leg_mesh.v1",
  "status":"PASS_SAMPLED_MESH_GEOMETRY_ONLY",
  "profile":profile,"source_rights":RIGHTS,"exact_glb_sha256":sha,
  "native_source_basis":"BLENDER_WORLD_XYZ_Z_UP",
  "frames":list(FRAMES),"indexed_vertex_observations":784,
  "triangles_per_actor":{k:len(v) for k,v in faces.items()},
  "ground_tolerance_source_units":GROUND_TOL,
  "collision_surface_threshold_source_units":NEAR_SURFACE,
  "scope":"DUAL_LEG_ACTUAL_TRIANGLE_SAMPLES_AND_LINEAR_SWEPT_VERTEX_TRACKS_NOT_FULL_SWEPT_TRIANGLES_NOT_LABELED_HEEL_TOE_NOT_BIOMECHANICS",
  "contact_admission":"ABSTAIN_PROCEDURAL_LEG_GROUPS_NOT_HEEL_TOE_SOLE_ANATOMY",
  "occlusion_admission":"ABSTAIN_ORTHO_FRUSTUM_PROXY_ONLY",
  "continuous_mesh_admission":"ABSTAIN_VERTEX_TRACK_SWEEP_NOT_SURFACE_TRIANGLE_SWEEP",
  **stats}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--glb",required=True);p.add_argument("--truth",required=True)
 p.add_argument("--profile",choices=("forward","outward"),required=True)
 p.add_argument("--out",required=True);a=p.parse_args()
 receipt=run(a.glb,a.truth,a.profile)
 Path(a.out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
 print("W16D2_SAMPLED_ACTUAL_MESH_PASS",json.dumps(receipt,sort_keys=True))
if __name__=="__main__":main()
