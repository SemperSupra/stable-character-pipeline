#!/usr/bin/env python3
"""Independent, read-only qualification of public Mechanica preview media.

Uses only Python stdlib plus ffmpeg/ffprobe installed in the host runner.
This is a media/structure probe, not Blender review, collision checking,
iPhone device testing, physical validation, or release acceptance.
"""
import argparse
import hashlib
import json
import pathlib
import struct
import subprocess
import sys

EXPECTED_SOURCE = "ee3f027a2d1e05b9a1b44dd5c5569a19b35dd4d1"
EXPECTED_RIGS = {
    "ground/suv", "air/utility-twin", "space/orbital-tug", "titan/iron-atlas"
}
EXPECTED_TRACKS = 50
EXPECTED_PARTS = 189


class QualificationError(Exception):
    pass


def require(value, reason):
    if not value:
        raise QualificationError(reason)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_json(argv):
    proc = subprocess.run(argv, check=True, capture_output=True, text=True)
    return json.loads(proc.stdout)


def ffprobe(path):
    return run_json([
        "ffprobe", "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path)
    ])


def iso_boxes(data):
    boxes = []
    pos = 0
    while pos + 8 <= len(data):
        size, typ = struct.unpack_from(">I4s", data, pos)
        header = 8
        if size == 1:
            require(pos + 16 <= len(data), "truncated 64-bit MP4 box header")
            size = struct.unpack_from(">Q", data, pos + 8)[0]
            header = 16
        if size == 0:
            size = len(data) - pos
        require(size >= header and pos + size <= len(data),
                "malformed MP4 box structure")
        boxes.append(typ.decode("ascii", errors="replace"))
        pos += size
    require(pos == len(data), "trailing truncated MP4 bytes")
    return boxes


def gray_frames(path, width=120, height=68):
    proc = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostdin", "-v", "error",
        "-i", str(path), "-an", "-vf",
        f"fps=1,scale={width}:{height},format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-"
    ], check=True, capture_output=True)
    size = width * height
    require(len(proc.stdout) % size == 0, "incomplete decoded gray frame")
    return [proc.stdout[i:i + size]
            for i in range(0, len(proc.stdout), size)]


def frame_motion(frames):
    require(len(frames) >= 7, "fewer than seven sampled decoded frames")
    require(any(max(frame) - min(frame) >= 12 for frame in frames),
            "sampled frames lack visible contrast")
    require(any(sum(px >= 15 for px in frame) >= len(frame) // 50
                for frame in frames),
            "video appears almost black")
    diffs = [
        round(sum(abs(a - b) for a, b in zip(before, after))
              / len(before), 4)
        for before, after in zip(frames, frames[1:])
    ]
    require(sum(delta > 0.6 for delta in diffs) >= 3,
            "decoded video lacks sufficient measurable motion")
    return diffs


def inspect_movie(path):
    require(path.is_file() and path.stat().st_size > 2000,
            f"missing/empty MP4: {path.name}")
    meta = ffprobe(path)
    videos = [x for x in meta["streams"] if x["codec_type"] == "video"]
    require(len(videos) == 1, f"{path.name}: expected exactly one video stream")
    v = videos[0]
    require(v["codec_name"] == "h264", f"{path.name}: non-H264 video")
    require(v["pix_fmt"] == "yuv420p", f"{path.name}: non-yuv420p video")
    require((int(v["width"]), int(v["height"])) == (960, 540),
            f"{path.name}: unexpected pixel dimensions")
    require(int(v.get("nb_frames", 0)) == 49,
            f"{path.name}: expected 49 actual frames")
    duration = float(meta["format"]["duration"])
    require(8.0 < duration < 9.0,
            f"{path.name}: unexpected duration {duration}")
    boxes = iso_boxes(path.read_bytes())
    require("ftyp" in boxes and "moov" in boxes and "mdat" in boxes,
            f"{path.name}: missing required ISO base media box")
    require(boxes.index("moov") < boxes.index("mdat"),
            f"{path.name}: MP4 faststart moov must precede mdat")
    diffs = frame_motion(gray_frames(path))
    return {
        "filename": path.name, "sha256": sha256(path),
        "bytes": path.stat().st_size, "video_codec": v["codec_name"],
        "pixel_format": v["pix_fmt"], "width": int(v["width"]),
        "height": int(v["height"]), "frame_count": int(v["nb_frames"]),
        "duration_seconds": duration, "faststart": True,
        "sampled_frame_l1_deltas": diffs
    }


def inspect_contact_sheet(path):
    require(path.is_file(), f"missing contact sheet {path.name}")
    meta = ffprobe(path)
    video = next((s for s in meta["streams"]
                  if s["codec_type"] == "video"), None)
    require(video and video["codec_name"] == "png",
            f"{path.name}: contact sheet is not PNG")
    require((int(video["width"]), int(video["height"])) == (960, 540),
            f"{path.name}: unexpected contact-sheet dimensions")
    return {"filename": path.name, "sha256": sha256(path),
            "bytes": path.stat().st_size}


