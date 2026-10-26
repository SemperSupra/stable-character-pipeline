#!/usr/bin/env python3
"""Optional Kokoro ONNX CPU provider. Public synthetic research ONLY.

The Audio Foundry Go core owns orchestration, custody, and scene timelines.
This worker speaks original generic lines into private temp output; do not
pass real-person references or final human character audio into public CI.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import wave

MODEL_SHA = "ae315a79b623f244700e4afb9246c46a26066782e049ba174bf3ba433970ee9c"
VOICES_SHA = "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"
RELEASE = "thewh1teagle/kokoro-onnx:model-files-v1.1"
MODEL_FILE = "kokoro-v1.0.int8.onnx"
VOICE_FILE = "voices-v1.0.bin"
CLASSIFICATION = "PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL"
SAMPLES = (
    ("human", "af_sarah", "A gentle breeze passes through the imaginary forest."),
    ("computer", "am_adam", "Environmental sensors online. All systems nominal."),
)

def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()

def verify_files(model_dir: Path) -> None:
    for name, expected in ((MODEL_FILE, MODEL_SHA), (VOICE_FILE, VOICES_SHA)):
        path = model_dir / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("missing or symlinked model: " + name)
        observed = digest(path)
        if observed != expected:
            raise ValueError(f"model digest failed: {name}; observed {observed}")

def wave_stats(path: Path) -> dict:
    with wave.open(str(path), "rb") as f:
        rate, channels, frames = f.getframerate(), f.getnchannels(), f.getnframes()
        if f.getsampwidth() != 2 or channels != 1 or rate != 24000 or frames < 2400:
            raise ValueError(f"unexpected WAV format or empty audio: {path.name}")
    return {"sample_rate_hz": rate, "channels": channels, "duration_seconds": round(frames / rate, 3), "sha256": digest(path), "bytes": path.stat().st_size}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    verify_files(args.models)
    if args.verify_only:
        print(json.dumps({"model_sha256": MODEL_SHA, "voice_style_sha256": VOICES_SHA, "verified": True}))
        return
    if args.out is None:
        parser.error("--out is required unless --verify-only is set")
    if args.out.exists():
        raise ValueError("refusing existing output directory")
    args.out.mkdir(parents=True, mode=0o700)
    from kokoro_onnx import Kokoro
    import numpy as np
    import soundfile as sf
    engine = Kokoro(str(args.models / MODEL_FILE), str(args.models / VOICE_FILE))
    receipts = []
    for label, voice, text in SAMPLES:
        samples, rate = engine.create(text, voice=voice, speed=1.0, lang="en-us")
        samples = np.asarray(samples, dtype=np.float32)
        if rate != 24000 or samples.ndim != 1 or samples.size < 2400 or not np.all(np.isfinite(samples)):
            raise ValueError("invalid or silent inference waveform shape/sample rate")
        peak = float(np.max(np.abs(samples)))
        rms = float(np.sqrt(np.mean(samples * samples)))
        if peak > 1.01 or rms < 0.0001 or not math.isfinite(peak):
            raise ValueError("bad waveform levels")
        target = args.out / f"{label}_kokoro.wav"
        with target.open("xb") as f:
            sf.write(f, samples, rate, subtype="PCM_16", format="WAV")
        stats = wave_stats(target)
        receipts.append({"type": label, "voice": voice, "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "rms": round(rms, 6), "peak": round(peak, 6), **stats})
    record = {"schema": "audio_foundry.kokoro_cpu.v1", "classification": CLASSIFICATION, "engine": "kokoro-onnx", "package_version": "0.6.1", "source_release": RELEASE, "model_sha256": MODEL_SHA, "voice_style_sha256": VOICES_SHA, "voices": receipts}
    (args.out / "receipt.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("kokoro_cpu_PASS", json.dumps({"voices": [(x["type"], x["sha256"], x["duration_seconds"]) for x in receipts], "classification": CLASSIFICATION}))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("KOKORO_FIRST_FAILURE:", str(exc), file=sys.stderr)
        raise SystemExit(1)
