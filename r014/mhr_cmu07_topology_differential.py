"""R014 actual source-native MHR dimensionless skin differential, evidence only.

Reopens original source-derived Blender scene ONLY in admitted disposable runner.
No CMU trajectory, derived scene, mesh coordinates or images leave runner.
Historical frame-1 normal reversals remain *separate* from geometric checks.
"""
import argparse
import collections
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

parser = argparse.ArgumentParser()
parser.add_argument("--native-source", required=True, type=Path)
parser.add_argument("--numeric-receipt", required=True, type=Path)
parser.add_argument("--motion", required=True, choices=("07_01", "07_02"))
parser.add_argument("--variant", required=True, choices=("neutral",))
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
assert Path(bpy.data.filepath).resolve() == args.native_source.resolve()
source = json.loads(args.numeric_receipt.read_text())
assert source["status"] == "HOLD_NATIVE_GAIT_ANATOMY_AND_CINEMATIC_VIDEO"
assert source["original_source_motion"] == args.motion
assert source["variant"] == args.variant
assert source["capture_contact_provenance"] == "UNKNOWN_NOT_FORCE_MEASURED"
assert source["derived_full_animation_artifact_distribution"] == "WITHHELD_SOURCE_RIGHTS_VENUE_GATE"
assert source["source_mesh_vertices"] == 18439 and source["source_rig_bones"] == 126
assert source["gait_frames"] in (64, 66)
assert source["structural_contact_candidate"] is False
rig = bpy.data.objects["R014_MHR_neutral_rig"]
body = bpy.data.objects["R014_MHR_neutral_body"]
assert len(body.data.vertices) == 18439 and len(rig.data.bones) == 126
scene = bpy.context.scene
sample_frames = sorted(int(x) for x in source["skin_geometry_samples"])
assert len(sample_frames) == 5 and sample_frames[0] == 1
assert sample_frames[-1] == source["gait_frames"]
all_frames = range(1, source["gait_frames"] + 1)
sample_frame_set = set(sample_frames)

def geometry():
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    try:
        inverse = rig.matrix_world.inverted_safe()
        pts = np.asarray([list(inverse @ (evaluated.matrix_world @ v.co))
                          for v in mesh.vertices], dtype=np.float64)
        polys = [tuple(int(i) for i in f.vertices) for f in mesh.polygons]
    finally:
        evaluated.to_mesh_clear()
    assert pts.shape == (18439, 3) and np.isfinite(pts).all()
    return pts, polys

def normals_and_lengths(verts, indices):
    a, b, c = (verts[indices[:,i]] for i in range(3))
    n = np.cross(b - a, c - a)
    m = np.linalg.norm(n, axis=1)
    lengths = np.column_stack((np.linalg.norm(b - a, axis=1),
                               np.linalg.norm(c - b, axis=1),
                               np.linalg.norm(a - c, axis=1)))
    return n, m, lengths

scene.frame_set(1)
bpy.context.view_layer.update()
rest, polygons = geometry()
tris = np.asarray([(p[0],p[k],p[k+1])
                   for p in polygons for k in range(1,len(p)-1)], dtype=np.int32)
assert len(tris) == 36874
n0, m0, l0 = normals_and_lengths(rest, tris)
assert np.isfinite(m0).all() and np.min(m0) > 1e-11
assert np.min(l0) > 1e-9

# Build original stable topology adjacency. Shared-edge hinge differential
# is invariant to any *global* proper rotation or translation.
edges = collections.defaultdict(list)
for i, t in enumerate(tris):
    for v0, v1 in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
        edges[(min(int(v0), int(v1)), max(int(v0), int(v1)))].append(i)
if any(len(v) > 2 for v in edges.values()):
    raise ValueError("nonmanifold reference source MHR triangulated mesh")
pairs = np.asarray([v for v in edges.values() if len(v) == 2], dtype=np.int32)
assert pairs.ndim == 2 and pairs.shape[1] == 2
n0unit = n0 / m0[:,None]
ref_dihedral = np.einsum("ij,ij->i",n0unit[pairs[:,0]],n0unit[pairs[:,1]])
near_planar = ref_dihedral >= .95
count_near_planar = int(np.count_nonzero(near_planar))

