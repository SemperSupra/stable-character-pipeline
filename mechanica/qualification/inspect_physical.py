#!/usr/bin/env python3
"""Read-only independent mechanical support/contact and collision broadphase.

This is evidence, NOT a physical dynamics solver:
* World Z is up in the original generator, with glTF coordinate conversion.
* Ground reference is inferred from 4 SUV tire bottoms at initial pose.
* Contact is a bounding-geometry proximity test, not force/stance dynamics.
* Positive AABB overlap means potential collision ONLY (not actual mesh contact).
* All scene assets are pinned original public synthetic models.
"""
import argparse
import hashlib
import json
import math
import pathlib
import statistics
import sys
import traceback

CONTACT_TOL = 0.08
PENETRATION_TOL = 0.08
OVERLAP_TOL = 0.04
SAMPLES = (0, 48, 96, 144, 192)
GLB_SHA256 = "19573f420f8c089842a04ec15664afb35829d587ed87a81c45ee00752c3a1aa8"
GENERATOR_SHA = "ee3f027a2d1e05b9a1b44dd5c5569a19b35dd4d1"

SUPPORTS = {
    "car/left/front-tire": "suv",
    "car/right/front-tire": "suv",
    "car/left/rear-tire": "suv",
    "car/right/rear-tire": "suv",
    "titan/iron-atlas/port/foot": "walker",
    "titan/iron-atlas/starboard/foot": "walker",
}
# Only cross-assembly pairs: intentional connected/ornamental overlap excluded.
# AABB overlap is a broadphase *candidate*, not a narrowphase collision verdict.
PAIRS = (
    ("titan/iron-atlas/port/foot", "titan/iron-atlas/starboard/foot"),
    ("titan/iron-atlas/port/foot", "titan/iron-atlas/starboard/lower-leg"),
    ("titan/iron-atlas/starboard/foot", "titan/iron-atlas/port/lower-leg"),
    ("titan/iron-atlas/port/foot", "titan/iron-atlas/pelvis"),
    ("titan/iron-atlas/starboard/foot", "titan/iron-atlas/pelvis"),
    ("car/left/front-tire", "car/chassis"),
    ("car/right/front-tire", "car/chassis"),
    ("car/left/rear-tire", "car/chassis"),
    ("car/right/rear-tire", "car/chassis"),
    ("space/port/solar-panel", "space/pressure-hull"),
    ("space/starboard/solar-panel", "space/pressure-hull"),
    ("car/tailgate", "car/chassis"),
)

def require(condition, message):
    if not condition:
        raise ValueError(message)

def classify_support(bottom_z, ground_z, tolerance=CONTACT_TOL):
    require(math.isfinite(bottom_z) and math.isfinite(ground_z),
            "SUPPORT_NONFINITE")
    distance = bottom_z - ground_z
    if distance < -tolerance:
        return "BELOW_INFERRED_PLANE", round(distance, 5)
    if distance > tolerance:
        return "ABOVE_INFERRED_PLANE", round(distance, 5)
    return "NEAR_INFERRED_PLANE", round(distance, 5)

def intersection_depth(a, b, tolerance=OVERLAP_TOL):
    """World AABB positive intersection on *all* axes; no triangle claim."""
    assert len(a) == len(b) == 2
    require(all(math.isfinite(float(v)) for bounds in (a,b) for pt in bounds
                for v in pt), "AABB_NONFINITE")
    require(all(a[0][i] <= a[1][i] and b[0][i] <= b[1][i]
                for i in range(3)), "AABB_INVERTED")
    depths = tuple(round(min(a[1][i], b[1][i]) -
                         max(a[0][i], b[0][i]), 5)
                   for i in range(3))
    return depths if all(v > tolerance for v in depths) else None

