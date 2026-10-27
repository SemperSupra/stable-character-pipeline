#!/usr/bin/env python3
"""CI-only structural/signal checks for independently rendered public test material.
Not the production Audio Foundry engine; no network, third-party dependencies, uploads.
"""
import hashlib
import json
import math
import pathlib
import struct
import subprocess
import sys

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def wav(directory):
    files=sorted(pathlib.Path(directory).glob("*.wav"))
    if not files:
        raise RuntimeError("headless render did not create any WAV stems")
    audible=0
    for path in files:
        p=subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=codec_name,sample_rate,channels","-show_entries","format=duration","-of","json",str(path)],check=True,capture_output=True,text=True)
        data=json.loads(p.stdout)
        streams=data.get("streams",[])
        duration=float(data["format"]["duration"])
        if len(streams)!=1 or streams[0].get("sample_rate")!="48000" or duration<0.1 or duration>600:
            raise RuntimeError("invalid audio render "+path.name)
        if streams[0].get("channels",0)<1 or streams[0].get("channels",0)>2:
            raise RuntimeError("unexpected channel layout "+path.name)
        if path.stat().st_size<4096:
            raise RuntimeError("truncated stem "+path.name)
        check=subprocess.run(["ffmpeg","-hide_banner","-nostdin","-v","error","-xerror","-i",str(path),"-f","null","-"],capture_output=True,text=True)
        if check.returncode:
            raise RuntimeError("undecodable stem "+path.name+": "+check.stderr[:180])
        import wave
        # Detect actual samples if PCM; for all other valid codecs, ffmpeg verifies decode.
        if streams[0]["codec_name"].startswith("pcm_s16"):
            with wave.open(str(path),"rb") as w:
                raw=w.readframes(min(32000,w.getnframes()))
                if any(raw):audible+=1
        else:
            loud=subprocess.run(["ffmpeg","-nostdin","-hide_banner","-i",str(path),"-af","volumedetect","-f","null","-"],capture_output=True,text=True,check=True)
            if "mean_volume: -" in loud.stderr and "mean_volume: -inf" not in loud.stderr:
                audible+=1
        print("lmms_stem",path.name,"seconds",round(duration,3),"sha256",sha256(path))
    if audible==0:raise RuntimeError("all rendered tracks are silent")
    print(f"headless_wav_qualification_PASS stems={len(files)} audible={audible}")

def midi(path):
    p=pathlib.Path(path)
    raw=p.read_bytes()
    if len(raw)<30 or raw[:4]!=b"MThd":
        raise RuntimeError("MIDI header missing")
    header=struct.unpack(">I",raw[4:8])[0]
    if header!=6:raise RuntimeError("nonstandard MIDI header length")
    fmt,ntracks,division=struct.unpack(">HHH",raw[8:14])
    if fmt not in (0,1) or ntracks<1 or division==0:
        raise RuntimeError("invalid MIDI timing/tracks")
    p0=14
    for _ in range(ntracks):
        if raw[p0:p0+4]!=b"MTrk" or p0+8>len(raw):
            raise RuntimeError("MIDI track missing")
        length=struct.unpack(">I",raw[p0+4:p0+8])[0]
        p0+=8+length
        if p0>len(raw):raise RuntimeError("truncated MIDI track")
    print("musescore_midi_PASS",json.dumps({"format":fmt,"tracks":ntracks,"division":division,"bytes":len(raw),"sha256":sha256(p)}))

if __name__=="__main__":
    if len(sys.argv)!=3 or sys.argv[1] not in {"wav","midi"}:
        sys.exit("usage: verify.py wav DIR | midi FILE")
    try:
        {"wav":wav,"midi":midi}[sys.argv[1]](sys.argv[2])
    except Exception as e:
        sys.exit("HEADLESS_FIRST_FAILURE: "+str(e))
