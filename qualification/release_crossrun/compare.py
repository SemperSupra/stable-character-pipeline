"""Independent original H264 decoded-pixel cross-runtime differential.

Only original self-authored synthetic research; NO natural human gait acceptance.
Never uses source annotations as an image-quality/behavioral oracle.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

SCHEMA = "scp.release-crossrun.decode.v1"
CAMERAS = ("OriginalFront", "OriginalOblique")
MAX_FRAME_RAW = 192 * 1024 * 1024
MAX_ZIP_UNCOMPRESSED = 256 * 1024 * 1024

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def refuse(code):
    raise ValueError(code)

def content(z, path):
    try:
        return z.read(path)
    except KeyError:
        refuse("MISSING_ORIGINAL:" + path)

def verify_zip(z):
    members = z.infolist()
    if len({i.filename for i in members}) != len(members):
        refuse("DUPLICATE_ORIGINAL_ZIP_MEMBER")
    if len(members) > 100 or sum(i.file_size for i in members) > MAX_ZIP_UNCOMPRESSED:
        refuse("ARCHIVE_SIZE_OR_MEMBER_COUNT")
    for i in members:
        if i.filename.startswith("/") or ".." in Path(i.filename).parts or "\\" in i.filename:
            refuse("ARCHIVE_UNSAFE_PATH")
    if z.testzip() is not None:
        refuse("ORIGINAL_ZIP_CRC_FAILURE")

def probe(path):
    command = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
               "-of", "json", str(path)]
    proc = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
    streams = json.loads(proc.stdout).get("streams", [])
    if len(streams) != 1:
        refuse("VIDEO_STREAM_COVERAGE")
    meta = streams[0]
    try:
        width, height, frames = int(meta["width"]), int(meta["height"]), int(meta["nb_frames"])
        fps = meta["r_frame_rate"]
    except (KeyError, ValueError, TypeError):
        refuse("VIDEO_CLOCK_UNKNOWN")
    if width < 1 or height < 1 or frames < 1 or frames > 720 or width * height * frames * 3 > MAX_FRAME_RAW:
        refuse("VIDEO_FRAME_BUDGET")
    return {"width": width, "height": height, "frames": frames, "fps": fps}

def decode(raw):
    with tempfile.NamedTemporaryFile(suffix=".mp4") as f:
        f.write(raw)
        f.flush()
        meta = probe(f.name)
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", f.name,
               "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
        p = subprocess.run(cmd, capture_output=True, check=True, timeout=90)
        expected = meta["width"] * meta["height"] * meta["frames"] * 3
        if len(p.stdout) != expected:
            refuse("DECODED_FRAME_CLOCK_OR_BYTE_COUNT")
        return meta, p.stdout

def scene_provenance(media, evidence):
    source = content(evidence, "forward/source.json")
    data = json.loads(source)
    if data.get("rights") != "ORIGINAL_SELF_AUTHORED_SYNTHETIC" or data.get("schema") != "scp.walk_w7a_original_approach.v1":
        refuse("SOURCE_RIGHTS_OR_SCHEMA")
    witness = json.loads(content(evidence, "receipt/witness.json"))
    admission = json.loads(content(evidence, "receipt/release-admission.json"))
    if witness.get("source_sha256") != sha(source) or witness.get("full_body") != "FAIL_ABSTRACT_LIMBS_ONLY" or witness.get("private_r009") != "NOT_RUN_NOT_ADMITTED":
        refuse("SOURCE_OR_FIRST_FAILURE_NOT_PRESERVED")
    if admission != {"status": "UNKNOWN", "code": "DRAFT_NOT_PROMOTED"}:
        refuse("WRONG_RELEASE_HOLD")
    glb = content(media, "original_synthetic_24frame_skinned.glb")
    blend = content(media, "original_source_grounded_24frame_native.blend")
    if witness.get("glb_sha256") != sha(glb) or witness.get("blend_sha256") != sha(blend):
        refuse("NATIVE_BYTES_DONT_MATCH_WITNESS")
    originals = {}
    for camera in CAMERAS:
        raw = content(media, "rendered/" + camera + ".mp4")
        if witness.get("video_sha256", {}).get(camera) != sha(raw):
            refuse("ORIGINAL_VIDEO_SHA_DISAGREES_WITH_WITNESS")
        originals[camera] = raw
    return {"source_sha256": sha(source), "glb_sha256": sha(glb),
            "blend_sha256": sha(blend), "videos": originals}

def compare_raw(a, b, meta):
    size = meta["width"] * meta["height"] * 3
    matching, total_abs, total_sq, max_delta, per_frame = 0, 0, 0, 0, []
    for idx in range(meta["frames"]):
        left, right = a[idx * size:(idx + 1) * size], b[idx * size:(idx + 1) * size]
        if left == right:
            matching += 1
            per_frame.append(0.0)
            continue
        dif = [abs(x - y) for x, y in zip(left, right)]
        total_abs += sum(dif)
        total_sq += sum(d * d for d in dif)
        max_delta = max(max_delta, max(dif))
        per_frame.append(sum(dif) / size)
    count = size * meta["frames"]
    psnr = None if total_sq == 0 else round(10 * math.log10(255.0 ** 2 / (total_sq / count)), 3)
    return {"frames_equal_rgb": matching, "frames_total": meta["frames"],
            "mean_abs_rgb": total_abs / count, "max_rgb_delta": max_delta,
            "psnr_db": psnr, "per_frame_mean_abs_rgb": per_frame}

def compare(base_media_path, base_evidence_path, new_media_path, new_evidence_path):
    locations = list(map(Path, (base_media_path, base_evidence_path, new_media_path, new_evidence_path)))
    original_sha = [sha(p.read_bytes()) for p in locations]
    with zipfile.ZipFile(locations[0]) as a, zipfile.ZipFile(locations[1]) as ae, \
         zipfile.ZipFile(locations[2]) as b, zipfile.ZipFile(locations[3]) as be:
        for z in (a, ae, b, be):
            verify_zip(z)
        left = scene_provenance(a, ae)
        right = scene_provenance(b, be)
    if left["source_sha256"] != right["source_sha256"] or left["glb_sha256"] != right["glb_sha256"]:
        refuse("NOT_SAME_ORIGINAL_SOURCE_OR_NATIVE_GLB")
    cameras = []
    changed = False
    for name in CAMERAS:
        mb, va = decode(left["videos"][name])
        mn, vb = decode(right["videos"][name])
        if mb != mn:
            refuse("CROSS_RUNTIME_RESOLUTION_OR_FRAME_CLOCK_DRIFT")
        metrics = compare_raw(va, vb, mb)
        if metrics["frames_equal_rgb"] != metrics["frames_total"]:
            changed = True
        cameras.append({"camera": name, "metadata": mb,
                        "baseline_h264_sha256": sha(left["videos"][name]),
                        "candidate_h264_sha256": sha(right["videos"][name]),
                        **metrics})
    return {"schema": SCHEMA,
            "status": "OBSERVED_DECODED_DRIFT_NOT_SCIENTIFIC_ACCEPTANCE" if changed else "DECODED_FRAMES_EQUAL_NOT_SCIENTIFIC_ACCEPTANCE",
            "source_rights": "ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "source_sha256": left["source_sha256"],
            "glb_sha256": left["glb_sha256"],
            "baseline_blend_sha256": left["blend_sha256"],
            "candidate_blend_sha256": right["blend_sha256"],
            "input_zip_sha256": original_sha,
            "cameras": cameras,
            "human_behavior": "FAIL_ABSTRACT_LIMBS_ONLY",
            "private_r009": "NOT_RUN_NOT_ADMITTED"}

def main():
    p = argparse.ArgumentParser()
    for x in ("base_media", "base_evidence", "new_media", "new_evidence"):
        p.add_argument("--" + x.replace("_", "-"), required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    try:
        result = compare(args.base_media, args.base_evidence, args.new_media, args.new_evidence)
    except (ValueError, subprocess.CalledProcessError, zipfile.BadZipFile, json.JSONDecodeError) as e:
        raise SystemExit("CROSSRUN_FAIL_CLOSED " + str(e))
    Path(args.out).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(result["status"])

if __name__ == "__main__":
    main()
