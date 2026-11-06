#!/usr/bin/env python3
"""Independent 72-sample 35-joint animation reader, without anatomical PASS.

Consumes the frozen source-original GLB through an independent structural
observer; reports exact time-indexed technical quaternion step magnitudes.
No normatively valid human JCS, loads, collision, photography, or gait claims.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "human_rig_observer"))
from observe import ACTORS, InvalidModel, analyze, load_glb, require, values

ROLES = tuple(f"{joint}_{side}" for side in ("L", "R")
              for joint in ("hip", "knee", "ankle", "shoulder", "elbow",
                            "clavicle", "heel", "ball", "toe")) + ("spine", "head")
FRAMES = 72


def rotation_steps(quaternions):
    require(len(quaternions) == FRAMES, "wrong animated frame count")
    clean = []
    for q in quaternions:
        require(len(q) == 4 and all(math.isfinite(x) for x in q),
                "nonfinite quaternion")
        norm = math.sqrt(sum(x * x for x in q))
        require(0.999 <= norm <= 1.001, "unnormalized quaternion")
        clean.append([x / norm for x in q])
    steps = []
    for a, b in zip(clean, clean[1:]):
        # q and -q are identical orientations. Never flag a sign flip as snap.
        dot = min(1., abs(sum(x * y for x, y in zip(a, b))))
        steps.append(math.degrees(2 * math.acos(dot)))
    require(all(math.isfinite(x) for x in steps), "nonfinite angular step")
    return steps


def inspect(data):
    contract = analyze(data)
    doc, binary = load_glb(data)
    require(len(doc.get("animations", [])) == 1, "missing gait animation")
    nodes = doc["nodes"]
    channel_lookup = {}
    anim = doc["animations"][0]
    for channel in anim["channels"]:
        target = channel["target"]
        node_id = target["node"]
        require(type(node_id) is int and 0 <= node_id < len(nodes),
                "bad animated node")
        key = (nodes[node_id]["name"], target["path"])
        require(key not in channel_lookup, "duplicate animated target")
        channel_lookup[key] = anim["samplers"][channel["sampler"]]
    output = {}
    for actor in ACTORS:
        trajectories = []
        for role in ROLES:
            name = actor + "_" + role
            key = (name, "rotation")
            require(key in channel_lookup, "missing joint animation " + name)
            sampler = channel_lookup[key]
            timeline = values(doc, binary, sampler["input"])
            require(len(timeline) == FRAMES and all(
                abs(t[0] - index / 12.) < 1e-4 for index, t in enumerate(timeline)),
                "wrong source clock")
            quats = values(doc, binary, sampler["output"])
            steps = rotation_steps(quats)
            trajectories.append({"joint": role,
                                 "max_step_deg": round(max(steps), 6),
                                 "sum_step_deg": round(sum(steps), 6),
                                 "large_steps_over_45deg": sum(s > 45 for s in steps)})
        require(len(trajectories) == 20, "incomplete source-controlled joint list")
        output[actor] = {"controlled_rotation_joints": 20,
                         "largest_step_deg": max(t["max_step_deg"] for t in trajectories),
                         "large_steps_over_45deg": sum(t["large_steps_over_45deg"]
                                                        for t in trajectories),
                         "tracks": trajectories}
    return {"schema": "scp.r009_original_rig35_rotation_timeline.v1",
            "source_glb_sha256": hashlib.sha256(data).hexdigest(),
            "independent_structure_sha256": contract["sha256"],
            "actors": output, "samples_per_track": 72, "fps": 12,
            "observed_rotation_tracks": 40,
            "technical_quaternion_continuity": "MEASURED",
            "abrupt_step_threshold": "45deg/frame IS DIAGNOSTIC, NOT BIOLOGICAL",
            "biological_joint_coordinate_system": "UNKNOWN",
            "normative_joint_ROM": "UNKNOWN",
            "skin_surface_contact": "NOT_RUN",
            "surgery_appearance_or_photo_fit": "NOT_RUN",
            "human_motion_accepted": False, "model_mutation": False,
            "release_or_CPE_admission": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--glb", required=True)
    parser.add_argument("--receipt", required=True)
    opts = parser.parse_args()
    blob = Path(opts.glb).read_bytes()
    require(len(blob) <= 64 * 1024 * 1024, "GLB over bounded budget")
    report = inspect(blob)
    Path(opts.receipt).write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print("RIG35_FRAMEWISE_STRUCTURAL_ONLY", report["source_glb_sha256"],
          "tracks", report["observed_rotation_tracks"])


if __name__ == "__main__":
    main()