def bvh_overlap_candidates(points):
    # Blender BVH returns potentially coplanar/near-touching pairs. Exclude
    # pairs sharing even one vertex, canonicalize duplicates, report only a
    # conservative collision *candidate*, not proven anatomical penetration.
    verts = [Vector(p) for p in points.tolist()]
    tree = BVHTree.FromPolygons(verts, [tuple(map(int, f)) for f in tris],
                                all_triangles=True, epsilon=1e-7)
    pairs_found = tree.overlap(tree)
    unique = set()
    for a,b in pairs_found:
        i,j = sorted((int(a),int(b)))
        if i == j: continue
        if any(int(v) in tris[j] for v in tris[i]): continue
        unique.add((i,j))
    return len(unique)

results = {}
all_frame_metrics = []  # EPHEMERAL; only summaries leave the runner
baseline_bvh = None
for frame in all_frames:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    sample, other = geometry()
    assert other == polygons, ("evaluated topology changed",frame)
    n, m, lengths = normals_and_lengths(sample, tris)
    historic = int(np.count_nonzero(np.einsum("ij,ij->i",n0,n)<=0))
    collapse = int(np.count_nonzero(m < .1*m0))
    if frame in sample_frame_set:
        expected = source["skin_geometry_samples"][str(frame)]
        assert historic == expected["inverted_triangles"], ("history changed", frame)
        assert collapse == expected["severe_area_collapse"], ("collapse history changed",frame)
    strain = lengths/l0
    compressed = int(np.count_nonzero(np.any(strain<.75,axis=1)))
    stretched = int(np.count_nonzero(np.any(strain>1.25,axis=1)))
    max_strain = float(np.max(np.abs(strain-1.0)))
    normal = n/np.maximum(m[:,None],1e-18)
    cos = np.einsum("ij,ij->i",normal[pairs[:,0]],normal[pairs[:,1]])
    opposing = int(np.count_nonzero(near_planar & (cos <= -.90)))
    overlaps = bvh_overlap_candidates(sample)
    if baseline_bvh is None: baseline_bvh = overlaps
    all_frame_metrics.append({"frame": frame,
        "rest_normal_reversals": historic, "area_collapses": collapse,
        "compressed_faces": compressed, "stretched_faces": stretched,
        "max_abs_edge_strain": max_strain,
        "opposing_hinges": opposing, "nonadjacent_bvh_pairs": overlaps})
    if frame in sample_frame_set:
        results[str(frame)] = {
        "historical_rest_normal_reversal_count_NOT_PROVEN_INVERSION": historic,
        "severe_area_collapse_count_under_0_1_reference": collapse,
        "faces_any_edge_compressed_under_0_75": compressed,
        "faces_any_edge_stretched_over_1_25": stretched,
        "maximum_absolute_edge_strain_dimensionless": max_strain,
        "opposing_interior_hinges_reference_coplanar": opposing,
        "nonadjacent_bvh_triangle_overlap_candidate_pairs": overlaps,
        "delta_bvh_candidate_pairs_relative_first_frame": overlaps - baseline_bvh,
        "cannot_conclude": "BVH overlap candidates include near contact/coplanar cases; negative count does not certify global absence of surface penetration"
    }
    if frame in sample_frame_set:
        print("R014_REAL_MHR_DIMENSIONLESS_TOPOLOGY_DIFFERENTIAL",
              json.dumps({"motion":args.motion,"frame":frame,
                          "rest_normal_reversals":historic,"area_collapse":collapse,
                          "opposing_hinges":opposing,"nonadjacent_bvh_pairs":overlaps},
                         sort_keys=True),flush=True)

assert len(all_frame_metrics) == source["gait_frames"]
assert args.native_source.stat().st_size > 100000

