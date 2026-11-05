#!/usr/bin/env python3
"""Check exact source-bound 48f gait events, encoded WAV and AV playback container.

Only proves clock and transport integrity, not physical hoof/sound accuracy.
"""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

def probe_video(path, frames=48):
    obj=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-count_frames","-show_entries",
        "stream=index,codec_type,codec_name,sample_rate,nb_read_frames,width,height:format=duration",
        "-of","json",str(path)],text=True))
    streams=obj["streams"]
    videos=[s for s in streams if s["codec_type"]=="video"]
    audios=[s for s in streams if s["codec_type"]=="audio"]
    if len(videos)!=1 or len(audios)!=1:
        raise ValueError("expected exactly one video and audio stream")
    if int(videos[0].get("nb_read_frames",0))!=frames:
        raise ValueError("wrong number of video frames")
    if videos[0]["codec_name"]!="h264" or audios[0]["codec_name"]!="aac":
        raise ValueError("wrong media codecs")
    if int(audios[0]["sample_rate"])!=48000:
        raise ValueError("wrong audio sample rate")
    if not 1.95 <= float(obj["format"]["duration"]) <= 2.06:
        raise ValueError("wrong video wall-clock duration")
    return obj

def check(events,receipt,wav,source_video,mux):
    g=json.loads(Path(events).read_text())
    a=json.loads(Path(receipt).read_text())
    src=json.loads(Path(source_video).read_text())
    raw=Path(wav).read_bytes()
    if g["schema"]!="equine.contact.v1" or g["basis"]!="SYNTHETIC_PLANNED" or g["evaluation"]!="PLANNED_ONLY_NOT_EVALUATED_HOOF_CONTACT":
        raise ValueError("unadmitted origin")
    if g["gait"]!="walk" or g["frames_per_cycle"]!=48 or g["cycles"]!=1 or g["fps"]!=24 or g["sample_rate"]!=48000:
        raise ValueError("source cycle mismatch")
    footfalls=[(x["frame"],x["foot"],x["sample"]) for x in g["events"]]
    if footfalls!=[(0,"HL",0),(12,"FL",24000),(24,"HR",48000),(36,"FR",72000)]:
        raise ValueError(f"footfall order mismatch: {footfalls}")
    if a["schema"]!="equine.audio.v1" or a["mode"]!="SYNTHETIC_HOOF_FOLEY" or a["biomechanics"]!="UNKNOWN" or a["event_count"]!=4:
        raise ValueError("inaccurate audio provenance claim")
    if raw[:4]!=b"RIFF" or raw[8:12]!=b"WAVE" or struct.unpack_from("<I",raw,24)[0]!=48000:
        raise ValueError("not 48kHz wave")
    if len(raw)!=192044 or hashlib.sha256(raw).hexdigest()!=a["wav_sha256"]:
        raise ValueError("synth source WAV is wrong length/hash")
    if src.get("schema")!="equine.glb.motion.playback.v1" or src.get("source_branch_sha")!="1b0a12da753ad662ec5b21f8d1aad73fba3224d9" or src.get("coat")!="black":
        raise ValueError("wrong independent playback source")
    if src["files"]["shetland_black_walk_2s.mp4"]["sha256"]!="16205b172604ec86c389b7bdc8615ed45b0fb4f9882e5a18f266428386000a99":
        raise ValueError("playback archive is not exact verified source")
    p=Path(mux)
    probe_video(p)
    return {"schema":"equine.av.transport.receipt.v1",
        "verdict":"SOURCE48_SYNTHETIC_AV_CLOCK_PASS_NOT_BIOMECHANICAL_OR_VOCAL_ACCEPTANCE",
        "source_animation_sha256":src["source_sha256"],
        "source_video_sha256":src["files"]["shetland_black_walk_2s.mp4"]["sha256"],
        "source_gait_sha256":hashlib.sha256(Path(events).read_bytes()).hexdigest(),
        "source_audio_sha256":a["wav_sha256"],
        "h264_aac_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
        "duration_sec":2,"source_frames":48,"fps":24,"sample_rate":48000,
        "footfall_frames":[0,12,24,36],"event_basis":"PLANNED_NOT_MEASURED",
        "visual_quality":"UNKNOWN","animal_audio":"SYNTHETIC_FOLEY_NOT_REAL_HORSE"}

if __name__=="__main__":
    if len(sys.argv)!=7:
        raise SystemExit("verify_av.py events.json sound_receipt.json source.wav source_video_receipt.json merged.mp4 out.json")
    report=check(*sys.argv[1:6])
    Path(sys.argv[6]).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