def parse_glb(data):
    require(len(data) >= 28, "GLB truncated")
    magic, version, length = struct.unpack_from("<III", data)
    require(magic == 0x46546c67 and version == 2, "invalid glTF 2.0 header")
    require(length == len(data), "GLB declared length mismatch")
    chunk_length, chunk_type = struct.unpack_from("<I4s", data, 12)
    require(chunk_type == b"JSON", "GLB first chunk is not JSON")
    require(20 + chunk_length <= len(data), "GLB truncated JSON chunk")
    return json.loads(data[20:20 + chunk_length])


def inspect_rig(preview_dir):
    manifest_path = preview_dir / "rig_manifest.json"
    glb_path = preview_dir / "mechanical_scene.glb"
    require(manifest_path.is_file() and glb_path.is_file(),
            "missing mechanical GLB or rig manifest")
    manifest = json.loads(manifest_path.read_text())
    require(manifest["Schema"] == "mechanical.rig.v0", "wrong rig schema")
    require({r["Name"] for r in manifest["Rigs"]} == EXPECTED_RIGS,
            "public rig inventory drift")
    require(manifest["Tracks"] == EXPECTED_TRACKS,
            "rig manifest track count drift")
    require(manifest["Parts"] == EXPECTED_PARTS,
            "rig manifest part count drift")
    require(sum(len(r["Joints"]) for r in manifest["Rigs"]) == EXPECTED_TRACKS,
            "manifest joint and track counts inconsistent")
    glb = parse_glb(glb_path.read_bytes())
    require(len(glb.get("animations", [])) >= 1, "GLB has no animation")
    channels = glb["animations"][0]["channels"]
    require(len(channels) == EXPECTED_TRACKS, "GLB animation channel count drift")
    require(all(c["target"]["path"] == "rotation" for c in channels),
            "unexpected animation target path")
    require(len(glb["nodes"]) == EXPECTED_PARTS + 1,
            "glTF scene node count drift")
    return {
        "glb_sha256": sha256(glb_path),
        "manifest_sha256": sha256(manifest_path),
        "rigs": sorted(EXPECTED_RIGS),
        "part_count": manifest["Parts"],
        "joint_tracks": manifest["Tracks"],
        "animation_channels": len(channels)
    }


def self_test():
    errors = []
    for name, action in [
        ("bad_glb_header", lambda: parse_glb(b"\x00" * 28)),
        ("black_frames", lambda: frame_motion([bytes(120 * 68)] * 8)),
        ("frozen_frames", lambda: frame_motion(
            [bytes([100 if i % 2 == 0 else 180]) * (120 * 68)
             for i in range(8)])),
        ("truncated_mp4_box", lambda: iso_boxes(b"\x00\x00\x00\x10moov"))
    ]:
        try:
            action()
        except QualificationError:
            errors.append({"fixture": name, "detected": True})
        else:
            raise QualificationError(f"negative control escaped: {name}")
    return errors


def inspect(directory):
    provenance = dict(line.split("=", 1) for line in
                      (directory / "provenance.txt").read_text().splitlines()
                      if "=" in line)
    require(provenance.get("source_sha") == EXPECTED_SOURCE,
            "preview source commit mismatch")
    require(provenance.get("generated_by") == "public_GitHub_Actions",
            "unrecognized preview producer")
    require(provenance.get("rig_count") == "4",
            "preview provenance rig count mismatch")
    return {
        "schema": "mechanica.playback_qualification.v1",
        "status": "PASS_MEDIA_STRUCTURE_ONLY",
        "source_sha": EXPECTED_SOURCE,
        "scope": "independent ffprobe/ffmpeg decode, GLB structure and preview provenance",
        "rig": inspect_rig(directory),
        "movies": [
            inspect_movie(directory / "mechanical_articulation.mp4"),
            inspect_movie(directory / "titan_articulation.mp4")
        ],
        "contact_sheets": [
            inspect_contact_sheet(directory / "mechanical_contact_sheet.png"),
            inspect_contact_sheet(directory / "titan_contact_sheet.png")
        ],
        "negative_controls": self_test(),
        "open_gates": [
            "human visual acceptance", "actual iPhone Safari playback",
            "Blender import and independent render", "joint limits/collision",
            "ground contact/physics", "source-rights review", "merge/release/deploy"
        ]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-dir", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            report = {"negative_controls": self_test(), "status": "PASS"}
        else:
            require(args.preview_dir is not None, "--preview-dir required")
            report = inspect(args.preview_dir)
    except (QualificationError, KeyError, ValueError,
            subprocess.CalledProcessError) as exc:
        report = {"status": "FAIL", "first_failure": str(exc)}
        print(json.dumps(report, indent=2), file=sys.stderr)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
        return 1
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