def self_test():
    near, dist = classify_support(0.02, 0.0)
    require(near == "NEAR_INFERRED_PLANE" and dist == 0.02,
            "CONTACT_POSITIVE_CONTROL_FAILED")
    require(classify_support(0.5, 0)[0] == "ABOVE_INFERRED_PLANE",
            "HOVER_NEGATIVE_CONTROL_FAILED")
    require(classify_support(-0.2, 0)[0] == "BELOW_INFERRED_PLANE",
            "PENETRATION_NEGATIVE_CONTROL_FAILED")
    aa = ((0, 0, 0), (2, 2, 2))
    bb = ((1, 1, 1), (3, 3, 3))
    cc = ((2.1, 0, 0), (4, 2, 2))
    require(intersection_depth(aa, bb) == (1, 1, 1),
            "AABB_POSITIVE_CONTROL_FAILED")
    require(intersection_depth(aa, cc) is None,
            "AABB_SEPARATED_NEGATIVE_CONTROL_FAILED")
    require(intersection_depth(aa, ((2, 0, 0), (4, 2, 2))) is None,
            "AABB_TOUCH_NOT_PENETRATION_CONTROL_FAILED")
    # A spinning circular tire should NOT inherit the excess radius of a
    # rotated cubic bounding box: this synthetic red-team example proves why
    # imported vertices, not obj.bound_box, must define support extremes.
    angle = math.pi / 4
    radius = 0.46
    xs = [radius * math.cos(2 * math.pi * i / 20) for i in range(20)]
    zs = [radius * math.sin(2 * math.pi * i / 20) for i in range(20)]
    actual_min = min(-math.sin(angle) * x + math.cos(angle) * z
                     for x, z in zip(xs, zs))
    rotated_box_min = -radius * (abs(math.sin(angle)) +
                                 abs(math.cos(angle)))
    require(actual_min > rotated_box_min + 0.13,
            "ROTATING_TIRE_AABB_OVERHANG_CONTROL_FAILED")
    try:
        classify_support(float("nan"), 0)
    except ValueError:
        pass
    else:
        raise ValueError("CONTACT_NONFINITE_CONTROL_FAILED")
    print("MECHANICA_CONTACT_SELFTEST=PASS (8 synthetic positive/negative assertions)")

def world_bounds(obj):
    # A transformed local AABB overstates the extremal radius of rotating
    # cylinders. Use actual imported vertices for a tight *world* broadphase
    # (still not triangle intersection / physical penetration).
    vertices = [obj.matrix_world @ v.co for v in obj.data.vertices]
    require(bool(vertices), "EMPTY_MESH:" + obj.name)
    lo = tuple(min(v[k] for v in vertices) for k in range(3))
    hi = tuple(max(v[k] for v in vertices) for k in range(3))
    require(all(math.isfinite(v) for v in (*lo, *hi)),
            "WORLD_BBOX_NONFINITE:" + obj.name)
    return (lo, hi)

