"""R041 investigate imported-only MPFB geometry against source raw mesh vs evaluated skin.

This reports exact source state and tests the hypothesis that modifier/mask
geometry that should not be visible gets exported. No export acceptance.
"""
import argparse
import hashlib
import json
import math
import os
import sys

import bpy
from mathutils.kdtree import KDTree

THRESHOLD_M = .001


def die(s):
    raise RuntimeError("R041_EXTRA_GEOMETRY_DIAGNOSTIC_HOLD " + s)


def points_raw(obj):
    return [obj.matrix_world @ v.co for v in obj.data.vertices]


def points_evaluated(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    v = obj.evaluated_get(deps)
    mesh = v.to_mesh()
    try:
        return [v.matrix_world @ p.co for p in mesh.vertices]
    finally:
        v.to_mesh_clear()


def tree(points):
    if not points:
        die("empty reference points")
    t = KDTree(len(points))
    for index, pos in enumerate(points):
        t.insert(pos, index)
    t.balance()
    return t


def classify(imported, evaluated, raw):
    ev = tree(evaluated)
    rr = tree(raw)
    extras = []
    matched_raw = 0
    unmatched_raw = 0
    max_direction = None
    for k, pos in enumerate(imported):
        _, source_id, d_eval = ev.find(pos)
        if not math.isfinite(d_eval):
            die("nonfinite evaluated source distance")
        if d_eval <= THRESHOLD_M:
            continue
        near_raw, raw_id, d_raw = rr.find(pos)
        if not math.isfinite(d_raw):
            die("nonfinite raw source distance")
        if d_raw <= THRESHOLD_M:
            matched_raw += 1
        else:
            unmatched_raw += 1
        entry = {
            "import_vertex_id": k,
            "imported_xyz": [float(v) for v in pos],
            "nearest_evaluated_vertex_id": int(source_id),
            "distance_to_evaluated_m": float(d_eval),
            "nearest_raw_vertex_id": int(raw_id),
            "nearest_raw_xyz": [float(v) for v in near_raw],
            "distance_to_raw_m": float(d_raw),
        }
        if max_direction is None or d_eval > max_direction["distance_to_evaluated_m"]:
            max_direction = entry
        if len(extras) < 5:
            extras.append(entry)
    return {
        "source_raw_vertices": len(raw),
        "source_evaluated_vertices": len(evaluated),
        "imported_vertices": len(imported),
        "imported_extra_threshold_m": THRESHOLD_M,
        "imported_points_far_from_evaluated": matched_raw + unmatched_raw,
        "far_points_matching_raw_geometry_1mm": matched_raw,
        "far_points_not_matching_raw_geometry_1mm": unmatched_raw,
        "fraction_far_points_matching_raw": matched_raw / max(1, matched_raw + unmatched_raw),
        "examples": extras,
        "max_evaluated_distance": max_direction,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    root = os.path.abspath(args.out)
    native = bpy.data.objects.get("R036_Official_MPFB_Human")
    if not native:
        die("native source body missing")
    bpy.context.scene.frame_set(1)
    r = points_raw(native)
    e = points_evaluated(native)
    mods = [
        {
            "type": m.type,
            "name": m.name,
            "show_viewport": bool(m.show_viewport),
            "show_render": bool(m.show_render),
            "show_in_editmode": bool(m.show_in_editmode),
            "target_armature": m.object.name if m.type == "ARMATURE" and m.object else None,
        }
        for m in native.modifiers
    ]

    all_w = os.path.join(root, "mpfb-official-anatomy-allweights.glb")
    if not os.path.isfile(all_w):
        die("missing independent all-influences export")
    old = {obj.as_pointer() for obj in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=all_w)
    added = [obj for obj in bpy.data.objects if obj.as_pointer() not in old]
    bodies = [obj for obj in added if obj.type == "MESH" and "R036_Official_MPFB_Human" in obj.name]
    if len(bodies) != 1:
        die("expected exactly one identifiable imported body")
    t = points_evaluated(bodies[0])
    c = classify(t, e, r)
    c.update({
        "schema": "r041.mpfb.raw-vs-evaluated-import.v1",
        "status": "PASS_MEASURE_ONLY_EXPORT_FIDELITY_HOLD",
        "native_modifiers": mods,
        "frame": 1,
        "source_and_import_rights": "PINNED_OFFICIAL_MPFB_PLUS_ORIGINAL_SYNTHETIC",
        "claim_limit": "source-raw nearest-vertex matching does not prove exporter modification cause",
    })
    out = os.path.join(root, "r041-extra-geometry.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2, sort_keys=True)
    print("R041_IMPORTED_EXTRA_GEOMETRY_RECEIPT", json.dumps(c, sort_keys=True))


if __name__ == "__main__":
    main()
