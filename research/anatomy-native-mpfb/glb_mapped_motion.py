"""R040 independent source-to-GLB geometric and skin motion diagnostic.

No assets are uploaded, no game/film export acceptance is asserted.
Nearest-rest correspondence is a hypothesis, not an indexed topology mapping.
"""
import argparse
import hashlib
import json
import math
import os
import sys

import bpy
from mathutils.kdtree import KDTree

FRAMES = (1, 12, 24)
CLOSE_M = 0.001


def fail(message):
    raise RuntimeError("R040_MAPPED_MOTION_HOLD " + message)


def world_mesh(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    ob = obj.evaluated_get(deps)
    mesh = ob.to_mesh()
    try:
        return [ob.matrix_world @ v.co for v in mesh.vertices]
    finally:
        ob.to_mesh_clear()


def summary(values):
    if not values:
        return {"count": 0, "status": "EMPTY"}
    x = sorted(values)
    n = len(x)
    return {
        "count": n,
        "mean_m": float(sum(x) / n),
        "p95_m": float(x[max(0, math.ceil(n * .95) - 1)]),
        "max_m": float(x[-1]),
    }


def positions(obj):
    return {f: _frame(obj, f) for f in FRAMES}


def _frame(obj, f):
    bpy.context.scene.frame_set(f)
    return world_mesh(obj)


def kd(points):
    if not points:
        fail("empty source point set")
    tree = KDTree(len(points))
    for i, p in enumerate(points):
        tree.insert(p, i)
    tree.balance()
    return tree


def region(z, min_z, max_z):
    frac = (z - min_z) / max(1e-9, max_z - min_z)
    if frac < .24: return "feet_lower_leg"
    if frac < .53: return "upper_leg_pelvis"
    if frac < .79: return "torso_arms"
    return "neck_head"


def spatial_diagnostics(source, imported):
    tree = kd(imported)
    low_z = min(p.z for p in source)
    high_z = max(p.z for p in source)
    worst = None
    per_region = {}
    for i, p in enumerate(source):
        neighbor, index, distance = tree.find(p)
        if not math.isfinite(distance):
            fail("nonfinite spatial distance")
        label = region(p.z, low_z, high_z)
        per_region.setdefault(label, []).append(float(distance))
        if worst is None or distance > worst["distance_m"]:
            worst = {
                "direction": "native_to_import",
                "source_vertex_index": i,
                "nearest_import_vertex_index": int(index),
                "region_approximation": label,
                "native_world_xyz": [float(v) for v in p],
                "nearest_import_world_xyz": [float(v) for v in neighbor],
                "distance_m": float(distance),
            }
    reverse_tree = kd(source)
    worst_back = None
    for i, p in enumerate(imported):
        neighbor, idx, dist = reverse_tree.find(p)
        if not math.isfinite(dist):
            fail("nonfinite reverse spatial distance")
        if worst_back is None or dist > worst_back["distance_m"]:
            worst_back = {
                "direction": "import_to_native",
                "import_vertex_index": i,
                "nearest_native_vertex_index": int(idx),
                "import_world_xyz": [float(v) for v in p],
                "nearest_native_world_xyz": [float(v) for v in neighbor],
                "distance_m": float(dist),
            }
    return {
        "native_to_import_max": worst,
        "import_to_native_max": worst_back,
        "native_region_nearest_residuals_m": {k: summary(v) for k, v in per_region.items()},
    }


def match_and_motion(source, target):
    # Freeze nearest mapping at *rest* once, then compare displacement vectors
    # of corresponding indexed vertices at the same future frame.
    # This is diagnostic only: rest-position collisions and split seams are
    # explicitly not proof of a source-authoritative vertex identity map.
    rest_s = source[1]
    rest_t = target[1]
    tree = kd(rest_s)
    matches = []
    distances = []
    identities = {}
    for i, p in enumerate(rest_t):
        _, j, d = tree.find(p)
        if not math.isfinite(d):
            fail("nonfinite rest match")
        distances.append(float(d))
        if d <= CLOSE_M:
            matches.append((i, j))
            identities[j] = identities.get(j, 0) + 1

    out = {
        "rest_match_tolerance_m": CLOSE_M,
        "target_vertices": len(rest_t),
        "source_vertices": len(rest_s),
        "within_tolerance_count": len(matches),
        "within_tolerance_fraction": len(matches) / len(rest_t),
        "unique_source_vertices_matched": len(identities),
        "multiply_matched_source_vertices": sum(1 for n in identities.values() if n > 1),
        "rest_nearest_m": summary(distances),
        "per_frame_displacement_delta_m": {},
        "decision": "DIAGNOSTIC_MAPPING_NOT_AUTHORITATIVE",
    }
    for frame in FRAMES[1:]:
        if len(source[frame]) != len(rest_s) or len(target[frame]) != len(rest_t):
            fail("unexpected topology cardinality across time")
        errs = []
        for i, j in matches:
            src_move = source[frame][j] - rest_s[j]
            dst_move = target[frame][i] - rest_t[i]
            errs.append(float((dst_move - src_move).length))
        out["per_frame_displacement_delta_m"][str(frame)] = summary(errs)
    return out


def take_import(path):
    before = {o.as_pointer() for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o.as_pointer() not in before]
    bodies = [o for o in new if o.type == "MESH" and "R036_Official_MPFB_Human" in o.name]
    arms = [o for o in new if o.type == "ARMATURE"]
    if len(bodies) != 1 or not arms:
        fail("GLB source body or armature not distinguishable")
    if not any(m.type == "ARMATURE" and m.object in arms for m in bodies[0].modifiers):
        fail("import did not bind a usable skin")
    samples = positions(bodies[0])
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    return samples


def paired_import_difference(four, all_w):
    out = {"topology_cardinality_equal": True, "per_frame_index_paired_m": {}}
    for f in FRAMES:
        a, b = four[f], all_w[f]
        if len(a) != len(b):
            out["topology_cardinality_equal"] = False
            out["per_frame_index_paired_m"][str(f)] = {"status": "CARDINALITY_MISMATCH"}
            continue
        vals = [float((p - q).length) for p, q in zip(a, b)]
        out["per_frame_index_paired_m"][str(f)] = summary(vals)
    aligned = (
        out["topology_cardinality_equal"]
        and out["per_frame_index_paired_m"]["1"]["max_m"] <= .00001
    )
    out["rest_index_alignment_10um"] = aligned
    out["decision"] = (
        "INDEX_PAIRED_IMPORT_DIAGNOSTIC_NOT_ENGINE_PROOF" if aligned
        else "HOLD_IMPORT_INDEX_TOPOLOGY_CORRESPONDENCE"
    )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    root = os.path.abspath(args.out)
    original = os.path.join(root, "mpfb-official-anatomy.blend")
    fours = os.path.join(root, "mpfb-official-anatomy.glb")
    alls = os.path.join(root, "mpfb-official-anatomy-allweights.glb")
    for p in (original, fours, alls):
        if not os.path.isfile(p):
            fail("required source/export artifact missing")

    native = bpy.data.objects.get("R036_Official_MPFB_Human")
    if not native or native.type != "MESH":
        fail("original saved native MPFB body is unavailable")
    reference = positions(native)
    four = take_import(fours)
    all_w = take_import(alls)

    output = {
        "status": "DIAGNOSTIC_ONLY_EXPORT_HOLD",
        "schema": "r040.mpfb.imported-motion.v1",
        "source": "Official pinned MPFB, synthetic original organ proxies",
        "frames": list(FRAMES),
        "units": "Blender world coordinate meters (source unit scale unqualified)",
        "source_vertices": len(reference[1]),
        "four_vertices": len(four[1]),
        "all_vertices": len(all_w[1]),
        "sha256": {
            "native": _sha(original),
            "four": _sha(fours),
            "all": _sha(alls),
        },
        "four": {
            "spatial_frame_1": spatial_diagnostics(reference[1], four[1]),
            "rest_correspondence_motion": match_and_motion(reference, four),
        },
        "all": {
            "spatial_frame_1": spatial_diagnostics(reference[1], all_w[1]),
            "rest_correspondence_motion": match_and_motion(reference, all_w),
        },
        "four_vs_all": paired_import_difference(four, all_w),
        "rights": "PUBLIC_SOURCE_PINNED_NO_PROTECTED_MEDIA",
        "acceptance": "HOLD_NOT_NATIVE_MORPH_OR_GAME_ENGINE_FIDELITY",
    }
    dest = os.path.join(root, "r040-imported-motion-diagnostic.json")
    with open(dest, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
    print("R040_MAPPED_MOTION_DIAGNOSTIC", json.dumps(output, sort_keys=True))


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for buf in iter(lambda: f.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


if __name__ == "__main__":
    main()
