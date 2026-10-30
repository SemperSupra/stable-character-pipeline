"""W16-D5 conservative continuous swept triangle separation for LINEAR vertex tracks.

For each actual animated GLB triangle, the swept AABB is the union of its
two time-endpoint triangles. Any disjoint axis certifies no triangle contact
for EVERY linear-interpolated t in [0,1]. Overlap is UNKNOWN/REJECT, never
false PASS. This is not a certificate for Blender nonlinear paths between
sampled source poses, surface forces, self or human collision.
"""
import argparse,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w16d3"))
from mesh_checks import read_geometry,ACTORS,FRAMES
THRESHOLD=.025
def swept_aabb(vertices0,vertices1,tri):
 pts=[vs[i] for vs in (vertices0,vertices1) for i in tri]
 if any(len(p)!=3 or any(not math.isfinite(x) for x in p) for p in pts):
  raise ValueError("NONFINITE_SWEEP")
 return tuple((min(p[k] for p in pts),max(p[k] for p in pts)) for k in range(3))
def separation(a,b):
 # Separation of full swept AABB along at least one coordinate. Positive
 # means a provable continuous nonintersection, negative means UNKNOWN.
 return max(max(a[k][0]-b[k][1],b[k][0]-a[k][1]) for k in range(3))
def segment_bounds(older,newer,faces_a,faces_b,actor_a,actor_b):
 first=[swept_aabb(older[actor_a],newer[actor_a],f) for f in faces_a]
 second=[swept_aabb(older[actor_b],newer[actor_b],f) for f in faces_b]
 minimum=math.inf;comparisons=0
 for x in first:
  for y in second:
   margin=separation(x,y)
   comparisons+=1;minimum=min(minimum,margin)
   if margin<=THRESHOLD:
    raise ValueError("UNCERTIFIED_CONTINUOUS_TRIANGLE_PAIR")
 if minimum==math.inf:raise ValueError("NO_ACTUAL_TRIANGLE_COMPARISONS")
 return minimum,comparisons
def verify(glb,truth,profile):
 if profile not in ("forward","outward"):raise ValueError("PROFILE")
 src,faces,sha=read_geometry(glb,truth)
 if set(faces)!=set(ACTORS):raise ValueError("MISSING_NATIVE_ACTORS")
 observed=src["world_vertices"]
 if set(observed)!=set(map(str,FRAMES)):raise ValueError("SOURCE_CLOCK_COVERAGE")
 min_interactor=math.inf;min_intra=math.inf;checks=0
 for j in range(1,len(FRAMES)):
  prev,nxt=observed[str(FRAMES[j-1])],observed[str(FRAMES[j])]
  a,b=ACTORS
  margin,n=segment_bounds(prev,nxt,faces[a],faces[b],a,b)
  checks+=n;min_interactor=min(min_interactor,margin)
  for actor in ACTORS:
   # C2 original leg meshes are explicitly indexed 0..27 left, 28..55 right.
   # Do not pretend these procedural groups are human anatomical feet.
   left=[tri for tri in faces[actor] if all(i<28 for i in tri)]
   right=[tri for tri in faces[actor] if all(28<=i<56 for i in tri)]
   if len(left)+len(right)!=len(faces[actor]) or not left or not right:
    raise ValueError("UNEXPECTED_CROSS_LEG_TRIANGLE")
   q,n=segment_bounds(prev,nxt,left,right,actor,actor)
   checks+=n;min_intra=min(min_intra,q)
 native_min=min(v[2] for f in observed.values() for xyz in f.values() for v in xyz)
 if native_min<0:raise ValueError("GROUND_PENETRATION")
 return {"schema":"scp.walk_w16d5_linear_swept_triangle_certificate.v1",
  "status":"PASS_LINEAR_SWEPT_TRIANGLE_AABB_SEPARATION_ONLY",
  "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC","profile":profile,
  "native_glb_sha256":sha,"frame_index_samples":list(FRAMES),
  "actor_count":2,"source_world_vertex_observations":784,
  "swept_triangle_pair_checks":checks,
  "minimum_interactor_aabb_separation":min_interactor,
  "minimum_intra_actor_leg_aabb_separation":min_intra,
  "source_min_ground_clearance":native_min,
  "continuous_criterion":"SWEPT_VERTEX_LINEAR_INTERVAL_AABB_SUFFICIENT_CERTIFICATE",
  "nonlinear_native_interpolation":"ABSTAIN_NOT_CERTIFIED",
  "rendered_pixel_visibility":"RED_EXTERNAL_VISUAL_QA_NEEDS_FULL_BODY",
  "anatomical_foot_contact":"ABSTAIN_UNLABELED_PROXY_HOVERS",
  "scope":"LINEAR_PROXY_SWEPT_TRIANGLES_NOT_ACTUAL_NONLINEAR_SKIN_UNSAMPLED_OR_HUMAN"}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--glb",required=True);p.add_argument("--truth",required=True)
 p.add_argument("--profile",required=True);p.add_argument("--out",required=True)
 a=p.parse_args();r=verify(a.glb,a.truth,a.profile)
 Path(a.out).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print("W16D5_CONSERVATIVE_LINEAR_TRIANGLE_PASS",r["profile"],r["minimum_interactor_aabb_separation"],r["swept_triangle_pair_checks"])
if __name__=="__main__":main()
