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
# RAW, undeformed source mesh: independent reference proxy, NOT certified
# true anatomical bind pose (armature rest transform/shape-key state unknown).
# All output is nonreconstructive numerical QA; never export coordinates.
raw_faces=[tuple(int(k) for k in p.vertices) for p in body.data.polygons]
assert raw_faces == polygons, "unequal original and evaluated face topology"
inv = rig.matrix_world.inverted_safe()
raw_reference=np.asarray([list(inv @ (body.matrix_world @ v.co))
     for v in body.data.vertices],dtype=np.float64)
assert raw_reference.shape==rest.shape and np.isfinite(raw_reference).all()
raw_n,raw_m,raw_l=normals_and_lengths(raw_reference,tris)
raw_valid_area=raw_m>1e-11
raw_valid_edges=raw_l>1e-9
raw_degenerate_faces=int(np.count_nonzero(~raw_valid_area))
raw_degenerate_edges=int(np.count_nonzero(~raw_valid_edges))
n0, m0, l0 = normals_and_lengths(rest, tris)
# Hereafter raw-to-first compares actual evaluated captured frame 1 to
# the undeformed raw source mesh, not to a fabricated SI-scale human.
raw_first_area_ratio=np.divide(m0,raw_m,out=np.ones_like(raw_m),where=raw_valid_area)
raw_first_edge_ratio=np.divide(l0,raw_l,out=np.ones_like(raw_l),where=raw_valid_edges)
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

# Weight group labels are original MHR source controls, NOT validated human
# anatomy. Aggregate only approximate source group names, never face IDs,
# per-frame mesh coordinates, original CMU tracks, or derived images.
source_group_names = {g.index:g.name for g in body.vertex_groups}
source_rig_bones = {b.name for b in rig.data.bones}
dominant_face_group_cache = {}
def dominant_face_group(index):
    index=int(index)
    if index in dominant_face_group_cache:
        return dominant_face_group_cache[index]
    weights=collections.defaultdict(float)
    for vertex_id in tris[index]:
        for vertex_weight in body.data.vertices[int(vertex_id)].groups:
            group=source_group_names.get(vertex_weight.group,"")
            if group in source_rig_bones:
                weights[group]+=float(vertex_weight.weight)
    group=max(weights,key=weights.get) if weights else "UNBOUND_MESH"
    dominant_face_group_cache[index]=group
    return group

def group_category(name):
    low=name.lower()
    if any(k in low for k in ("foot","ball","toe","heel","tarsal","ankle","tibia",
                              "lowleg","upleg","thigh","femur","calf","knee","hip")):
        return "LOWER_BODY_OR_LEG"
    if any(k in low for k in ("arm","hand","finger","thumb","wrist","elbow","shoulder")):
        return "UPPER_LIMB_HAND"
    if any(k in low for k in ("pelvis","root","spine","torso","chest","abdomen")):
        return "PELVIS_TORSO"
    if any(k in low for k in ("head","face","jaw","eye","neck","tongue")):
        return "HEAD_FACE_NECK"
    return "OTHER_OR_UNKNOWN"
