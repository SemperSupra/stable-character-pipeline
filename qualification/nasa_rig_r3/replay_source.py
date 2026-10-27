#!/usr/bin/env python3
"""R5 clean-slate fixed NASA originals replay without expiring Actions artifacts.

Scientific inference runs in isolated public CPU job via existing R2 adapter.
FFmpeg comes from the version-pinned, self-contained imageio-ffmpeg wheel.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nasa_pair"))
from r2_probe import MODEL_SHA256, SOURCES

EXPECTED_VIDEO_SHA256 = "afcc7cb94b6c52de74a3892e7f1bf042700da3c96fb7fbec83f295b05f32f76a"
EXPECTED_PHOTO_SHA256 = "3c9f612dc86e2e496a8521b448ea58835d918343a8070aefb99de37410423c15"
REFERENCE_LANDMARK_SHA256 = "a6b56e7d794a5b74701031a75d350a9b2163182950861c1d135ec18b748c9b53"
REFERENCE_R2_RECEIPT_SHA256 = "9a9d3c891ad34a78543bccf46a537528e1fc942701878c8ad0f4df131f43b2e7"


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_native_receipt(record):
    if record.get("status") != "OBSERVED_VIDEO_AND_INDEPENDENT_PHOTO_POSES_NOT_RIG":
        raise ValueError("R2 NASA source replay not independently observed for both inputs")
    media = record.get("media") or {}
    for name, expected in (("video", EXPECTED_VIDEO_SHA256), ("photo", EXPECTED_PHOTO_SHA256)):
        actual = media.get(name, {})
        source = SOURCES[name]
        if actual.get("bytes") != source["bytes"] or actual.get("sha1") != source["sha1"] or actual.get("sha256") != expected:
            raise ValueError("source original SHA or file size changed for " + name)
    if (record.get("model") or {}).get("sha256") != MODEL_SHA256:
        raise ValueError("model weights SHA256 differs from native R2")
    if record.get("video_frames") != 30:
        raise ValueError("wrong fixed-source temporal frame count")
    if record.get("independent_photo_landmarks") != 33:
        raise ValueError("distinct NASA portrait pose inference failed")


def analyze(out):
    receipt_path = out / "receipt.json"
    observed_path = out / "video_landmarks.json"
    record = json.loads(receipt_path.read_text())
    verify_native_receipt(record)
    frames = json.loads(observed_path.read_text())
    if len(frames) != 30:
        raise ValueError("landmark observations not 30 frames")
    detected = 0
    continuous = 0
    best = 0
    for i, frame in enumerate(frames):
        if frame.get("frame") != i or frame.get("source_video_offset_ms") != 11000 + 1000 * i:
            raise ValueError("source timestamps drifted from 1Hz 11-40s window")
        count = len(frame.get("landmarks2d") or [])
        if count not in (0, 33):
            raise ValueError("partial skeleton")
        if count == 33:
            detected += 1
            continuous += 1
            best = max(best, continuous)
        else:
            continuous = 0
    if best < 5:
        raise ValueError("insufficient contiguous detected frames for R3 source replay")
    observed_sha = sha256(observed_path)
    receipt_sha = sha256(receipt_path)
    proof = {
        "schema": "nasa-verified-source-replay/1",
        "status": "SOURCE_REPLAY_VERIFIED_WITH_CONTENT_CLASSIFIED",
        "observation_kind": "MODEL_ESTIMATED_2D_NOT_METRIC_3D",
        "input_origin": "DIRECT_PINNED_NASA_ORIGINALS_AND_OFFICIAL_MEDIAPIPE_MODEL_NO_ACTIONS_ARTIFACT",
        "media_original_sha256": {k: record["media"][k]["sha256"] for k in ("video", "photo")},
        "model_sha256": record["model"]["sha256"],
        "current_landmarks_sha256": observed_sha,
        "r2_reference_landmarks_sha256": REFERENCE_LANDMARK_SHA256,
        "bit_identical_observations_to_r2": observed_sha == REFERENCE_LANDMARK_SHA256,
        "current_r2_receipt_sha256": receipt_sha,
        "r2_reference_receipt_sha256": REFERENCE_R2_RECEIPT_SHA256,
        "bit_identical_receipt_to_r2": receipt_sha == REFERENCE_R2_RECEIPT_SHA256,
        "total_frames": len(frames),
        "pose_detected_frames": detected,
        "longest_contiguous_detected_frames": best,
        "independent_nasa_photo_pose_landmarks": record["independent_photo_landmarks"],
        "rights": "NASA US PUBLIC-DOMAIN-MEDIA CLAIM ONLY; PERSONALITY, GLOBAL AND MODEL REDISTRIBUTION REMAIN SEPARATE",
        "subject_pairing": "NASA_SOURCE_CAPTIONS_NOT_VISUAL_IDENTITY_INFERENCE",
        "anatomy_and_skinning": "NOT_INFERRED_BY_R2"
    }
    (out / "direct_source_replay.json").write_text(json.dumps(proof, indent=2) + "\n")
    print("R5_REPLAY_RECEIPT " + json.dumps(proof, sort_keys=True))
    return proof


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="nasa-pair-output")
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    import imageio_ffmpeg
    with tempfile.TemporaryDirectory(prefix="r5-ffmpeg-") as temp:
        ffbin = Path(temp) / "ffmpeg"
        ffbin.symlink_to(Path(imageio_ffmpeg.get_ffmpeg_exe()).resolve())
        env = dict(os.environ)
        env["PATH"] = temp + os.pathsep + env.get("PATH", "")
        subprocess.run([str(ffbin), "-version"], check=True, stdout=subprocess.DEVNULL, timeout=12)
        r2 = Path(__file__).resolve().parents[1] / "nasa_pair" / "r2_probe.py"
        subprocess.run([sys.executable, str(r2), "--out", str(out)], env=env, check=True, timeout=200)
    analyze(out)


if __name__ == "__main__":
    main()
