#!/usr/bin/env python3
"""R064 independent bounded follow-on: source-clean critic challenge / veto.

Reuses unchanged R063 original synthetic fixtures + actual model loading.
Never calls a private asset or publishes output media.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback
import wave

BASE = Path(__file__).resolve().parents[1] / "r063-critic-interview" / "interview.py"
VIDEO_500_MODEL = "HuggingFaceTB/SmolVLM2-500M-Video-Instruct"
VIDEO_500_SHA = "5761ea844d66ecc658ae4fa88d0ba22b151f4131"

def base():
    spec = importlib.util.spec_from_file_location("r063_original", BASE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def rms16(path):
    import numpy as np
    with wave.open(str(path), "rb") as w:
        if w.getframerate() != 16000 or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError("unqualified audio format")
        data = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float64") / 32768.0
    if len(data) == 0:
        raise ValueError("zero-length WAV")
    return math.sqrt(float((data*data).mean()))

def audio_guard_lane(m, output):
    # Make the unchanged original Whisper probe run first for matched evidence.
    raw = m.audio_lane(output)
    if [r["fixture"] for r in raw] != ["left", "silence"]:
        raise RuntimeError("unexpected original-audio receipt")
    voice_rms = rms16(output / "voice16.wav")
    silence_rms = rms16(output / "silence16.wav")
    if not (voice_rms > 0.003 and silence_rms == 0.0):
        raise RuntimeError("required original source and silence energy witness absent")
    # Predeclared fail-closed policy: digital silence must bypass ASR and return
    # NO_SPEECH. Preserve, do not erase, the model's actual hallucinated output.
    # Low-level noise is deliberately classified ABSTAIN, not proven no-speech.
    guard_threshold = 0.003
    composed = []
    for r, energy in zip(raw, (voice_rms, silence_rms)):
        raw_text = r["raw"]
        decision = ("NO_SPEECH" if energy == 0.0 else
                    "ABSTAIN_QUIET" if energy < guard_threshold else
                    "TRANSCRIPT_" + raw_text)
        intended = "NO_SPEECH" if r["fixture"] == "silence" else "TRANSCRIPT_LEFT"
        passed = (decision == "NO_SPEECH" if r["fixture"] == "silence"
                  else "left" in raw_text.lower().replace(".", " ").replace("!", " ").replace("?", " ").split())
        composed.append({
            "fixture": r["fixture"], "fixture_sha256": r["sha256"],
            "raw_whisper_text": raw_text, "raw_whisper_passed": r["passed"],
            "rms": round(energy, 9), "threshold": guard_threshold,
            "guarded_decision": decision, "intended": intended,
            "passed": passed
        })
    # Silence is one special case, not a generic VAD or validated acoustic
    # classification in noise/music/breathing/whistling environments.
    return composed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", required=True, choices=["video-500m", "audio-guard"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    module = base()
    start = time.monotonic()
    receipt = {
        "schema": "scp.r064.critic-adaptation.v1",
        "lane": args.lane, "source_sha": os.getenv("GITHUB_SHA", "NOT_GHA"),
        "status": "UNKNOWN", "negative_controls": [],
        "first_failure": None, "executed": False,
        "private_inputs": False, "publication": False,
        "model_accepted": False, "product_accepted": False,
        "source_class": "ORIGINAL_SYNTHETIC_ONLY",
    }
    try:
        if args.lane == "video-500m":
            module.VISION_MODEL = VIDEO_500_MODEL
            module.VISION_REV = VIDEO_500_SHA
            receipt["model"] = VIDEO_500_MODEL
            receipt["model_revision"] = VIDEO_500_SHA
            records = module.visual_lane(output, video=True)
            receipt["status"] = "PASS_NARROW_SYNTHETIC_ONLY" if all(r["passed"] for r in records) else "FAIL_CONTROLS"
        else:
            receipt["model"] = module.AUDIO_MODEL
            receipt["model_revision"] = module.AUDIO_REV
            records = audio_guard_lane(module, output)
            receipt["raw_whisper_negative_failure_preserved"] = not records[1]["raw_whisper_passed"]
            receipt["status"] = "PASS_NARROW_COMPOSITE_ONLY" if all(r["passed"] for r in records) else "FAIL_CONTROLS"
        receipt["negative_controls"] = records
        receipt["executed"] = True
        if receipt["status"] == "FAIL_CONTROLS":
            receipt["first_failure"] = next(r["fixture"] for r in records if not r["passed"])
    except Exception as e:
        receipt["first_failure"] = type(e).__name__ + ": " + str(e)[:450]
        receipt["status"] = "ERROR_RUNTIME"
        traceback.print_exc()
    receipt["elapsed_seconds"] = round(time.monotonic()-start, 2)
    data = json.dumps(receipt, sort_keys=True).encode()
    receipt["receipt_sha256_without_self_hash"] = hashlib.sha256(data).hexdigest()
    (output/"r064-receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print("R064_CRITIC_ADAPTATION",json.dumps(receipt,sort_keys=True))
    return 0 if receipt["status"].startswith("PASS_NARROW") else 12

if __name__ == "__main__":
    sys.exit(main())
