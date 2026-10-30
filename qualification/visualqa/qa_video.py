"""Source-clean L1 *pixel/video* observer. Not a human anatomical or identity oracle.

Runs only on authorized synthetic/public-rights media. NEVER uploads inputs.
Receipt makes no claim that a pose was detected in the decoded image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

MAX_BYTES = 100 * 1024 * 1024
MAX_FRAMES = 600
MAX_SIDE = 1920


def command(argv):
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=90, check=True)


def inspect(video, output):
    video = Path(video)
    if not video.is_file() or video.is_symlink() or not (1024 <= video.stat().st_size <= MAX_BYTES):
        raise ValueError("VIDEO_NOT_ADMITTED")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    meta = json.loads(command(["ffprobe", "-v", "error", "-count_frames",
                               "-select_streams", "v:0",
                               "-show_entries", "stream=codec_name,width,height,avg_frame_rate,nb_read_frames",
                               "-of", "json", str(video)]).stdout)
    if len(meta.get("streams", [])) != 1:
        raise ValueError("ONE_VIDEO_STREAM_REQUIRED")
    stream = meta["streams"][0]
    width, height = int(stream["width"]), int(stream["height"])
    frames = int(stream["nb_read_frames"])
    if stream.get("codec_name") != "h264" or not (16 <= width <= MAX_SIDE and 16 <= height <= MAX_SIDE) or not (2 <= frames <= MAX_FRAMES):
        raise ValueError("VIDEO_CODEC_SIZE_FRAMES_NOT_ADMITTED")
    # Actual decoded image bytes, not declared metadata, are checked below.
    md5text = command(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video),
                       "-map", "0:v:0", "-an", "-f", "framemd5", "-"]).stdout
    digest_rows = [row.split(",")[-1].strip() for row in md5text.splitlines() if row and not row.startswith("#")]
    if len(digest_rows) != frames or any(not re.fullmatch(r"[0-9a-f]{32}", d) for d in digest_rows):
        raise ValueError("ACTUAL_FRAME_COUNT_OR_MD5_INCONSISTENT")
    unique = len(set(digest_rows))
    # Independently inspect near-black spans and extended repeated-picture spans.
    black = command(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(video), "-vf",
                     "blackdetect=d=0.50:pix_th=0.10", "-an", "-f", "null", "-"]).stderr
    freeze = command(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(video), "-vf",
                      "freezedetect=n=-50dB:d=1.0", "-an", "-f", "null", "-"]).stderr
    black_events = [line.strip() for line in black.splitlines() if "black_start:" in line]
    freeze_events = [line.strip() for line in freeze.splitlines() if "freeze_start:" in line]
    contact = output / "contact_sheet.png"
    command(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video),
             "-vf", "fps=2,scale=320:180,tile=4x3", "-frames:v", "1", str(contact)])
    if not contact.is_file() or contact.stat().st_size <= 1024:
        raise ValueError("ACTUAL_VISUAL_CONTACT_SHEET_MISSING")
    failures = []
    if unique < 3:
        failures.append("VIDEO_STATIC_OR_REPEATED")
    if black_events:
        failures.append("BLACK_SPAN_DETECTED")
    if freeze_events:
        failures.append("FREEZE_SPAN_DETECTED")
    receipt = {
        "schema": "scp.visualqa.l1_video.v1",
        "status": "FAIL" if failures else "PASS_L1_VIDEO_ONLY",
        "source_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "contact_sheet_sha256": hashlib.sha256(contact.read_bytes()).hexdigest(),
        "frames_decoded": len(digest_rows),
        "unique_image_frame_digests": unique,
        "video": {"codec": stream["codec_name"], "width": width,
                  "height": height, "rate": stream["avg_frame_rate"]},
        "failures": failures,
        "black_spans": black_events,
        "freeze_spans": freeze_events,
        "anatomy": "UNKNOWN_NOT_MEASURED_FROM_PIXELS",
        "identity": "UNKNOWN_NOT_EVALUATED",
        "camera_and_skinning": "UNKNOWN_NO_INDEPENDENT_RENDER_GEOMETRY_WITNESS"
    }
    (output / "video_qa.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        r = inspect(args.video, args.out)
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as err:
        print("VISUALQA_L1_UNKNOWN", type(err).__name__, str(err)[:300], file=sys.stderr)
        return 3
    print(json.dumps(r, sort_keys=True))
    return 0 if r["status"] == "PASS_L1_VIDEO_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
