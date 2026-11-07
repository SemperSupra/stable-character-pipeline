#!/usr/bin/env python3
"""R009 unmodified GLB ankle-world-position / shoe-height phase evidence.

All source assets are user-owned synthetic or admitted CC0 body geometry.
World Y is up. Diagnostic root lift is never applied to the GLB.
Requires actual owner-retained GLB and preexisting source-bound sole witness.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from costume_garment_v1 import _unpack_glb
from observe_makehuman35_motion_v0 import parents_of, worlds, frame_poses

SCHEMA = "scp.r009.ankle_sole_phase_witness.v1"
SOURCE_SHA256 = "b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748"
ACTORS = ("AsterOriginal", "JuniperOriginal")
SIDES = ("L", "R")


def generate(raw_glb: bytes, raw_shoe_support: bytes, raw_correspondence: bytes) -> dict:
    if hashlib.sha256(raw_glb).hexdigest() != SOURCE_SHA256:
        raise ValueError("SOURCE_HASH_MISMATCH")
    from sole_phase_root_feasibility_v1 import evaluate as validate_prior
    correspondence = json.loads(raw_correspondence)
    validate_prior(correspondence)  # raises if source, frame, actor, bilateral stats forged
    shoe = json.loads(raw_shoe_support)
    if (shoe.get("source_sha256") != SOURCE_SHA256
            or shoe.get("frames_evaluated") != 72 or shoe.get("coordinate_up") != "Y"
            or shoe.get("schema") != "scp.r009.shoe_ground_phase_cpu72.v1"
            or any(shoe.get(flag) is not False for flag in ("root_shift_applied", "native_blender_evaluated", "gait_accepted", "release_approved"))
            or set(shoe.get("actors", {})) != set(ACTORS)):
        raise ValueError("SHOE_SUPPORT_PROVENANCE")

    doc, binbuf = _unpack_glb(raw_glb)
    nodes = doc["nodes"]
    parents = parents_of(nodes)
    by_name = {node.get("name"): i for i, node in enumerate(nodes)}
    if len(by_name) != len(nodes):
        raise ValueError("DUPLICATE_NODE_NAMES")
    joint_ids = {
        actor: {side: by_name[f"{actor}_ankle_{side}"] for side in SIDES}
        for actor in ACTORS
    }
    position = {actor: {side: [] for side in SIDES} for actor in ACTORS}
    pose_count = 0
    for pose in frame_poses(doc, binbuf):
        pose_count += 1
        world = worlds(nodes, parents, pose)
        for actor in ACTORS:
            for side in SIDES:
                vector = world[joint_ids[actor][side]][:3, 3]
                if not all(math.isfinite(float(x)) and abs(x) < 20 for x in vector):
                    raise ValueError("ANKLE_NONFINITE_OR_OUT_OF_SCENE")
                position[actor][side].append([float(x) for x in vector])
    if pose_count != 72:
        raise ValueError("EXPECTED_72_POSES")

    actors = {}
    for actor in ACTORS:
        rows = shoe["actors"][actor]
        if len(rows) != 144:
            raise ValueError("SHOE_SUPPORT_ROWS")
        shoe_y = {side: [None] * 72 for side in SIDES}
        for r in rows:
            f, side = r.get("frame"), r.get("side")
            if type(f) is not int or f not in range(72) or side not in SIDES:
                raise ValueError("SHOE_SAMPLE_FRAME_SIDE")
            if shoe_y[side][f] is not None:
                raise ValueError("DUPLICATE_SHOE_SAMPLE")
            y = r.get("min_y_m")
            if type(y) not in (int, float) or not math.isfinite(y) or abs(y) > 2:
                raise ValueError("INVALID_SHOE_HEIGHT")
            shoe_y[side][f] = float(y)
        if any(y is None for side in SIDES for y in shoe_y[side]):
            raise ValueError("INCOMPLETE_SHOE_SAMPLES")
        lift = correspondence["actors"][actor]["required_root_y_clearance_m"]
        # Verify that the independent root-lift witness matches the source shoe minima.
        for f in range(72):
            if abs(lift[f] + min(shoe_y[side][f] for side in SIDES)) > 1e-7:
                raise ValueError("INDEPENDENT_FLOOR_CLEARANCE_MISMATCH")
        actors[actor] = {
            "ankle_world_xyz_m": position[actor],
            "shoe_min_y_m": shoe_y,
            "diagnostic_root_lift_m": lift,
        }
    return {
        "schema": SCHEMA,
        "source_sha256": SOURCE_SHA256,
        "sole_correspondence_sha256": hashlib.sha256(raw_correspondence).hexdigest(),
        "shoe_support_sha256": hashlib.sha256(raw_shoe_support).hexdigest(),
        "coordinate_up": "Y", "frames": 72, "actors": actors,
        "root_shift_applied": False, "foot_ik_applied": False,
        "native_blender_evaluated": False, "gait_accepted": False,
        "release_approved": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True, type=Path)
    ap.add_argument("--sole", required=True, type=Path)
    ap.add_argument("--shoe-support", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    if args.out.exists() or args.out.resolve() in (args.glb.resolve(), args.sole.resolve(), args.shoe_support.resolve()):
        raise ValueError("NO_OVERWRITE")
    out = generate(args.glb.read_bytes(), args.shoe_support.read_bytes(), args.sole.read_bytes())
    args.out.write_text(json.dumps(out, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"schema": SCHEMA, "sha256": hashlib.sha256(args.out.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
