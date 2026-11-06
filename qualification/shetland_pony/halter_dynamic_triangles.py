#!/usr/bin/env python3
"""Native evaluated 48-frame head/halter triangle and pose-diversity audit.

BVH triangle overlap proves candidate surface intersections ONLY, not
closed-volume containment, fur clearance, tack pressure, or veterinary fit.
A rigid head-relative strap does not count as 48 independent deformations.
"""
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

HEAD = "sculpt_equine_brow_bridge_muzzle"
STRAPS = ("halter_cheek_L", "halter_cheek_R", "halter_crownpiece",
          "halter_noseband", "halter_throatlatch")
FRAMES = tuple(range(1, 49))

def mesh_snapshot(obj, depsgraph, to_local):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if mesh is None or len(mesh.vertices) < 3 or len(mesh.polygons) < 1:
            raise ValueError("missing evaluated triangles: " + obj.name)
        transform = to_local @ evaluated.matrix_world
        coords = [tuple(transform @ v.co) for v in mesh.vertices]
        faces = [tuple(p.vertices) for p in mesh.polygons]
        if any(len(poly) < 3 for poly in faces):
            raise ValueError("nontriangulable face: " + obj.name)
        if any(not math.isfinite(t) for xyz in coords for t in xyz):
            raise ValueError("nonfinite mesh: " + obj.name)
        return coords, faces
    finally:
        evaluated.to_mesh_clear()

def fingerprint(coords):
    # 10-micron quantization; never infer veterinary adequacy from equality.
    h = hashlib.sha256()
    h.update(struct.pack("<I", len(coords)))
    for xyz in coords:
        for c in xyz:
            if not math.isfinite(c):
                raise ValueError("nonfinite fingerprint input")
            h.update(struct.pack("<q", round(c * 100000.)))
    return h.hexdigest()

def bvh(points, faces):
    if any(v < 0 or v >= len(points) for f in faces for v in f):
        raise ValueError("mesh has out-of-range polygon index")
    return BVHTree.FromPolygons([Vector(c) for c in points], faces,
                                all_triangles=False, epsilon=0.000001)

def calibrate_overlap():
    # Actual crossing triangle positive control and 10m-separated negative.
    a = bvh([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 2)])
    crossing = bvh([(.25, .25, -.5), (.25, .25, .5), (.75, .25, 0)],
                   [(0, 1, 2)])
    far = bvh([(10, 0, 0), (11, 0, 0), (10, 1, 0)], [(0, 1, 2)])
    if not a.overlap(crossing) or a.overlap(far):
        raise ValueError("native BVH positive/negative calibration failed")

def inspect(source):
    raw = source.read_bytes()
    if not 1024 <= len(raw) <= 300_000_000:
        raise ValueError("bounded Blender source file absent/too large")
    calibrate_overlap()
    bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
    scene = bpy.context.scene
    head = bpy.data.objects.get(HEAD)
    if head is None or head.type != "MESH":
        raise ValueError("actual synthetic head missing")
    if any(bpy.data.objects.get(n) is None or bpy.data.objects[n].type != "MESH"
           for n in STRAPS):
        raise ValueError("missing source-fitted halter triangles")
    frames = {}
    world_pose_states, relative_states = set(), set()
    any_overlap = False
    for frame in FRAMES:
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        head_world = head.evaluated_get(depsgraph).matrix_world.copy()
        world_pose_states.add(fingerprint([
            tuple(head_world @ Vector((0, 0, 0))),
            tuple(head_world @ Vector((1, 0, 0))),
            tuple(head_world @ Vector((0, 1, 0)))]))
        to_head = head_world.inverted_safe()
        headverts, headfaces = mesh_snapshot(head, depsgraph, to_head)
        head_bvh = bvh(headverts, headfaces)
        row, state = {}, [fingerprint(headverts)]
        for strap in STRAPS:
            vertices, faces = mesh_snapshot(bpy.data.objects[strap],
                                             depsgraph, to_head)
            if len(vertices) < 10:
                raise ValueError("halter surface too small: " + strap)
            state.append(fingerprint(vertices))
            pairs = len(head_bvh.overlap(bvh(vertices, faces)))
            any_overlap |= pairs > 0
            row[strap] = {"evaluated_vertices": len(vertices),
                          "evaluated_polygons": len(faces),
                          "bvh_triangle_overlap_pairs": pairs,
                          "triangle_overlap_candidate": bool(pairs)}
        relative_states.add(hashlib.sha256("|".join(state).encode()).hexdigest())
        frames[str(frame)] = row
    return {"schema": "equine.halter.evaluated_48frame_triangle_screen.v1",
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "frames_examined": len(FRAMES), "strap_parts": list(STRAPS),
            "world_head_pose_states": len(world_pose_states),
            "unique_head_relative_mesh_states": len(relative_states),
            "head_relative_dynamics_present": len(relative_states) > 1,
            "any_candidate_triangle_overlap": any_overlap,
            "frames": frames,
            "calibration": "crossing triangle positive / separated triangle negative",
            "limitations": "BVH candidates, not signed solid penetration, containment, fur, tack pressure, anatomical JCS or normative ROM",
            "science_hold": "KEEP", "veterinary_halter_accepted": False,
            "release_or_CPE_admission": False, "model_mutation": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True)
    p.add_argument("--receipt", required=True)
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    out = Path(args.receipt)
    if out.exists():
        raise ValueError("refuse overwrite prior evidence")
    result = inspect(Path(args.blend))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("HALTER_EVALUATED_48F_TRIANGLE_SCREEN_SCIENCE_HOLD",
          result["unique_head_relative_mesh_states"],
          result["any_candidate_triangle_overlap"])

if __name__ == "__main__":
    main()
