#!/usr/bin/env python3
"""Read-only contact-label identifiability falsifier for original jumping jacks.

Research-only graph bound. A moving ankle cannot remain planted across both
endpoints of the same frame interval. This script NEVER rewrites original
contacts, frames, mesh, or media, and a minimum relabel count is NOT a
biomechanical correction or permission to relabel without independent physics.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

CASE = "female_jumping_jacks_sandals"
BATCH = "exercise_pose"
SCHEMA = "scp.visualqa.jacks-contact-cover.v1"
MAX_BYTES = 5_000_000
MAX_STANCE_SPEED_M_S = 0.025

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def load_original(root: Path):
    folder = root / BATCH
    manifest_raw = (folder / "manifest.json").read_bytes()
    if len(manifest_raw) > MAX_BYTES:
        raise ValueError("MANIFEST_TOO_LARGE")
    manifest = json.loads(manifest_raw)
    if (manifest.get("schema") != "scp.expanded-original-3d-motion-corpus.v1"
        or manifest.get("batch") != BATCH
        or manifest.get("rights") != "CC0-1.0 for original generated files"
        or manifest.get("fps") != 20 or manifest.get("frames") != 40):
        raise ValueError("SOURCE_MANIFEST_AUTHORITY_MISMATCH")
    items = [x for x in manifest.get("cases", []) if x.get("case") == CASE]
    if len(items) != 1:
        raise ValueError("MISSING_OR_DUPLICATE_ORIGINAL_CASE")
    item = items[0]
    if (item.get("spec", {}).get("motion") != "jumping_jacks"
        or item.get("spec", {}).get("footwear") != "sandals"):
        raise ValueError("ORIGINAL_CASE_SPEC_MISMATCH")
    gt = item["ground_truth"]
    if gt["file"] != CASE + "_ground_truth.json":
        raise ValueError("LABEL_FILENAME_MISMATCH")
    raw = (folder / gt["file"]).read_bytes()
    if len(raw) > MAX_BYTES or sha(raw) != gt["sha256"]:
        raise ValueError("ORIGINAL_GROUND_TRUTH_HASH_MISMATCH")
    for obj in [item["model"], *item["videos"]]:
        filename = obj["file"]
        if filename not in [CASE + ".glb", CASE + "_side.mp4"]:
            raise ValueError("UNEXPECTED_CASE_MEDIA")
        if sha((folder / filename).read_bytes()) != obj["sha256"]:
            raise ValueError("ORIGINAL_MEDIA_HASH_MISMATCH")
    gt_json = json.loads(raw)
    frames = gt_json.get("frames")
    if (gt_json.get("schema") != "scp.expanded-original-3d-motion-labels.v1"
        or gt_json.get("case") != CASE or gt_json.get("fps") != 20
        or not isinstance(frames, list) or len(frames) != 40):
        raise ValueError("ORIGINAL_FRAME_CLOCK_MISMATCH")
    for i, frame in enumerate(frames):
        if frame.get("frame") != i:
            raise ValueError("FRAME_INDEX_DRIFT")
        for side in ("left", "right"):
            if type(frame["contact"][side]) is not bool:
                raise ValueError("BAD_CONTACT_BOOLEAN")
            p = frame["joints"][side + "_ankle"]
            if len(p) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in p):
                raise ValueError("INVALID_WORLD_ANKLE")
    return frames, sha(raw), sha(manifest_raw)

def sliding_edges(frames: list[dict], side: str, fps: int = 20,
                  max_stance_speed: float = MAX_STANCE_SPEED_M_S):
    if len(frames) < 2 or fps <= 0 or not math.isfinite(max_stance_speed) or max_stance_speed < 0:
        raise ValueError("INVALID_CONTACT_WINDOW")
    out = []
    for i in range(1, len(frames)):
        a, b = frames[i-1], frames[i]
        if type(a["contact"][side]) is not bool or type(b["contact"][side]) is not bool:
            raise ValueError("BAD_CONTACT_BOOLEAN")
        p, q = a["joints"][side + "_ankle"], b["joints"][side + "_ankle"]
        if any(len(x) != 3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in x) for x in (p,q)):
            raise ValueError("INVALID_WORLD_ANKLE")
        if a["contact"][side] and b["contact"][side]:
            speed = math.dist(p, q) * fps
            if speed > max_stance_speed:
                out.append(i-1)
    return out

def minimum_cover_dp(edge_starts: list[int], frame_count: int):
    """Exact minimum vertex cover on the frame-adjacency path, with witness."""
    if frame_count < 2 or any(type(i) is not int or i < 0 or i >= frame_count-1 for i in edge_starts):
        raise ValueError("INVALID_EDGES")
    edge_set = set(edge_starts)
    states = {0: (0, ()), 1: (1, (0,))}
    for i in range(1, frame_count):
        next_states = {}
        for selected in (0, 1):
            candidates = []
            for last, (cost, witness) in states.items():
                if i-1 in edge_set and last == 0 and selected == 0:
                    continue
                candidates.append((cost + selected, witness + ((i,) if selected else ())))
            next_states[selected] = min(candidates)
        states = next_states
    count, witness = min(states.values())
    if any(i not in witness and i+1 not in witness for i in edge_set):
        raise AssertionError("COVER_WITNESS_DOES_NOT_HIT_EDGE")
    return count, list(witness)

def maximum_matching_path(edge_starts: list[int], frame_count: int):
    """Independent greedy maximum matching on an ordered path (König bound)."""
    if frame_count < 2 or any(type(i) is not int or i < 0 or i >= frame_count-1 for i in edge_starts):
        raise ValueError("INVALID_EDGES")
    selected, occupied_until = [], -1
    for i in sorted(set(edge_starts)):
        if i > occupied_until:
            selected.append(i)
            occupied_until = i+1
    return len(selected), selected

def evaluate(root: Path, method: str):
    if method not in ("dp", "matching"):
        raise ValueError("UNSUPPORTED_INDEPENDENT_ORACLE")
    frames, labels_sha, manifest_sha = load_original(root)
    records = {}
    for side in ("left", "right"):
        edges = sliding_edges(frames, side)
        if method == "dp":
            lower_bound, witness = minimum_cover_dp(edges, len(frames))
        else:
            lower_bound, witness = maximum_matching_path(edges, len(frames))
        records[side] = {
            "original_contact_true_frames": sum(x["contact"][side] for x in frames),
            "sliding_contiguous_stance_intervals": len(edges),
            "sliding_edge_start_frames": edges,
            "minimum_contact_state_changes_if_original_ankle_paths_preserved": lower_bound,
            "mathematical_witness_frames": witness,
            "witness_kind": "cover_relabel_positions" if method == "dp" else "disjoint_sliding_edges",
        }
    return {
        "schema": SCHEMA, "case": CASE, "method": method,
        "original_source_labels_sha256": labels_sha,
        "original_manifest_sha256": manifest_sha, "fps": 20, "frames": len(frames),
        "original_source_verdict": "FAIL", "records": records,
        "science": "COMBINATORIAL_CONTACT_LABEL_CONTRADICTION_ONLY",
        "disposition": "HOLD_NO_CORRECTION_OR_REALISM_ACCEPTANCE",
        "limitations": [
            "Original rights-only source, GLB and H264 remain unchanged and hash verified",
            "Minimum vertex-cover relabel bound is not a physically admissible takeoff/landing schedule",
            "Feet could instead be reanimated to fixed stance; that would change the spread motion",
            "No center-of-mass, flight impulse, force, contact patch, video or human realism test",
            "Never modify labels just to turn the source evaluator green",
        ],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--method", required=True, choices=("dp", "matching"))
    p.add_argument("--out", required=True)
    a = p.parse_args()
    out = Path(a.out)
    result = evaluate(Path(a.root), a.method)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("ORIGINAL_JACKS_CONTACT_CONTRADICTION", a.method,
          {side: (x["sliding_contiguous_stance_intervals"],
                  x["minimum_contact_state_changes_if_original_ankle_paths_preserved"])
           for side, x in result["records"].items()})

if __name__ == "__main__":
    main()
