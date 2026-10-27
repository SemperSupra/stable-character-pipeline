#!/usr/bin/env python3
"""R2: NASA separately published photo and video, public CPU pose observability."""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cc0_human_pose"))
from probe import LINKS, MODEL_URL

SOURCES = {
    "video": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/6/63/Astronaut_Mike_Hopkins-_Workout_in_Space_2.webm",
        "page": "https://commons.wikimedia.org/wiki/File:Astronaut_Mike_Hopkins-_Workout_in_Space_2.webm",
        "sha1": "dfc000088cfff728b57fe0c8ae38a7266410caeb",
        "bytes": 10680037, "limit": 12000000},
    "photo": {
        "url": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Michael_S._Hopkins%2C_official_portrait.jpg",
        "page": "https://commons.wikimedia.org/wiki/File:Michael_S._Hopkins,_official_portrait.jpg",
        "sha1": "e9e88122157dd60bc314d57754c02844954eaa00",
        "bytes": 3001066, "limit": 4000000}
}
MODEL_SHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"


def fetch(original_url, destination, maximum):
    if original_url not in ({a["url"] for a in SOURCES.values()} | {MODEL_URL}):
        raise ValueError("source not allowlisted")
    sha1, sha256 = hashlib.sha1(), hashlib.sha256()
    size = 0
    request = urllib.request.Request(original_url, headers={"User-Agent": "StableCharacterResearch/0.1"})
    with urllib.request.urlopen(request, timeout=50) as response, destination.open("wb") as stream:
        u = urllib.parse.urlparse(response.geturl())
        if u.scheme != "https" or u.hostname not in ("upload.wikimedia.org", "storage.googleapis.com"):
            raise ValueError("redirect to untrusted media host")
        while True:
            block = response.read(min(65536, maximum + 1 - size))
            if not block:
                break
            size += len(block)
            if size > maximum:
                raise ValueError("source exceeds bounded byte limit")
            stream.write(block)
            sha1.update(block)
            sha256.update(block)
    return {"bytes": size, "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()}


def verify(meta, digest):
    if meta["sha1"] != digest["sha1"] or meta["bytes"] != digest["bytes"]:
        raise ValueError("NASA original source SHA1 or length mismatch")


def points_row(result):
    landmarks = result.pose_landmarks[0] if result.pose_landmarks else []
    return [{"x": p.x, "y": p.y, "z": p.z, "visibility": p.visibility} for p in landmarks]


def draw_overlay(image, points, caption):
    import cv2
    h, w = image.shape[:2]
    for a, b in LINKS:
        if max(a, b) >= len(points):
            continue
        p, q = points[a], points[b]
        cv2.line(image, (int(p["x"] * w), int(p["y"] * h)),
                 (int(q["x"] * w), int(q["y"] * h)), (0, 225, 65), 2)
    cv2.rectangle(image, (0, 0), (w, 28), (0, 0, 0), -1)
    cv2.putText(image, caption, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                (255, 255, 255), 1, cv2.LINE_AA)
    return image


def run(destination):
    import cv2
    import mediapipe as mp
    import numpy as np

    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "independent-nasa-media-pair/1",
        "status": "RUNNING",
        "subject_metadata": "NASA captions both media as Michael S. Hopkins",
        "pairing": "INDEPENDENT_NASA_DOCUMENTARY_CAPTIONS_NOT_FACE_MATCHING",
        "photo_date": "2016-12-29",
        "video_date": "2014-02-19",
        "rights": "US_NASA_PUBLIC_DOMAIN_SOURCE_WITH_PERSONALITY_AND_INSIGNIA_CAVEATS",
        "identity_inference": "NOT_PERFORMED",
        "calibrated_3d_ground_truth": "NOT_AVAILABLE",
        "rigging": "NOT_TESTED",
        "media": {}
    }
    try:
        with tempfile.TemporaryDirectory() as td:
            t = Path(td)
            for kind, filename in (("video", "original.webm"), ("photo", "portrait.jpg")):
                digest = fetch(SOURCES[kind]["url"], t / filename, SOURCES[kind]["limit"])
                verify(SOURCES[kind], digest)
                receipt["media"][kind] = digest
            model = t / "pose.task"
            receipt["model"] = fetch(MODEL_URL, model, 12000000)
            if receipt["model"]["sha256"] != MODEL_SHA256:
                raise ValueError("pose task model does not match previously observed SHA256")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                            "-ss", "11", "-t", "30", "-i", str(t / "original.webm"),
                            "-vf", "fps=1,scale=640:-2",
                            "-frames:v", "30", str(t / "frame_%03d.png")],
                           check=True, timeout=60)
            frames = sorted(t.glob("frame_*.png"))
            if len(frames) != 30:
                raise ValueError("expected 30 sampled workout frames; got %s" % len(frames))
            photo = cv2.imread(str(t / "portrait.jpg"))
            if photo is None:
                raise ValueError("independent NASA portrait failed to decode")
            portrait_h, portrait_w = photo.shape[:2]
            portrait_small = cv2.resize(photo, (480, round(portrait_h * 480 / portrait_w)))
            cv2.imwrite(str(output / "independent_nasa_portrait.jpg"), portrait_small)
            options = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO, num_poses=1)
            still_options = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                running_mode=mp.tasks.vision.RunningMode.IMAGE, num_poses=1)
            temporal, montages = [], []
            with mp.tasks.vision.PoseLandmarker.create_from_options(options) as movie, mp.tasks.vision.PoseLandmarker.create_from_options(still_options) as portrait:
                rgb = cv2.cvtColor(portrait_small, cv2.COLOR_BGR2RGB)
                photo_points = points_row(portrait.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)))
                receipt["independent_photo_landmarks"] = len(photo_points)
                receipt["photo_resolution_original"] = [portrait_w, portrait_h]
                (output / "portrait_landmarks.json").write_text(json.dumps({
                    "source_kind": "INDEPENDENT_PUBLISHED_PHOTO", "source_url": SOURCES["photo"]["page"],
                    "landmarks2d": photo_points}, indent=2) + "\n")
                cv2.imwrite(str(output / "portrait_overlay.jpg"),
                            draw_overlay(portrait_small.copy(), photo_points, "NASA official portrait / model estimated 2D"))
                for i, path in enumerate(frames):
                    bgr = cv2.imread(str(path))
                    if bgr is None:
                        raise ValueError("missing extracted frame")
                    image = mp.Image(image_format=mp.ImageFormat.SRGB,
                                     data=cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                    points = points_row(movie.detect_for_video(image, i * 1000))
                    temporal.append({"frame": i, "source_video_offset_ms": 11000 + i * 1000,
                                     "landmarks2d": points})
                    overlay = draw_overlay(bgr.copy(), points, "NASA workout / model estimated 2D / %0.1fs" % (11 + i))
                    cv2.imwrite(str(output / ("frame_%03d.png" % (i + 1))), overlay)
                    if i in (0, 5, 10, 15, 20, 25):
                        montages.append(cv2.resize(overlay, (320, 180)))
            (output / "video_landmarks.json").write_text(json.dumps(temporal, indent=2) + "\n")
            cv2.imwrite(str(output / "contact_sheet.jpg"),
                        np.vstack([np.hstack(montages[:3]), np.hstack(montages[3:6])]))
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                            "-framerate", "1", "-start_number", "1",
                            "-i", str(output / "frame_%03d.png"), "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                            str(output / "video_pose_preview.mp4")], check=True, timeout=60)
            receipt["sampling_window_seconds"] = [11, 41]\n            receipt["sampling_rate_hz"] = 1\n            receipt["video_frames"] = len(temporal)
            receipt["video_frames_33_points"] = sum(len(x["landmarks2d"]) == 33 for x in temporal)
            if receipt["video_frames_33_points"] == 0:
                raise ValueError("NO_POSE_DETECTION_ON_NASA_WORKOUT_VIDEO")
            receipt["status"] = ("OBSERVED_VIDEO_AND_INDEPENDENT_PHOTO_POSES_NOT_RIG"
                                 if len(photo_points) == 33 else
                                 "OBSERVED_VIDEO_POSE_PHOTO_POSE_UNAVAILABLE")
            receipt["cross_source_pose_accuracy"] = "NOT_SCORABLE_DIFFERENT_TIME_CAMERA_AND_OUTFIT"
            receipt["same_person_basis"] = "TWO_NASA_AUTHORED_CAPTIONS_NOT_VISUAL_IDENTIFICATION"
    except Exception as e:
        receipt["status"] = "FAILED_FIRST_ERROR"
        receipt["first_error"] = type(e).__name__ + ": " + str(e)
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="nasa-pair-output")
    run(p.parse_args().out)
