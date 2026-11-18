"""N04: SciPy vertex nearest vs Open3D triangle closest surface, public synthetic mesh only."""
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import time
import importlib.metadata
import numpy as np
from scipy.spatial import cKDTree
import open3d as o3d
from geometry_contract import exact_distance,grid,queries

def performance(fn, repeats=5):
 times=[]
 for _ in range(repeats):
  t=time.perf_counter_ns()
  result=fn()
  times.append((time.perf_counter_ns()-t)/1e6)
 return result,{"median_ms":statistics.median(times),"min_ms":min(times),"max_ms":max(times)}

def summarize(values):
 return {"p50":float(np.quantile(values,.5)),"p95":float(np.quantile(values,.95)),
         "maximum":float(np.max(values))}

def main():
 vertices,triangles=grid(20)
 raw=queries(4096)
 v=np.asarray(vertices,dtype=np.float64)
 tris=np.asarray(triangles,dtype=np.int32)
 q=np.asarray(raw,dtype=np.float64)
 truth=np.asarray([exact_distance(x) for x in raw])
 if not (np.isfinite(q).all() and np.isfinite(truth).all()):
  raise ValueError("NONFINITE_GEOMETRY")
 baseline=cKDTree(v)
 vdist,vperf=performance(lambda:baseline.query(q,k=1,workers=1)[0])
 points=o3d.core.Tensor(v.astype(np.float32),dtype=o3d.core.Dtype.Float32)
 faces=o3d.core.Tensor(tris,dtype=o3d.core.Dtype.Int32)
 mesh=o3d.t.geometry.TriangleMesh(points,faces)
 scene=o3d.t.geometry.RaycastingScene()
 scene.add_triangles(mesh)
 q_tensor=o3d.core.Tensor(q.astype(np.float32),dtype=o3d.core.Dtype.Float32)
 nearest,tri_perf=performance(lambda:scene.compute_closest_points(q_tensor)["points"].numpy())
 triangle=np.linalg.norm(q-np.asarray(nearest,dtype=np.float64),axis=1)
 if not np.isfinite(triangle).all():raise ValueError("NONFINITE_TRIANGLE_DISTANCE")
 vertex_err=np.abs(vdist-truth)
 triangle_err=np.abs(triangle-truth)
 index=np.arange(len(q))
 correct=(float(np.max(triangle_err))<2e-5
          and float(np.median(vertex_err))>0.002
          and float(np.max(triangle-vdist))<=2e-5
          and float(np.max(vertex_err))>0.01)
 report={
  "schema":"scp.n04.surface-correspondence.v1",
  "verdict":"PASS_NARROW" if correct else "RED",
  "synthetic_square_only":True,"native_body_fit_accepted":False,
  "registration_quality_accepted":False,"canonical":False,
  "python_version":platform.python_version(),
  "platform":platform.platform(),
  "libraries":{key:importlib.metadata.version(key) for key in ("numpy","scipy","open3d-cpu")},
  "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  "oracle":"closed_square_planar_nearest_point_double_precision",
  "mesh":{"vertices":len(v),"triangles":len(tris),"source":"ORIGINAL_SYNTHETIC_RECTANGULAR_SURFACE"},
  "points":len(q),"query_seed":20261118,
  "nearest_vertex":{"abs_error_m":summarize(vertex_err),"query_only_ms":vperf},
  "nearest_triangle":{"abs_error_m":summarize(triangle_err),"query_only_ms":tri_perf},
  "performance_note":"Same process, 5 repetitions, warm-started query; not full geometry build, install, end-to-end or character fit",
  "technical_correctness":correct}
 print(json.dumps(report,sort_keys=True,indent=2,allow_nan=False))
 if not correct:raise SystemExit(12)

if __name__=="__main__":main()
