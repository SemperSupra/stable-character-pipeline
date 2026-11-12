#!/usr/bin/env python3
"""Prepare a no-oracle video bakeoff for rights-original Stable Character corpus.

Consumes *local* generated files only; never fetches private Drive or person data.
Hashes are checked against the immutable source generation manifest before QA.
"""
import argparse
import hashlib
import json
from pathlib import Path

BATCHES = ("locomotion", "exercise_pose", "dance_combat", "aquatic")
STATIC_MOTIONS = frozenset(("stand", "pinup_pose"))

def load_manifest(root: Path):
    root = root.resolve(strict=True)
    cases = []
    seen = set()
    for batch in BATCHES:
        manifest = json.loads((root / batch / "manifest.json").read_text())
        if manifest.get("schema") != "scp.expanded-original-3d-motion-corpus.v1":
            raise ValueError("INVALID_CORPUS_SCHEMA")
        if manifest.get("batch") != batch or manifest.get("rights") != "CC0-1.0 for original generated files":
            raise ValueError("UNEXPECTED_BATCH_OR_RIGHTS")
        for item in manifest["cases"]:
            name = item["case"]
            if not isinstance(name, str) or not name or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in name):
                raise ValueError("INVALID_CASE_NAME")
            if name in seen:
                raise ValueError("DUPLICATE_CASE")
            seen.add(name)
            spec = item["spec"]
            if spec["motion"] not in {
                "walk", "run", "skip", "jump", "stand", "sit", "squat",
                "jumping_jacks", "cartwheel", "pinup_pose", "photoshoot",
                "dance", "karate_kata", "judo_kata", "kickboxing",
                "swimming", "diving",
            }:
                raise ValueError("UNKNOWN_MOTION")
            for video in item["videos"]:
                filename = video["file"]
                if filename != name + "_side.mp4":
                    raise ValueError("UNEXPECTED_VIDEO_NAME")
                src = (root / batch / filename).resolve(strict=True)
                if not src.is_relative_to(root):
                    raise ValueError("VIDEO_ESCAPES_CORPUS")
                sha = hashlib.sha256(src.read_bytes()).hexdigest()
                if sha != video["sha256"]:
                    raise ValueError("VIDEO_SHA_MISMATCH")
                cases.append({
                    "id": name + "_video",
                    "kind": "video",
                    "path": batch + "/" + filename,
                    "expected_motion": spec["motion"] not in STATIC_MOTIONS,
                    # No 'expect': an evaluator must not invent a gold label.
                })
    if not cases:
        raise ValueError("EMPTY_CORPUS")
    return {"schema": "scp.video-bakeoff-cases.v1", "cases": cases}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    root = args.root.resolve(strict=True)
    if args.out.resolve().parent != root:
        raise ValueError("OUTPUT_MUST_LIVE_IN_CORPUS_ROOT")
    document = load_manifest(root)
    args.out.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
    print("UNLABELLED_VIDEO_CASES", len(document["cases"]))

if __name__ == "__main__":
    main()
