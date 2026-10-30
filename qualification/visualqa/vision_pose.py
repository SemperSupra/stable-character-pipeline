"""L3 independent *actual image model* research observer, not an anatomy pass.

Pinned CPU MediaPipe Lite from prior public R1/R2. Only original synthetic
video + receipt may run; no image upload or private source access.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import urllib.parse
import urllib.request

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
MODEL_SHA256 = "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"
MODEL_MAX = 12_000_000
RIG_POINTS = (23, 24, 25, 26, 27, 28, 29, 30, 31, 32)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as inp:
        while True:
            block = inp.read(65536)
            if not block:
                return h.hexdigest()
            h.update(block)


def acquire(path):
    # One exact allowlisted pinned public model, no token or input upload.
    with urllib.request.urlopen(urllib.request.Request(
         MODEL_URL, headers={"User-Agent": "StableCharacterVisualQA/0.1"}), timeout=40) as response:
        parsed = urllib.parse.urlparse(response.geturl())
        if parsed.scheme != "https" or parsed.hostname != "storage.googleapis.com":
            raise ValueError("UNTRUSTED_MODEL_REDIRECT")
        total = 0
        with path.open("wb") as output:
            while True:
                block = response.read(min(65536, MODEL_MAX + 1 - total))
                if not block:
                    break
                total += len(block)
                if total > MODEL_MAX:
                    raise ValueError("MODEL_DOWNLOAD_TOO_LARGE")
                output.write(block)
    if sha(path) != MODEL_SHA256:
        raise ValueError("MODEL_SHA256_CHANGED")


def observe(video, native_receipt, output):
    import mediapipe as mp
    video, native_receipt, output = Path(video), Path(native_receipt), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    native = json.loads(native_receipt.read_text())
    if native.get("source_rights") != "ORIGINAL_SELF_AUTHORED_SYNTHETIC" or native.get("video_sha256") != sha(video):
        raise ValueError("SOURCE_RIGHTS_OR_EXACT_VIDEO_MISMATCH")
    with tempfile.TemporaryDirectory() as temp:
        t = Path(temp)
        model = t / "pose.task"
        acquire(model)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video),
                        "-vf", "fps=1", "-frames:v", "6", str(t / "frame_%03d.png")],
                       check=True, timeout=60)
        frames = sorted(t.glob("frame_*.png"))
        if len(frames) != 6:
            raise ValueError("EXACT_FRAME_SAMPLING_FAILED")
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=2, min_pose_detection_confidence=0.5)
        observations = []
        with mp.tasks.vision.PoseLandmarker.create_from_options(options) as detector:
            for i, path in enumerate(frames):
                image = mp.Image.create_from_file(str(path))
                result = detector.detect_for_video(image, i * 1000)
                poses = []
                for person in result.pose_landmarks:
                    if len(person) != 33:
                        continue
                    poses.append({str(j): {"x":float(person[j].x), "y":float(person[j].y),
                                           "visibility":float(person[j].visibility)}
                                  for j in RIG_POINTS})
                observations.append({"source_time_ms":i*1000, "pose_count":len(poses),
                                     "observed_image_landmarks":poses})
    receipt = {
        "schema": "scp.visualqa.l3_pixel_inferred_pose_research.v1",
        "status": "OBSERVED_UNQUALIFIED" if any(o["pose_count"] for o in observations)
                  else "UNKNOWN_NO_MODEL_POSE_DETECTION",
        "source_rights": "ORIGINAL_SELF_AUTHORED_SYNTHETIC",
        "video_sha256": sha(video), "model_sha256": MODEL_SHA256,
        "model": "MediaPipe Lite fixed SHA256 / 33 points / CPU",
        "samples": observations,
        "detected_pose_frames": sum(bool(o["pose_count"]) for o in observations),
        "projected_3d_image_parity": "UNKNOWN_NO_CALIBRATED_CAMERA_OR_MODEL_ERROR_ORACLE",
        "correct_human_anatomy": "UNKNOWN_NO_INDEPENDENT_REFERENCE",
        "overall_visual_qa": "NOT_ACCEPTED_RESEARCH_ONLY"
    }
    (output / "l3_model_observations.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status":receipt["status"], "detected_pose_frames":receipt["detected_pose_frames"],
                      "overall_visual_qa":receipt["overall_visual_qa"]}))
    return receipt


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--video", required=True)
    a.add_argument("--native-receipt", required=True)
    a.add_argument("--out", required=True)
    opts = a.parse_args()
    observe(opts.video, opts.native_receipt, opts.out)
