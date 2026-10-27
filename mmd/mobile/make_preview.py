#!/usr/bin/env python3
"""W21 phone-visible media from exact ORIGINAL synthetic Blender/GHA outputs.

Never invent missing in-between mesh samples: 3 actual 3D source keyframes
become a frame-hold video, not a fake continuous pose trajectory.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(cmd):
    subprocess.run(cmd,check=True,timeout=90)

def main():
    p=argparse.ArgumentParser()
    for x in ("g4","g7","g9","out"):
        p.add_argument("--"+x,required=True,type=Path)
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    expected=[
       a.g4/"mmd_animated_interchange.mp4",
       *[a.g7/f"articulation_{n:04}.png" for n in (0,15,30)],
       *[a.g9/f"morph_{n:04}.png" for n in (0,15,30)]
    ]
    for f in expected:
        if not f.is_file() or f.stat().st_size==0:raise ValueError(f"missing actual source image/video: {f}")
    try:
        font="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        h=ImageFont.truetype(font,40); small=ImageFont.truetype(font,24)
    except OSError:
        h=ImageFont.load_default(); small=h
    imgs=[]
    for i,n in enumerate((0,15,30)):
        frame=Image.new("RGB",(1080,1920),(16,21,32))
        d=ImageDraw.Draw(frame)
        d.text((75,90),"MMD / ORIGINAL RENDER EVIDENCE",font=h,fill=(232,239,250))
        d.text((75,165),"Self-authored geometry  |  real Blender frames",font=small,fill=(171,192,215))
        for title,source,y in [
            ("G7 / ARTICULATED RIBBON",a.g7/f"articulation_{n:04}.png",290),
            ("G9 / VERTEX MORPH GRID",a.g9/f"morph_{n:04}.png",960)
        ]:
            d.rounded_rectangle((60,y-40,1020,y+610),radius=22,fill=(29,38,53))
            d.text((90,y),title,font=small,fill=(226,237,250))
            with Image.open(source) as raw:
                sample=raw.convert("RGB")
            sample.thumbnail((780,530),Image.Resampling.LANCZOS)
            frame.paste(sample,((1080-sample.width)//2,y+60+(530-sample.height)//2))
        d.text((75,1650),f"ACTUAL SOURCE FRAME {n} / 30  -  {n/30:.2f} s",font=small,fill=(232,239,250))
        d.text((75,1715),"Frame-hold slideshow: only 3 genuinely rendered keyframes",font=small,fill=(171,192,215))
        d.text((75,1775),"No interpolated pose, photo identity or community assets",font=small,fill=(171,192,215))
        fn=a.out/f"phoneframe_{i:03d}.png"
        frame.save(fn)
        imgs.append(fn)
    original=a.g4/"mmd_animated_interchange.mp4"
    continuous=a.out/"original_31frames_looped_iphone.mp4"
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-stream_loop","2","-i",str(original),
        "-vf","scale=960:720:flags=lanczos","-c:v","libx264","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(continuous)])
    storyboard=a.out/"g7_g9_real_keyframe_slideshow_iphone.mp4"
    run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate","1/2",
        "-i",str(a.out/"phoneframe_%03d.png"),"-vf","fps=24,format=yuv420p",
        "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(storyboard)])
    details=[]
    for file in (continuous,storyboard):
        doc=json.loads(subprocess.check_output([
            "ffprobe","-v","error","-show_entries","stream=codec_name,pix_fmt,width,height,nb_frames:format=duration",
            "-of","json",str(file)],timeout=30))
        stream=doc["streams"][0]
        assert stream["codec_name"]=="h264" and stream["pix_fmt"]=="yuv420p"
        assert stream["width"]%2==0 and stream["height"]%2==0 and int(stream["nb_frames"])>=31
        details.append({"name":file.name,"source_sha256":sha(file),"codec":"h264",
            "pixel_format":"yuv420p","width":stream["width"],"height":stream["height"],
            "decoded_frames":int(stream["nb_frames"]),"duration_s":float(doc["format"]["duration"])})
    receipt={"schema":"scp.mmd.w21-mobile-capture.v1",
      "status":"PASS_PHONE_COMPATIBLE_H264_FROM_GENUINE_SOURCE_RENDER_BYTES",
      "media":details,"input_source_sha256":{f.name:sha(f) for f in expected},
      "limits":["original_31frames_looped_iphone.mp4 repeats actual 31 rendered frames 3 times",
        "g7_g9_real_keyframe_slideshow_iphone.mp4 holds only actual 0/15/30 renders",
        "not third-engine MMD physics or humanoid character evidence",
        "provenance is original, rights-clean G4/G7/G9 GHA runner artifact, not a published release"]}
    (a.out/"mobile_capture_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("W21_MOBILE_PREVIEW",json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    main()
