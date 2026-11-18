"""N04B three-pose true-surface vs nearest vertex; independent triangle oracle."""
import hashlib,json,math,platform,statistics,time,sys
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import open3d as o3d
import importlib.metadata
from nonplanar_oracle import wavy_mesh,queries,reference_distances
def timed(fn):
 out=[];result=None
 for _ in range(5):
  t=time.perf_counter_ns();result=fn();out.append((time.perf_counter_ns()-t)/1e6)
 return result,statistics.median(out)
def summary(a):return {"max_m":float(np.max(a)),"p50_m":float(np.median(a)),"p95_m":float(np.quantile(a,.95))}
def main():
 rows=[]
 for phase in (.35,.8,1.3):
  vertices,faces=wavy_mesh(phase)
  pts=queries(phase)
  ref=np.array(reference_distances(vertices,faces,pts))
  v=np.array(vertices,dtype=np.float64)
  q=np.array(pts,dtype=np.float64)
  kd=cKDTree(v)
  vd,vt=timed(lambda:kd.query(q,k=1,workers=1)[0])
  scene=o3d.t.geometry.RaycastingScene()
  scene.add_triangles(o3d.t.geometry.TriangleMesh(o3d.core.Tensor(v.astype(np.float32)),o3d.core.Tensor(np.array(faces,dtype=np.int32))))
  closest,tt=timed(lambda:scene.compute_closest_points(o3d.core.Tensor(q.astype(np.float32)))["points"].numpy())
  td=np.linalg.norm(q-closest.astype(np.float64),axis=1)
  ve=np.abs(vd-ref);te=np.abs(td-ref)
  if not np.isfinite(te).all():raise ValueError("NONFINITE_TRIANGLE_RESULT")
  rows.append({"phase":phase,"vertex_abs_error":summary(ve),"triangle_abs_error":summary(te),
               "vertex_query_median_ms":vt,"triangle_query_median_ms":tt,
               "point_count":len(pts),"source_vertices":len(v),"source_triangles":len(faces)})
 ok=(all(r["triangle_abs_error"]["max_m"]<3e-5 and r["vertex_abs_error"]["p50_m"]>.001 and r["triangle_abs_error"]["max_m"]<=r["vertex_abs_error"]["max_m"] for r in rows))
 result={"schema":"scp.n04b.deforming-triangle.v1","verdict":"PASS_NARROW" if ok else "RED",
         "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"python":platform.python_version(),
         "packages":{x:importlib.metadata.version(x) for x in ("open3d-cpu","scipy","numpy")},
         "source":"ORIGINAL_SYNTHETIC_NONPLANAR_GRID","oracle":"independent_Ericson_triangle_region_closest_point_double",
         "third_party_assets":False,"native_body_registration_accepted":False,"uv_weights_arap_accepted":False,
         "phases":rows,"performance_scope":"warm_query_only_not_total_pipeline"}
 print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
 if not ok:sys.exit(12)
if __name__=="__main__":main()
