#!/usr/bin/env python3
"""Independent libVLC original-audio callback oracle. Full bytes, no trimming."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

FRAMES = 16384
RATE = 48000
EXPECTED_SHA = "155cd0c71c1743bfb2ff90fe36288b354f766f89da4ebcd8adc9febe456b9d39"
EVENTS = {0: 12000, 4096: 15000, 8192: 10000}

def source_original():
    return b"".join(struct.pack("<h", EVENTS.get(i, 0)) for i in range(FRAMES))

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def require(test, code):
    if not test:
        raise ValueError(code)

def audit(root):
    root = Path(root)
    original = source_original()
    require(sha(original) == EXPECTED_SHA, "FROZEN_SOURCE_SHA_MISMATCH")
    reported_source = (root / "source_s16le.raw").read_bytes()
    require(reported_source == original, "NATIVE_SOURCE_NOT_B3_ORIGINAL")
    wav = (root / "source.wav").read_bytes()
    require(len(wav) == 44 + len(original), "WAV_LENGTH")
    require(wav[:4] == b"RIFF" and wav[8:16] == b"WAVEfmt ", "WAV_HEADER")
    require(struct.unpack_from("<I", wav, 4)[0] == len(wav)-8, "WAV_RIFF_SIZE")
    require(struct.unpack_from("<IHHIIHH", wav, 16) == (16,1,1,RATE,RATE*2,2,16),
            "WAV_FORMAT_MISMATCH")
    require(wav[36:40] == b"data" and struct.unpack_from("<I", wav, 40)[0] == len(original),
            "WAV_DATA_HEADER")
    require(wav[44:] == original, "WAV_PCM_NOT_ORIGINAL")
    info = json.loads((root / "native_observation.json").read_text(encoding="utf-8"))
    require(info.get("schema") == "scp.libvlc_callback_native.v1", "NATIVE_RECEIPT_SCHEMA")
    require(info.get("sample_rate") == RATE and info.get("channels") == 1
            and info.get("sample_format") == "S16N", "CALLBACK_FORMAT_MISMATCH")
    require(info.get("overflow") is False, "CALLBACK_OVERFLOW")
    require(info.get("status") == "ENDED", "NATIVE_PLAYBACK_NOT_ENDED")
    callback = (root / "callback_s16le.raw").read_bytes()
    require(type(info.get("callback_frames")) is int
            and info["callback_frames"] * 2 == len(callback), "CALLBACK_RECEIPT_COUNT")
    require(type(info.get("chunks")) is int and info["chunks"] >= 1, "NO_REAL_CALLBACK")
    require(len(callback) == len(original), "CALLBACK_FULL_LENGTH_MISMATCH")
    require(callback == original, "CALLBACK_PCM_DIFFERENT_FROM_SOURCE")
    for k in ("flushes", "drains", "pauses", "resumes", "first_pts", "last_pts"):
        require(type(info.get(k)) is int, "CALLBACK_EVENT_FIELD_" + k)
    require(info.get("exact_source_copy_claim") is False
            and info.get("physical_latency_claim") is False, "UNAUTHORIZED_NATIVE_CLAIM")
    ver = (root / "native_libvlc_version.txt").read_text(encoding="utf-8").strip()
    require(ver and "\n" not in ver and "\r" not in ver, "NO_LIBVLC_VERSION")
    return dict(schema="scp.libvlc_original_independent_pcm.v1",
                status="PASS_FULL_EXACT_SOURCE_COPY_CALLBACK_ONLY",
                original_source_sha256=EXPECTED_SHA, native_input_sha256=sha(reported_source),
                native_callback_sha256=sha(callback), frames=FRAMES,
                rate_hz=RATE, callback_chunks=info["chunks"],
                flushes=info["flushes"], drains=info["drains"],
                libvlc_version=ver, rights="ORIGINAL_SELF_AUTHORED_SYNTHETIC",
                no_claim=["PHYSICAL_DELAY","HRTF_EQUIVALENCE","GENERAL_CODEC_CORRECTNESS",
                          "SPATIAL_PERCEPTION","R009_PERSON_PRODUCT_ACCEPTANCE",
                          "UNIVERSAL_OUTPUT_LATENCY","REAL_FOOTSTEP_EVENTS"])

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("receipt")
    args = p.parse_args()
    try:
        result = audit(args.root)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        result = {"schema":"scp.libvlc_original_independent_pcm.v1",
                  "status":"FAIL", "first_failure":str(exc),
                  "original_source_sha256":EXPECTED_SHA,
                  "no_promotion":True}
        Path(args.receipt).write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")
        raise SystemExit("W4L_LIBVLC_FIRST_FAILURE " + str(exc))
    Path(args.receipt).write_text(json.dumps(result, sort_keys=True, indent=2)+"\n")
    print("W4L_LIBVLC_INDEPENDENT_FULL_PCM_PASS", EXPECTED_SHA)