def summary(key):
    vals = np.asarray([x[key] for x in all_frame_metrics],dtype=np.float64)
    return {"min":float(vals.min()),"p50":float(np.percentile(vals,50)),
            "p95":float(np.percentile(vals,95)),"max":float(vals.max()),
            "mean":float(vals.mean()),"frames_positive":int(np.count_nonzero(vals>0)),
            "worst_frame":int(all_frame_metrics[int(np.argmax(vals))]["frame"])}
field_names = ("rest_normal_reversals","area_collapses","compressed_faces",
               "stretched_faces","max_abs_edge_strain","opposing_hinges","nonadjacent_bvh_pairs")
all_window_summary = {key:summary(key) for key in field_names}
assert all_window_summary["area_collapses"]["frames_positive"] >= 0
# Retain a handful of diagnostic indices, not a full framewise source-derived sequence.
top_strain = sorted(all_frame_metrics,key=lambda x:x["max_abs_edge_strain"],reverse=True)[:5]
top_strain_frame_ids=[int(x["frame"]) for x in top_strain]
print("R014_ALL_CAPTURE_FRAMES_AGGREGATE_HOLD",json.dumps({
    "motion":args.motion,"count":len(all_frame_metrics),
    "severe_area_collapse_frames":all_window_summary["area_collapses"]["frames_positive"],
    "max_strain":all_window_summary["max_abs_edge_strain"]["max"],
    "max_strain_frame":all_window_summary["max_abs_edge_strain"]["worst_frame"],
    "max_BVH_overlap_candidates":all_window_summary["nonadjacent_bvh_pairs"]["max"]},
    sort_keys=True),flush=True)
src_sha = hashlib.sha256(args.native_source.read_bytes()).hexdigest()
doc = {
    "schema":"r014.actual_source_mhr_topology_differential.v1",
    "status":"HOLD_ACTUAL_HUMAN_MOTION_GEOMETRY_AND_SOURCE_RIGHTS",
    "original_motion":args.motion,
    "variant":args.variant,
    "source_mhr_native_sha256_EPHEMERAL_ONLY":src_sha,
    "source_amc_sha256":source["original_source_amc_sha256"],
    "source_asf_sha256":source["original_source_asf_sha256"],
    "source_rig_bones":126,
    "source_mesh_vertices":18439,
    "mesh_triangle_fans":len(tris),
    "mesh_interior_edges":len(pairs),
    "reference_near_planar_interior_edges":count_near_planar,
    "scene_coordinate_units":"RIG_LOCAL_UNCALIBRATED",
    "test_thresholds":{"area_ratio":.1,"edge_compress_ratio":.75,
       "edge_stretch_ratio":1.25,"reference_coplanar_cos_min":.95,
       "opposed_hinge_cos_max":-.90,"bvh_epsilon_rig_local":1e-7},
    "samples":results,
    "full_motion_window_frames_diagnosed":len(all_frame_metrics),
    "full_motion_window_aggregate_metrics_NO_TRACK":all_window_summary,
    "five_worst_edge_strain_frame_indices_NO_COORDINATES":top_strain_frame_ids,
    "what_is_proven":"Actual evaluated source-native MHR geometry, stable topology and exact legacy counts at sampled frames only",
    "what_is_not_proven":[
       "Full window scanned but only aggregate diagnostics retained; no full framewise pose track exported",
       "Reference frame is first sampled captured pose, not independently validated undeformed bind/rest mesh",
       "No self-intersection narrow-phase oracle or physical tissue collision proof",
       "No calibrated centimeters, full kinetic/force/contact or anatomical realism",
       "No full native scene/CMU source/derived frames allowed in downloadable artifact",
       "No hero identity, complete anatomy, facial motion or 1080p cinematic approval"],
    "hold":"All source rights, R014 native anatomy, R015 morphometry, R009 cinematic and Product #2 release/canon HOLD"
}
args.out.mkdir(parents=True,exist_ok=True)
out = args.out/"cmu07_real_mhr_topology_differential_NUMERIC_ONLY.json"
out.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("R014_REAL_MHR_TOPOLOGY_RECEIPT_WRITTEN",out.name,flush=True)
