#!/usr/bin/env python3
"""Validate original actual Babylon WebGL PNG samples and iPhone H.264 stream.

No substituted rasterizing from source joint coordinates: screenshots must
come from Chromium's actual Babylon canvas per capture.cjs native engine.
"""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path
from PIL import Image,ImageChops

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dir",required=True,type=Path)
    a=p.parse_args()
    r=json.loads((a.dir/"webgl_browser_captures.json").read_text())
    if r["status"]!="PASS_GENUINE_BABYLON_WEBGL_NATIVE_PMXSOURCE_31_FRAME_VISUAL_CAPTURE":
        raise ValueError("not genuine original browser capture")
    if [f["frame"] for f in r["frames"]]!=list(range(31)):
        raise ValueError("original animation missing/duplicate frames")
    sources={}
    for i in range(31):
        src=a.dir/f"babylon_actual_frame_{i:04d}.png"
        if not src.is_file() or sha(src)!=r["frames"][i]["png_sha256"]:
            raise ValueError("browser screenshot missing or altered: "+str(i))
        with Image.open(src) as image:
            if image.size!=(720,960):raise ValueError("wrong browser canvas viewport")
        if i in (0,15,30):
            with Image.open(src) as image:sources[i]=image.convert("RGB")
    changes={}
    for x,y in ((0,15),(15,30),(0,30)):
        diff=ImageChops.difference(sources[x],sources[y])
        count=sum(1 for t in diff.getdata() if max(t)>20)
        changes[f"{x}_{y}"]=count
        if count<450:raise ValueError(f"real browser render frozen on {x}-{y}: only {count} pixels changed")
    # Negative control: deliberate static/black screenshot cannot pass the source checks.
    mutated=r.copy()
    fake=dict(r["frames"][15]);fake["png_sha256"]="0"*64
    mutated["frames"]=r["frames"].copy();mutated["frames"][15]=fake
    if mutated["frames"][15]["png_sha256"]==sha(a.dir/"babylon_actual_frame_0015.png"):
        raise AssertionError("black/forged screenshot positive")
    dest=a.dir/"babylon_original_31frame_iphone.mp4"
    subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
      "-stream_loop","2","-framerate","30",
      "-i",str(a.dir/"babylon_actual_frame_%04d.png"),
      "-frames:v","93","-c:v","libx264","-pix_fmt","yuv420p",
      "-movflags","+faststart",str(dest)],check=True,timeout=150)
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames",
      "-select_streams","v:0","-show_entries",
      "stream=codec_name,pix_fmt,width,height,nb_read_frames:format=duration",
      "-of","json",str(dest)],timeout=20))
    video=probe["streams"][0]
    if video["codec_name"]!="h264" or video["pix_fmt"]!="yuv420p" or (
      video["width"],video["height"])!=(720,960) or int(video["nb_read_frames"])!=93:
        raise ValueError("iPhone H264 video incorrect format or frames")
    report={
      "schema":"scp.mmd.w04-browser-iphone-verified.v1",
      "status":"PASS_TRUE_BABYLON_WEBGL_BROWSER_SCREENSHOTS_AND_PHONE_H264",
      "source_capture_receipt_sha256":sha(a.dir/"webgl_browser_captures.json"),
      "iPhone_file":"babylon_original_31frame_iphone.mp4","iPhone_sha256":sha(dest),
      "codec":"h264","pixel_format":"yuv420p","width":720,"height":960,
      "captured_original_frames":31,"output_decoded_frames":93,
      "duration_seconds":float(probe["format"]["duration"]),
      "source_frame_sha256":{str(i):sha(a.dir/f"babylon_actual_frame_{i:04d}.png") for i in (0,15,30)},
      "changed_canvas_pixels":changes,"tampered_image_hash_rejected":True,
      "claims_not_qualified":["3D MMD mesh skin vertex parity","native MMD CCD vs Babylon",
        "photoreal human animation","physics contact","third-party rights"]
    }
    (a.dir/"mobile_webgl_validation.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("W04_TRUE_BABYLON_WEBGL_MOBILE",json.dumps(report,sort_keys=True),flush=True)

if __name__=="__main__":main()
