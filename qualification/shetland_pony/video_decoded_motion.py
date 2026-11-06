#!/usr/bin/env python3
"""Independent source-bound decoded-video motion screen for public synthetic Shetland.

Decode exact MP4 bytes with ffmpeg and count actual image variation; a producer's
declared unique PNG hashes are not a substitute. Synthetic diagnostic only,
not equine gait, hoof-floor contact, anatomy, or human/animal visual acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

VIEWS=("side","face","mane","tail")
W,H,FRAMES,FPS=160,105,48,24
MAX_MP4_BYTES=10*1024*1024

class InvalidEvidence(ValueError): pass

def require(condition,error):
    if not condition:raise InvalidEvidence(error)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def run_bounded(cmd,max_bytes):
    try:result=subprocess.run(cmd,capture_output=True,timeout=40,check=False)
    except (OSError,subprocess.TimeoutExpired) as error:
        raise InvalidEvidence("decoder unavailable or timed out") from error
    require(result.returncode==0 and len(result.stdout)<=max_bytes,
            "decoder failed or exceeded byte budget")
    return result.stdout

def max_freeze(hashes):
    current=1;largest=1
    for prev,cur in zip(hashes,hashes[1:]):
        current=current+1 if prev==cur else 1
        largest=max(largest,current)
    return largest

def observe_bytes(frames):
    """Decoder-neutral bounded 160x105 grayscale sequence for hostile tests."""
    require(type(frames) is list and len(frames)==FRAMES,"wrong observed frame count")
    require(all(type(f) is bytes and len(f)==W*H for f in frames),
            "wrong decoded frame geometry")
    hashes=[sha(f) for f in frames]
    consecutive=[sum(abs(x-y) for x,y in zip(a,b))/(W*H)
                 for a,b in zip(frames,frames[1:])]
    require(all(math.isfinite(x) for x in consecutive),"nonfinite observed motion")
    mean=sum(consecutive)/len(consecutive)
    return {"decoded_frames":FRAMES,
            "unique_decoded_frame_shas":len(set(hashes)),
            "mean_frame_delta_luma":round(mean,8),
            "max_frame_delta_luma":round(max(consecutive),8),
            "longest_exact_freeze_run":max_freeze(hashes),
            "frames_with_luma_delta_over_1":sum(x>1 for x in consecutive),
            "frames_with_luma_delta_over_half":sum(x>0.5 for x in consecutive),
            "first_gray_sha256":hashes[0],"last_gray_sha256":hashes[-1],
            "technical_motion_observed":(len(set(hashes))>=8 and
                max_freeze(hashes)<36 and mean>=0.25
                and sum(x>0.5 for x in consecutive)>=8)}

def inspect(root):
    root=Path(root)
    meta=json.loads((root/"diagnostic_video_receipt.json").read_text())
    render=json.loads((root/"diagnostic_frames_receipt.json").read_text())
    require(meta.get("schema")=="equine.motion.mp4.custody.v1","wrong source receipt")
    require(render.get("schema")=="equine.motion.fourviews.v1","wrong frame receipt")
    require(meta.get("source_sha256")==render.get("source_sha256"),"source model SHA drift")
    require(set(meta.get("videos",{}))=={v+".mp4" for v in VIEWS},
            "unexpected video membership")
    require(set(render.get("views",{}))==set(VIEWS),"incomplete view membership")
    report={}
    for view in VIEWS:
        vfile=root/(view+".mp4")
        require(vfile.is_file() and not vfile.is_symlink(),"missing or linked video")
        raw=vfile.read_bytes()
        require(200<len(raw)<=MAX_MP4_BYTES,"invalid video byte budget")
        claimed=meta["videos"][view+".mp4"]
        require(claimed.get("bytes")==len(raw) and claimed.get("sha256")==sha(raw),
                "original video changed")
        require(claimed.get("decoded_frames")==FRAMES and
                claimed.get("source_render_unique_frames")==FRAMES,
                "source video declared frame mismatch")
        info=run_bounded(["ffprobe","-v","error","-select_streams","v:0",
                          "-count_frames","-show_entries",
                          "stream=width,height,nb_read_frames,r_frame_rate",
                          "-of","json",str(vfile)],4096)
        streams=json.loads(info).get("streams",[])
        require(len(streams)==1 and streams[0].get("width")==640 and
                streams[0].get("height")==420 and
                streams[0].get("nb_read_frames")==str(FRAMES) and
                streams[0].get("r_frame_rate")=="24/1",
                "wrong actual video dimensions, source clock or count")
        decoded=run_bounded(["ffmpeg","-nostdin","-v","error","-i",str(vfile),
                             "-vf",f"scale={W}:{H}:flags=area,format=gray",
                             "-pix_fmt","gray","-f","rawvideo","-"],W*H*FRAMES+1)
        require(len(decoded)==W*H*FRAMES,"actual decoded bytes wrong")
        measure=observe_bytes([decoded[i*W*H:(i+1)*W*H] for i in range(FRAMES)])
        measure["original_mp4_sha256"]=sha(raw)
        measure["source_view_frame_count"]=render["views"][view]["frames"]
        report[view]=measure
    return {"schema":"equine.motion.decoded_temporal.v1",
            "source_sha256":meta["source_sha256"],"view_evidence":report,
            "decoded_video_motion":"TECHNICAL_VARIATION_OBSERVED" if all(
                 r["technical_motion_observed"] for r in report.values())
                 else "FAIL_STATIC_OR_FROZEN_VIEW",
            "gait_hoof_contact":"NOT_QUALIFIED",
            "hair_dynamics_realism":"NOT_QUALIFIED",
            "eye_halter_anatomy":"NOT_QUALIFIED",
            "model_mutation":False,"visual_acceptance":False,
            "release_or_CPE_admission":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    parser.add_argument("--out",required=True)
    opts=parser.parse_args()
    path=Path(opts.out)
    require(not path.exists(),"refuse overwrite evidence")
    result=inspect(opts.source)
    path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("EQUINE_DECODED_VIDEO_MOTION_DIAGNOSTIC_ONLY",result["decoded_video_motion"])

if __name__=="__main__":main()
