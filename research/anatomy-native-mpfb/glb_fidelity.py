"""R039: actual GLB reimport vs saved MPFB master deformation measurements.
Blender Python only. No pass on game/film parity from a structural GLB export.
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


def die(message):
    raise RuntimeError("R039_GLTF_FIDELITY_HOLD " + message)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def evaluated_points(obj):
    deps = bpy.context.evaluated_depsgraph_get()
    observed = obj.evaluated_get(deps)
    mesh = observed.to_mesh()
    try:
        transform = observed.matrix_world
        return [transform @ v.co for v in mesh.vertices]
    finally:
        observed.to_mesh_clear()


def metrics(reference, candidate):
    if not reference or not candidate:
        die("empty evaluated surface")

    def nearest(a, b):
        tree = KDTree(len(b))
        for index, p in enumerate(b):
            tree.insert(p, index)
        tree.balance()
        distances = []
        for p in a:
            _, _, d = tree.find(p)
            if not math.isfinite(d):
                die("nonfinite GLB surface deviation")
            distances.append(float(d))
        return distances

    # Bidirectional nearest-vertex residuals are a diagnostic, not a unique
    # vertex/topology correspondence or full surface Hausdorff guarantee.
    deviations = nearest(reference, candidate) + nearest(candidate, reference)
    deviations.sort()
    return {
        "max_m": deviations[-1],
        "p95_m": deviations[min(len(deviations) - 1, math.ceil(.95 * len(deviations)) - 1)],
        "mean_m": sum(deviations) / len(deviations),
        "rms_m": math.sqrt(sum(d * d for d in deviations) / len(deviations)),
        "samples_bidirectional": len(deviations),
    }


def moved(a, b):
    return len(a) == len(b) and any((x - y).length > 1e-7 for x, y in zip(a, b))


def sample_native():
    body = bpy.data.objects.get("R036_Official_MPFB_Human")
    rig = bpy.data.objects.get("R036_Official_MPFB_Rig")
    if body is None or rig is None or body.type != "MESH" or rig.type != "ARMATURE":
        die("original master body and official rig missing")
    samples = {}
    scene = bpy.context.scene
    for frame in FRAMES:
        scene.frame_set(frame)
        samples[frame] = evaluated_points(body)
    if not moved(samples[1], samples[24]):
        die("original native character did not move")
    return samples, rig, body


def import_measure(path, reference):
    before = {obj.as_pointer() for obj in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(path))
    added = [obj for obj in bpy.data.objects if obj.as_pointer() not in before]
    bodies = [obj for obj in added if obj.type == "MESH" and "R036_Official_MPFB_Human" in obj.name]
    rigs = [obj for obj in added if obj.type == "ARMATURE"]
    if len(bodies) != 1 or not rigs:
        die("reimport did not preserve a distinguishable body mesh and armature")
    body = bodies[0]
    if not any(mod.type == "ARMATURE" and mod.object in rigs for mod in body.modifiers):
        die("reimported skin no longer binds to an imported armature")
    scene = bpy.context.scene
    pose = {}
    report = {"imported_vertices": None, "imported_bones": sum(len(r.data.bones) for r in rigs), "frames": {}}
    for frame in FRAMES:
        scene.frame_set(frame)
        points = evaluated_points(body)
        if report["imported_vertices"] is None:
            report["imported_vertices"] = len(points)
        report["frames"][str(frame)] = metrics(reference[frame], points)
        if report["frames"][str(frame)]["max_m"] > 5.0:
            die("reimport spatial deviation >5m; likely transform/frame/units error")
        pose[frame] = points
    report["animated_on_reimport"] = moved(pose[1], pose[24])
    if not report["animated_on_reimport"]:
        die("reimport lost active animated character deformation")
    # Cleanup affects only disposable reimported objects; source is not saved.
    for obj in added:
        bpy.data.objects.remove(obj, do_unlink=True)
    return report


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    root = os.path.abspath(args.out)
    original = os.path.join(root, "mpfb-official-anatomy.blend")
    four = os.path.join(root, "mpfb-official-anatomy.glb")
    allweights = os.path.join(root, "mpfb-official-anatomy-allweights.glb")
    if not all(os.path.isfile(p) for p in (original, four, allweights)):
        die("missing native master or paired source-created exports")
    reference, rig, body = sample_native()
    observations = {
        "status": "MEASUREMENT_ONLY_NO_FIDELITY_ACCEPTANCE",
        "native_master_sha256": sha256(original),
        "body_vertices_native_evaluated": len(reference[1]),
        "bones_native": len(rig.data.bones),
        "frames": list(FRAMES),
        "units": "Blender world meters (must independently validate scene unit conventions)",
        "metric": "bidirectional nearest evaluated vertices, not indexed correspondence or full triangle surface",
        "acceptance": "HOLD_GAME_FILM_EXPORT",
        "arms": {},
    }
    for label, file in (("gltf_four_influences", four), ("gltf_all_influences", allweights)):
        result = import_measure(file, reference)
        result["glb_sha256"] = sha256(file)
        observations["arms"][label] = result
    with open(os.path.join(root, "glb-import-differential.json"), "w", encoding="utf-8") as stream:
        json.dump(observations, stream, sort_keys=True, indent=2)
    print("R039_GLTF_IMPORTED_DEFORMATION_RECEIPT", json.dumps(observations, sort_keys=True))


if __name__ == "__main__":
    main()
