"""Index-stable shoe material support witnessing and trajectory diagnostics."""
import math,statistics
def select_ids(world_rows,candidates,minimum=8,ratio=.01):
 if not isinstance(world_rows,list) or not 100<=len(world_rows)<=200000:raise ValueError("MESH_SIZE")
 if not isinstance(candidates,list) or len(set(candidates))!=len(candidates) or len(candidates)<80:raise ValueError("UNQUALIFIED_SHOE_PARTITION")
 if any(type(i)!=int or not 0<=i<len(world_rows) for i in candidates):raise ValueError("MESH_INDEX_DRIFT")
 if not 0<ratio<=.05 or not 4<=minimum<=32:raise ValueError("SUPPORT_SELECTION_POLICY")
 for p in world_rows:
  if not isinstance(p,(list,tuple)) or len(p)!=3 or not all(type(v) in (float,int) and math.isfinite(v) for v in p):raise ValueError("NONFINITE_GEOMETRY")
 return sorted(sorted(candidates,key=lambda i:(world_rows[i][2],i))[:max(minimum,len(candidates)//100)])
def snapshot(world_rows,indices):
 if not indices or any(type(i)!=int or i<0 or i>=len(world_rows) for i in indices):raise ValueError("MATERIAL_IDS_INVALID")
 p=[world_rows[i] for i in indices]
 if any(len(z)!=3 or not all(math.isfinite(x) for x in z) for z in p):raise ValueError("MATERIAL_NONFINITE")
 return {"centroid_xyz_m":[sum(v[j] for v in p)/len(p) for j in range(3)],
         "min_z_m":min(v[2] for v in p),"sampled_indices":len(indices)}
def stats(points,dt):
 if not isinstance(points,list) or len(points)<4:raise ValueError("TRAJECTORY_LENGTH")
 if not math.isfinite(dt) or not 0<dt<=.1:raise ValueError("SOURCE_CLOCK")
 xyz=[p["centroid_xyz_m"] for p in points]
 speeds=[math.hypot(xyz[i][0]-xyz[i-1][0],xyz[i][1]-xyz[i-1][1])/dt for i in range(1,len(xyz))]
 return {"max_speed_mps":round(max(speeds),6),"median_speed_mps":round(statistics.median(speeds),6),
  "min_tracked_vertex_z_m":round(min(x["min_z_m"] for x in points),6),
  "max_tracked_vertex_z_m":round(max(x["min_z_m"] for x in points),6),
  "physical_stance_proven":False}
def overlap(a,b):
 if len(a)==0 or len(b)==0:raise ValueError("EMPTY_SUPPORT_IDS")
 return round(len(set(a)&set(b))/len(set(a)|set(b)),6)
