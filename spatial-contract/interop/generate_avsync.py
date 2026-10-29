"""Synthetic source-only A/V media producer for public CI.

Makes three real independent 10-second(ish) Matroska lossless FFV1+PCM16
files and three H.264/AAC MP4 mobile preview comparators. No person data.
All audio sources have exactly one impulsive click at sample 96000, and
a white video flash on the frame closest to t=2s.
"""
import hashlib
import json
import math
import pathlib
import struct
import subprocess
import sys
import wave

SAMPLE_RATE=48000
CLICK_SAMPLE=96000
WIDTH,HEIGHT=160,90
CASES=(
    ("24", "24", 240, 480000, 48),
    ("30", "30", 300, 480000, 60),
    ("ntsc", "30000/1001", 300, 480480, 60),
)
def run(*args):
    r=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=90)
    if r.returncode:
        raise RuntimeError("FIRST_FAILURE command "+repr(args)+"\n"+r.stderr[-3000:])
    return r.stdout
def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def synth_wav(path,frames):
    data=bytearray(frames*2)
    struct.pack_into("<h",data,CLICK_SAMPLE*2,20000)
    with wave.open(str(path),"wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(data)
def main(root):
    root=pathlib.Path(root)
    root.mkdir(parents=True,exist_ok=False)
    metadata={"schema":"spatial_audio.avsync_native_fixture.v1",
              "rights":"ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC",
              "sample_rate":SAMPLE_RATE,"width":WIDTH,"height":HEIGHT,
              "click_sample":CLICK_SAMPLE,
              "ffmpeg_version":run("ffmpeg","-version").splitlines()[0],
              "ffprobe_version":run("ffprobe","-version").splitlines()[0],
              "cases":[]}
    for name,rate,video_frames,audio_frames,flash_frame in CASES:
        orig=root/f"{name}.wav"
        video=root/f"{name}_video.mkv"
        master=root/f"{name}_master.mkv"
        mobile=root/f"{name}_mobile.mp4"
        synth_wav(orig,audio_frames)
        draw=f"drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='eq(n,{flash_frame})'"
        run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-f","lavfi","-i",f"color=c=black:s={WIDTH}x{HEIGHT}:r={rate}",
            "-vf",draw,"-frames:v",str(video_frames),"-c:v","ffv1",
            "-level","3",str(video))
        run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-i",str(video),"-i",str(orig),"-map","0:v:0","-map","1:a:0",
            "-c:v","copy","-c:a","pcm_s16le","-avoid_negative_ts","disabled",
            str(master))
        # Container H264/AAC is an independent delivery candidate. Its
        # codec delay is measured separately; it is NOT the lossless oracle.
        run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-i",str(master),"-map","0:v:0","-map","0:a:0",
            "-c:v","libx264","-preset","ultrafast","-crf","25",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","96k",
            "-movflags","+faststart",str(mobile))
        metadata["cases"].append({"id":name,"rate":rate,"video_frames":video_frames,
              "audio_frames":audio_frames,"flash_frame":flash_frame,
              "original_pcm_wav_sha256":sha(orig),
              "lossless_master_sha256":sha(master),
              "mobile_preview_sha256":sha(mobile),
              "lossless_master":master.name,"mobile_preview":mobile.name})
        print("AVSYNC_NATIVE_MEDIA_GENERATED",name,
              "frames",video_frames,"samples",audio_frames,flush=True)
    (root/"native_source_manifest.json").write_text(json.dumps(metadata,sort_keys=True,indent=2)+"\n")
    print("AVSYNC_NATIVE_THREE_LOSSLESS_PLUS_MOBILE_COMPLETE",flush=True)
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: generate_avsync.py OUTPUT_NEW_DIR")
    main(sys.argv[1])
