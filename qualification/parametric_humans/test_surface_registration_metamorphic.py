"""Independent synthetic registration metamorphic invariants and bounded workload.

Proof here covers coordinate changes/mesh vertex indexing on an admitted tiny
synthetic body quad. It is NOT photographic reconstruction, anatomical fitting
or physically qualified skinning. No third-party model/weight dependency.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import time
import unittest

from surface_registration_v1 import fit_once
from test_surface_registration_v1 import fixture


def translate(vec):
    return [vec[0] + 2.0, vec[1] - 3.0, vec[2] + 5.0]


def rotate(vec):
    # Proper rigid rotation, +90 degrees around Y.
    return [vec[2], vec[1], -vec[0]]


def transform(document, position, normal=None):
    clone=json.loads(json.dumps(document))
    clone["vertices"]=[position(v) for v in document["vertices"]]
    clone["normals"]=[(normal or position)(v) for v in document["normals"]]
    for observation in clone["correspondences"]:
        if observation["status"] == "ADMITTED":
            observation["point"]=position(observation["point"])
    return clone


def run_metamorphic():
    src=fixture()
    reference=fit_once(src)
    checks={}
    # Geometry is in real-world metres; arbitrary origins must not alter fit.
    shifted=transform(src,translate,lambda v:v)
    shifted_result=fit_once(shifted)
    checks["translation_origin_equivariance"]=all(
        all(abs(a-b)<1e-10 for a,b in zip(got,translate(want)))
        for got,want in zip(shifted_result["vertices"],reference["vertices"])
    )
    # Rigid-frame transform rotates normals AND observations, not just vertices.
    moved=transform(src,rotate,rotate)
    moved_result=fit_once(moved)
    checks["rigid_rotation_equivariance"]=all(
        all(abs(a-b)<1e-10 for a,b in zip(got,rotate(want)))
        for got,want in zip(moved_result["vertices"],reference["vertices"])
    )
    # Uniform unit conversion is valid only when per-step metric bounds scale.
    scaled=transform(src,lambda v:[2*x for x in v],lambda v:v)
    scaled["options"]["max_normal_step_m"]*=2
    scaled["options"]["max_tangent_step_m"]*=2
    scaled_result=fit_once(scaled)
    checks["uniform_scale_with_metric_bounds"]=all(
        all(abs(a-2*b)<1e-10 for a,b in zip(got,want))
        for got,want in zip(scaled_result["vertices"],reference["vertices"])
    )
    # Vertex memory/index order is not part of physical morphology.
    permutation=[2,0,3,1]
    inverse={old:new for new,old in enumerate(permutation)}
    permuted=json.loads(json.dumps(src))
    for field in ("vertices","normals","correspondences"):
        permuted[field]=[src[field][old] for old in permutation]
    permuted["triangles"]=[[inverse[idx] for idx in face] for face in src["triangles"]]
    permuted_result=fit_once(permuted)
    checks["topology_preserving_vertex_reindex"]=all(
        all(abs(a-b)<1e-10 for a,b in zip(permuted_result["vertices"][new],reference["vertices"][old]))
        for new,old in enumerate(permutation)
    )
    return checks


def grid(n=33):
    """Produce ~1k vertices and ~2k actual triangle checks, original only."""
    out=fixture()
    out["vertices"]=[[float(i)/(n-1),float(j)/(n-1),0.] for j in range(n) for i in range(n)]
    out["normals"]=[[0.,0.,1.] for _ in out["vertices"]]
    out["correspondences"]=[{"status":"ADMITTED","surface":"BODY",
                              "point":[v[0],v[1],.015],"confidence":1.}
                             for v in out["vertices"]]
    out["triangles"]=[]
    for j in range(n-1):
        for i in range(n-1):
            a=j*n+i
            out["triangles"].append([a,a+1,a+n+1])
            out["triangles"].append([a,a+n+1,a+n])
    return out


class SurfaceMetamorphic(unittest.TestCase):
    def test_four_coordinate_and_topology_equivariances(self):
        result=run_metamorphic()
        self.assertEqual(len(result),4)
        self.assertTrue(all(result.values()),result)

    def test_33_grid_workload_and_receipt(self):
        data=grid()
        before=time.perf_counter_ns()
        result=fit_once(data)
        elapsed=time.perf_counter_ns()-before
        self.assertEqual(len(result["vertices"]),1089)
        self.assertEqual(len(result["triangles"]),2048)
        self.assertEqual(result["stats"]["fitted"],1089)
        self.assertTrue(all(abs(v[2]-.015)<1e-10 for v in result["vertices"]))
        path=os.getenv("SCP_SURFACE_METAMORPHIC_OUT")
        if path:
            source=Path(__file__).with_name("surface_registration_v1.py").read_bytes()
            blob=json.dumps(data,sort_keys=True,separators=(",",":")).encode()
            record={
                "schema":"scp.validator.metamorphic.v1",
                "validator":"scp.original_human.synthetic_surface_registration",
                "source_class":"SYNTHETIC_GRID_AND_QUAD_ONLY",
                "validator_sha256":hashlib.sha256(source).hexdigest(),
                "grid_input_sha256":hashlib.sha256(blob).hexdigest(),
                "metamorphic_checks":run_metamorphic(),
                "grid_vertices":1089,"grid_triangles":2048,
                "grid_latency_ns":elapsed,"python":platform.python_version(),
                "external_photo_fit":"NOT_RUN","anatomical_fidelity":"UNKNOWN",
                "merge_release_CPE_approval":False,
            }
            self.assertTrue(all(record["metamorphic_checks"].values()))
            Path(path).write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
            print("SURFACE_METAMORPHIC_SYNTHETIC_ONLY",record["validator_sha256"],elapsed)


if __name__ == "__main__":
    unittest.main()
