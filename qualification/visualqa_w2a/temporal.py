"""W2A: Independent bounded real-pixel temporal witness; not gait acceptance.

Compares actual H264 grayscale frames to separately observed Blender joint motion.
Preserves L1 freeze veto and never upgrades a failed video to PASS. No model/API.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess

MAX_VIDEO_BYTES = 100_000_000
MAX_PIXEL_BYTES = 96_000_000
MAX_FRAMES = 180
MAX_WIDTH, MAX_HEIGHT = 640, 360


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_actual(video):
    video = Path(video)
    if not video.is_file() or video.is_symlink() or not 1024 < video.stat().st_size <= MAX_VIDEO_BYTES:
        raise ValueError("VIDEO_ADMISSION")
    p = subprocess.run(["ffprobe", "-v", "error", "-count_frames",
                        "-select_streams", "v:0",
                        "-show_entries", "stream=codec_name,width,height,nb_read_frames,avg_frame_rate",
                        "-of", "json", str(video)], check=True,
                       capture_output=True, text=True, timeout=25)
    streams = json.loads(p.stdout).get("streams", [])
    if len(streams) != 1 or streams[0].get("codec_name") != "h264":
        raise ValueError("H264_STREAM_REQUIRED")
    w, h = int(streams[0]["width"]), int(streams[0]["height"])
    count = int(streams[0]["nb_read_frames"])
    if not 16 <= w <= MAX_WIDTH or not 16 <= h <= MAX_HEIGHT or not 2 <= count <= MAX_FRAMES or w*h*count > MAX_PIXEL_BYTES:
        raise ValueError("BOUNDED_RGB_DECODE_ADMISSION")
    p = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video),
                        "-map", "0:v:0", "-an", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True,
                       check=True, timeout=60)
    if len(p.stdout) != w*h*count:
        raise ValueError("ACTUAL_FRAME_DECODE_LENGTH")
    size = w*h
    return w, h, [memoryview(p.stdout)[i*size:(i+1)*size] for i in range(count)], streams[0]["avg_frame_rate"]


def frame_difference(before, after):
    if len(before) != len(after) or not before:
        raise ValueError("FRAME_PAIR_SIZE")
    total, changed = 0, 0
    # Byte-perfect decoded GRAY pixels, not compressed stream differences.
    for a, b in zip(before, after):
        d = abs(a-b)
        total += d
        changed += d > 8
    return {"mean_abs_gray": round(total/len(before), 6),
            "fraction_pixels_delta_gt8": round(changed/len(before), 6)}


def read_source(path, video, native):
    p = Path(path)
    if p.stat().st_size > 4_000_000:
        raise ValueError("SOURCE_OBSERVATION_SIZE")
    witness = json.loads(p.read_text())
    receipt = json.loads(Path(native).read_text())
    if (witness.get("schema") != "scp.visualqa.l2_knee_input.v1" or
        witness.get("rights") != "ORIGINAL_SELF_AUTHORED_SYNTHETIC" or
        receipt.get("source_rights") != witness["rights"] or
        witness.get("source_sha256") != receipt.get("blend_sha256") or
        receipt.get("video_sha256") != sha(video)):
        raise ValueError("SOURCE_AND_VIDEO_SHA_CUSTODY_MISMATCH")
    frames = witness.get("frames", [])
    ticks = [x["tick"] for x in frames]
    if len(ticks) < 3 or ticks[0] != 0 or any(not isinstance(t,int) for t in ticks) or any(a>=b for a,b in zip(ticks,ticks[1:])):
        raise ValueError("SOURCE_FRAME_CLOCK")
    keys = None
    for frame in frames:
        points = {}
        for pose in frame["poses"]:
            actor,leg = pose["actor"],pose["leg"]
            if leg not in ("Left","Right") or (actor,leg) in points:
                raise ValueError("INVALID_SOURCE_JOINT_COVERAGE")
            vals = sum((pose[n] for n in ("hip","knee","ankle")), [])
            if len(vals) != 9 or not all(isinstance(x,(float,int)) and math.isfinite(x) for x in vals):
                raise ValueError("INVALID_SOURCE_COORDINATES")
            points[(actor,leg)] = tuple(vals)
        if keys is None:
            keys = set(points)
        if not keys or set(points) != keys:
            raise ValueError("SOURCE_JOINT_COVERAGE_CHANGED")
        frame["_points"] = points
    return frames


def analyze(video, witness, native, out):
    width,height,pixels,rate = decode_actual(video)
    source = read_source(witness, video, native)
    if source[-1]["tick"] >= len(pixels):
        raise ValueError("SOURCE_TICK_OUTSIDE_ACTUAL_VIDEO")
    rows = [dict(frame=i, **frame_difference(pixels[i-1],pixels[i]))
            for i in range(1,len(pixels))]
    intervals=[]
    for a,b in zip(source,source[1:]):
        per_joint=[]
        for key in a["_points"]:
            old,new=a["_points"][key],b["_points"][key]
            per_joint.extend(math.dist(old[j:j+3],new[j:j+3]) for j in (0,3,6))
        motion=max(per_joint)
        subset=rows[a["tick"]:b["tick"]]
        # Thresholds are merely research hypotheses, NOT frozen acceptance standards.
        quiet=sum(r["mean_abs_gray"]<0.35 for r in subset)
        intervals.append({"start_frame":a["tick"],"end_frame":b["tick"],
                          "max_source_joint_displacement":round(motion,6),
                          "median_decoded_mean_abs_gray":round(statistics.median(x["mean_abs_gray"] for x in subset),6),
                          "max_decoded_mean_abs_gray":max(x["mean_abs_gray"] for x in subset),
                          "quiet_transition_fraction":round(quiet/len(subset),4),
                          "candidate_motion_pixel_discordance":bool(motion>0.02 and quiet/len(subset)>=0.75)})
    receipt={"schema":"scp.visualqa.w2a_temporal_research.v1",
             "status":"OBSERVED_RESEARCH_ONLY",
             "l1_acceptance":"UNCHANGED_EXTERNAL_FAIL_VETO",
             "anatomical_acceptance":"UNKNOWN_NOT_PERFORMED",
             "human_gait_acceptance":"UNKNOWN_NOT_PERFORMED",
             "source_observation_sha256":sha(witness),
             "video_sha256":sha(video), "source_render_sha256":sha(native),
             "frames_decoded":len(pixels),"width":width,"height":height,"frame_rate":rate,
             "hypothesis_thresholds":{"quiet_mean_abs_gray_lt":0.35,"source_motion_gt":0.02,"quiet_fraction_gte":0.75},
             "per_frame_transition":rows,"source_vs_pixel_intervals":intervals,
             "suspect_intervals":sum(int(x["candidate_motion_pixel_discordance"]) for x in intervals)}
    out=Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":receipt["status"],"frames":len(pixels),"suspect_intervals":receipt["suspect_intervals"]}))
    return receipt


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--video",required=True);p.add_argument("--poses",required=True)
    p.add_argument("--native-receipt",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    analyze(a.video,a.poses,a.native_receipt,a.out)