def extract(args):
    import bpy
    directory = pathlib.Path(args.preview_dir)
    path = directory / "mechanical_scene.glb"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == GLB_SHA256
    provenance = (directory / "provenance.txt").read_text()
    assert f"source_sha={GENERATOR_SHA}" in provenance
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path.resolve()))
    scene = bpy.context.scene
    meshes = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    mandatory = set(SUPPORTS)
    mandatory.update(p for pair in PAIRS for p in pair)
    require(mandatory <= set(meshes),
            "MISSING_MESH_NAMES:" + ",".join(sorted(mandatory-set(meshes))))
    report = {
        "schema": "mechanica.physical_observation.v1",
        "inspection_status": "PASS_MEASUREMENTS",
        "physical_acceptance": "NOT_ESTABLISHED",
        "source_sha": GENERATOR_SHA,
        "glb_sha256": GLB_SHA256,
        "coordinate_system": "Blender-world Z-up after glTF import",
        "bounds_method": "tight world AABB of actual imported mesh vertices",
        "reference": "Initial SUV four tire AABB bottoms; inferred support plane, no explicit terrain or physics",
        "thresholds_m": {"contact": CONTACT_TOL,
                         "candidate_overlap": OVERLAP_TOL},
        "sampled_frames": list(SAMPLES),
        "support": [],
        "candidate_collisions": [],
        "candidate_counts": {},
        "negative_controls": "PASS",
        "limitations": [
            "Bounding geometry, not triangle narrowphase or swept-volume collision",
            "No wheel/foot load, friction, dynamic balance, or contact forces",
            "Sparse 5-frame samples cannot exclude between-frame defects",
            "No physical terrain, no proof foot should always be planted",
            "Continuous motion and actuator safety not certified",
        ],
    }
    self_test()
    scene.frame_set(SAMPLES[0])
    bpy.context.view_layer.update()
    tire_names = [k for k, kind in SUPPORTS.items() if kind == "suv"]
    tire_zs = [world_bounds(meshes[name])[0][2] for name in tire_names]
    tire_span = max(tire_zs) - min(tire_zs)
    require(tire_span < 0.08, f"BASELINE_WHEEL_HEIGHT_DISAGREEMENT:{tire_zs}")
    ref_z = statistics.median(tire_zs)
    report["inferred_support_z_m"] = round(ref_z, 5)
    report["initial_tire_z_m"] = {n: round(z, 5)
                                   for n, z in zip(tire_names, tire_zs)}
    report["baseline_tire_spread_m"] = round(tire_span, 6)
    hover = []
    penetration = []
    for frame in SAMPLES:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        bboxes = {name: world_bounds(meshes[name]) for name in mandatory}
        for name, kind in SUPPORTS.items():
            status, dz = classify_support(bboxes[name][0][2], ref_z)
            row = {"frame": frame, "object": name, "category": kind,
                   "bottom_z_m": round(bboxes[name][0][2], 5),
                   "delta_to_inferred_support_m": dz,
                   "classification": status}
            report["support"].append(row)
            if status == "BELOW_INFERRED_PLANE":
                penetration.append(row)
            # Start/end are neutral keyed poses, not asserted real stance;
            # report *potential* unsupported walker poses without failing CI.
            if kind == "walker" and frame in (SAMPLES[0], SAMPLES[-1]) and \
                    status == "ABOVE_INFERRED_PLANE":
                hover.append(row)
        pair_count = 0
        for a, b in PAIRS:
            depths = intersection_depth(bboxes[a], bboxes[b])
            if depths is not None:
                pair_count += 1
                report["candidate_collisions"].append({
                    "frame": frame, "object_a": a, "object_b": b,
                    "aabb_intersection_depth_m": depths,
                    "narrowphase_verified": False,
                })
        report["candidate_counts"][str(frame)] = pair_count
    report["neutral_pose_walker_hover_observations"] = hover
    report["below_plane_observations"] = penetration
    report["potential_findings"] = (
        ["WALKER_NEUTRAL_POSE_GAP"] if hover else []
    ) + (["GEOMETRY_BELOW_REFERENCE"] if penetration else []) + (
        ["AABB_BROADPHASE_CANDIDATES"]
        if report["candidate_collisions"] else []
    )
    # PASS_MEASUREMENTS is intentionally NOT a physics/animation acceptance gate.
    return report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preview-dir")
    parser.add_argument("--output")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:]
                             if "--" in sys.argv else sys.argv[1:])
    if args.self_test:
        self_test()
        return
    require(args.preview_dir and args.output, "PREVIEW_AND_OUTPUT_REQUIRED")
    try:
        result = extract(args)
    except Exception as exc:
        result = {"schema": "mechanica.physical_observation.v1",
                  "inspection_status": "FAILED_MEASUREMENTS",
                  "first_failure": str(exc),
                  "traceback": traceback.format_exc()[-5000:]}
    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("MECHANICA_PHYSICAL_REPORT=" + json.dumps(result, sort_keys=True))
    if result["inspection_status"] != "PASS_MEASUREMENTS":
        sys.exit(1)

if __name__ == "__main__":
    main()