anomaly_group_counts=collections.defaultdict(collections.Counter)
anomaly_category_counts=collections.defaultdict(collections.Counter)
def accumulate_group(kind, face_indices):
    for fid in face_indices:
        group=dominant_face_group(fid)
        anomaly_group_counts[kind][group]+=1
        anomaly_category_counts[kind][group_category(group)]+=1

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
    collapsed_first_mask=(m < .1*m0)
    collapsed_raw_mask=raw_valid_area & (m < .1*raw_m)
    collapsed_raw_count=int(np.count_nonzero(collapsed_raw_mask))
    raw_edge_ratio=np.divide(lengths,raw_l,out=np.ones_like(lengths),where=raw_valid_edges)
    raw_strain_max=float(np.max(np.abs(raw_edge_ratio[raw_valid_edges]-1))) if np.any(raw_valid_edges) else 0.0
    collapse_both_count=int(np.count_nonzero(collapsed_first_mask&collapsed_raw_mask))
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
    collapsed_ids=np.flatnonzero(m < .1*m0)
    compressed_ids=np.flatnonzero(np.any(strain<.75,axis=1))
    stretched_ids=np.flatnonzero(np.any(strain>1.25,axis=1))
    opposed_pair_ids=np.flatnonzero(near_planar & (cos<=-.90))
    accumulate_group("area_collapse",collapsed_ids)
    accumulate_group("edge_compressed",compressed_ids)
    accumulate_group("edge_stretched",stretched_ids)
    if len(opposed_pair_ids):
        accumulate_group("opposing_hinge_faces",np.unique(pairs[opposed_pair_ids].ravel()))
    all_frame_metrics.append({"frame": frame,
        "rest_normal_reversals": historic, "area_collapses": collapse,
        "compressed_faces": compressed, "stretched_faces": stretched,
        "max_abs_edge_strain": max_strain,
        "collapsed_faces_vs_raw_reference": collapsed_raw_count,
        "collapsed_faces_vs_both_references": collapse_both_count,
        "max_abs_edge_strain_vs_raw_reference": raw_strain_max,
        "opposing_hinges": opposing, "nonadjacent_bvh_pairs": overlaps})
    if frame in sample_frame_set:
        results[str(frame)] = {
        "historical_rest_normal_reversal_count_NOT_PROVEN_INVERSION": historic,
        "severe_area_collapse_count_under_0_1_reference": collapse,
        "collapsed_area_under_0_1_raw_source_reference": collapsed_raw_count,
        "collapsed_under_0_1_both_reference_proxies": collapse_both_count,
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
               "stretched_faces","max_abs_edge_strain","collapsed_faces_vs_raw_reference",
               "collapsed_faces_vs_both_references","max_abs_edge_strain_vs_raw_reference",
               "opposing_hinges","nonadjacent_bvh_pairs")
all_window_summary = {key:summary(key) for key in field_names}
source_weight_group_summary={
  key:{"dominant_source_bone_groups_face_frame_occurrences":counter.most_common(12),
       "approximate_source_categories_face_frame_occurrences":
           dict(anomaly_category_counts[key])}
  for key,counter in anomaly_group_counts.items()
}
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
    "raw_undeformed_source_reference_status":"RAW_BODY_DATA_PROXY_NOT_CERTIFIED_ARMATURE_BIND_POSE",
    "raw_source_face_degenerate_count":raw_degenerate_faces,
    "raw_source_edge_degenerate_count":raw_degenerate_edges,
    "frame1_evaluated_vs_raw_reference_area_ratio_p05_p50_p95":
       [float(v) for v in np.percentile(raw_first_area_ratio[raw_valid_area],[5,50,95])]
       if np.any(raw_valid_area) else [],
    "frame1_evaluated_vs_raw_reference_max_abs_edge_ratio_delta":
       float(np.max(np.abs(raw_first_edge_ratio[raw_valid_edges]-1)))
       if np.any(raw_valid_edges) else None,
    "scene_coordinate_units":"RIG_LOCAL_UNCALIBRATED",
    "test_thresholds":{"area_ratio":.1,"edge_compress_ratio":.75,
       "edge_stretch_ratio":1.25,"reference_coplanar_cos_min":.95,
       "opposed_hinge_cos_max":-.90,"bvh_epsilon_rig_local":1e-7},
    "samples":results,
    "full_motion_window_frames_diagnosed":len(all_frame_metrics),
    "full_motion_window_aggregate_metrics_NO_TRACK":all_window_summary,
    "source_weight_group_attribution_DIAGNOSTIC_NOT_ANATOMY":source_weight_group_summary,
    "five_worst_edge_strain_frame_indices_NO_COORDINATES":top_strain_frame_ids,
    "what_is_proven":"Actual evaluated source-native MHR geometry, stable topology and exact legacy counts at sampled frames only",
    "what_is_not_proven":[
       "Full window scanned but only aggregate diagnostics retained; no full framewise pose track exported",
       "Reference frame is first sampled captured pose, not independently validated undeformed bind/rest mesh",
       "Raw mesh body.data vertices are an undeformed source reference proxy, not a validated armature rest/bind configuration",
       "Two reference proxies quantify deformation sensitivity but cannot establish clinical tissue injury or corrective weights",
       "Dominant original MHR skin weight group is approximate region evidence, not true anatomical landmark measurement",
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
