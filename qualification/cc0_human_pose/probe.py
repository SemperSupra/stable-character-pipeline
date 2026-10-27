#!/usr/bin/env python3
"""Bounded original-video -> same-take stills -> MediaPipe landmarks research probe."""
import argparse
import hashlib
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

SOURCE_URL = "https://upload.wikimedia.org/wikipedia/commons/c/c3/Ej_Exercise_-_ESP_ICT.webm"
SOURCE_SHA1 = "43e2cd38a7ebf75d10ed9ab76a0420b1391ecf8c"
SOURCE_SIZE = 2334882
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
LINKS = ((11, 13), (13, 15), (12, 14), (14, 16), (11, 12),
         (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
         (24, 26), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32))


def fetch(url, path, limit):
    if url not in (SOURCE_URL, MODEL_URL):
        raise ValueError("source URL not allowlisted")
    request = urllib.request.Request(url, headers={"User-Agent": "StableCharacterResearch/0.1 (public source verification)"})
    h1, h256 = hashlib.sha1(), hashlib.sha256()
    count = 0
    with urllib.request.urlopen(request, timeout=35) as response, path.open("wb") as stream:
        if response.geturl().split("/")[2] not in ("upload.wikimedia.org", "storage.googleapis.com"):
            raise ValueError("unrecognized redirect")
        while True:
            b = response.read(min(65536, limit + 1 - count))
            if not b:
                break
            count += len(b)
            if count > limit:
                raise ValueError("download limit exceeded")
            stream.write(b)
            h1.update(b)
            h256.update(b)
    return {"bytes": count, "sha1": h1.hexdigest(), "sha256": h256.hexdigest()}


def check_original(actual):
    if actual["bytes"] != SOURCE_SIZE or actual["sha1"] != SOURCE_SHA1:
        raise ValueError("immutable original media does not match Wikimedia checksum")


def run(args):
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"schema": "cc0-pose-recovery/1", "status": "RUNNING",
               "source": "https://commons.wikimedia.org/wiki/File:Ej_Exercise_-_ESP_ICT.webm",
               "rights": "CC0-1.0 media only; personality/model release unknown",
               "pairing": "SAME_VIDEO_FRAMES_NOT_INDEPENDENT_PHOTOS",
               "geometry": "2D_ESTIMATED_AND_MODEL_WORLD_3D_NOT_GROUND_TRUTH",
               "rigging": "NOT_TESTED", "person_identity_inference": "NOT_TESTED"}
    try:
        import cv2
        import mediapipe as mp
        import numpy as np

        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            source = work / "original.webm"
            model = work / "pose.task"
            receipt["media"] = fetch(SOURCE_URL, source, 4000000)
            check_original(receipt["media"])
            receipt["model"] = fetch(MODEL_URL, model, 12000000)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                            "-t", "6", "-i", str(source), "-vf", "fps=2",
                            "-frames:v", "12", str(work / "frame_%03d.png")],
                           check=True, timeout=45)
            frames = sorted(work.glob("frame_*.png"))
            if len(frames) != 12:
                raise ValueError("expected exactly 12 decoded frames; got %d" % len(frames))
            opts = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=1)
            still_opts = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                running_mode=mp.tasks.vision.RunningMode.IMAGE, num_poses=1)
            observations, overlays = [], []
            with mp.tasks.vision.PoseLandmarker.create_from_options(opts) as detector, mp.tasks.vision.PoseLandmarker.create_from_options(still_opts) as single:
                for index, frame in enumerate(frames):
                    bgr = cv2.imread(str(frame))
                    if bgr is None:
                        raise ValueError("corrupt extracted frame")
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                    detected = detector.detect_for_video(mp_img, index * 500)
                    points = detected.pose_landmarks[0] if detected.pose_landmarks else []
                    world = detected.pose_world_landmarks[0] if detected.pose_world_landmarks else []
                    row = {"frame": index, "timestamp_ms": index * 500, "detected": bool(points),
                           "landmarks2d": [{"x": p.x, "y": p.y, "z": p.z,
                                            "visibility": getattr(p, "visibility", None)} for p in points],
                           "world3d_model_estimate": [{"x": p.x, "y": p.y, "z": p.z} for p in world]}
                    observations.append(row)
                    for a, b in LINKS:
                        if len(points) > max(a, b):
                            x1, y1 = int(points[a].x * bgr.shape[1]), int(points[a].y * bgr.shape[0])
                            x2, y2 = int(points[b].x * bgr.shape[1]), int(points[b].y * bgr.shape[0])
                            cv2.line(bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(bgr, "CC0 source / estimated pose t=%.1fs" % (index / 2),
                                (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)
                    cv2.imwrite(str(output / ("overlay_%03d.png" % (index + 1))), bgr)
                    overlays.append(bgr)
                    if index == 4:
                        single_result = single.detect(mp_img)
                        pair = single_result.pose_landmarks[0] if single_result.pose_landmarks else []
                        receipt["same_frame_still_vs_video"] = {
                            "still_detected": bool(pair), "video_detected": bool(points),
                            "mean_joint_xy_distance_normalized": (
                                sum(((p.x - q.x)**2 + (p.y - q.y)**2)**0.5
                                    for p, q in zip(pair, points)) / len(pair)
                                if len(pair) == len(points) and len(pair) == 33 else None),
                            "independent_photo": False}
                        cv2.imwrite(str(output / "same_person_derived_still.png"),
                                    cv2.imread(str(frame)))
            (output / "landmarks.json").write_text(json.dumps(observations, indent=2))
            receipt["frames"] = len(frames)
            receipt["frames_with_33_landmarks"] = sum(len(r["landmarks2d"]) == 33 for r in observations)
            receipt["observed_motion"] = "NO_REFERENCE_ORACLE"
            resized = [cv2.resize(im, (184, 328)) for im in overlays[::2]]
            cv2.imwrite(str(output / "contact_sheet.jpg"),
                        np.vstack([np.hstack(resized[:3]), np.hstack(resized[3:6])]))
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                            "-framerate", "2", "-start_number", "1",
                            "-i", str(output / "overlay_%03d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                            str(output / "preview.mp4")], check=True, timeout=45)
            if receipt["frames_with_33_landmarks"] == 0:
                raise ValueError("NO_POSE_DETECTED: video decoded, but no valid landmark frames")
            receipt["status"] = "OBSERVED_POSE_NOT_RIG_OR_IDENTITY"
    except Exception as exc:
        receipt["status"] = "FAILED_FIRST_ERROR"
        receipt["first_error"] = "%s: %s" % (type(exc).__name__, str(exc))
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="pose-probe-output")
    run(parser.parse_args())
