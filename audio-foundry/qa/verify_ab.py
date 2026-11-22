#!/usr/bin/env python3
"""Independent PCM A/B technical evidence, not a perceptual listening oracle."""
import argparse
import array
import hashlib
import json
import math
import pathlib
import sys
import wave


def inspect(path):
    path = pathlib.Path(path)
    if path.stat().st_size > 12_000_000:
        raise ValueError(f"{path.name}: WAV exceeds bounded 12 MB input")
    with wave.open(str(path), "rb") as audio:
        rate, channels, width = audio.getframerate(), audio.getnchannels(), audio.getsampwidth()
        frames, compression = audio.getnframes(), audio.getcomptype()
        if (rate, channels, width, compression) != (48000, 2, 2, "NONE"):
            raise ValueError(f"{path.name}: expected uncompressed 48 kHz stereo 16-bit PCM")
        if frames <= 0:
            raise ValueError(f"{path.name}: empty recording")
        raw = audio.readframes(frames)
    samples = array.array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    if len(samples) != frames * channels:
        raise ValueError(f"{path.name}: truncated PCM payload")
    duration = frames / rate
    if not 1 <= duration <= 30:
        raise ValueError(f"{path.name}: unexpected {duration:.3f}s duration")
    peak = max(abs(sample) for sample in samples)
    rms = math.sqrt(sum(float(sample) ** 2 for sample in samples) / len(samples)) / 32768.0
    if peak >= 32767:
        raise ValueError(f"{path.name}: reaches PCM full-scale; potential clipping")
    if rms < 0.0001:
        raise ValueError(f"{path.name}: effectively silent")
    return {"file": path.name, "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sample_rate_hz": rate, "channels": channels, "frames": frames,
            "duration_seconds": duration, "peak_fraction": peak / 32768.0,
            "rms_fraction": rms}, samples


def qualify(before_path, after_path):
    before, x = inspect(before_path)
    after, y = inspect(after_path)
    if len(x) != len(y):
        raise ValueError("A/B mixes have inconsistent PCM duration")
    difference = math.sqrt(sum(float(a - b) ** 2 for a, b in zip(x, y)) / len(x)) / 32768.0
    if difference < 0.0001:
        raise ValueError("A/B sources did not produce a technically distinguishable mix")
    return {"schema": "audio_foundry.ab_signal_receipt.r0", "public_synthetic_only": True,
            "before": before, "after": after, "difference_rms_fraction": difference,
            "technical_signal_check_passed": True,
            "perceptual_acceptance": "NOT_TESTED", "real_device_acceptance": "NOT_TESTED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    result = qualify(args.before, args.after)
    # Atomic, no overwrite: an existing receipt must not be silently replaced.
    with open(args.receipt, "x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, sort_keys=True)
        output.write("\n")
    print("AUDIO_R5_AB_TECHNICAL_PASS", args.receipt)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, wave.Error) as exc:
        print("AUDIO_R5_AB_FIRST_FAILURE:", exc, file=sys.stderr)
        raise SystemExit(1)
