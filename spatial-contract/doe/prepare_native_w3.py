"""W3c W3 rights-clean source variants; same Go DOE, frame clock and immutable bytes.

Original 410Hz fixture is inherited, not regenerated. 930Hz and deterministic
impulse+noise burst are independently regenerated on both public workers.
"""
import hashlib
import json
import math
import struct
import sys
import wave
from pathlib import Path

RATE = 48000
BLOCK = 1024
CASE_BLOCKS = 47
UPSTREAM_EBU = "2db69f8fcea0bc5db8a78e14a9c2ae6ed4283c15"
UPSTREAM_VLC = "d149ed9744fd399b835c6f2920511f8cbcfce5ea"
RIGHTS = "ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def samples(kind, count):
    for i in range(count):
        if kind == "sine_930":
            value = .15 * math.sin(2 * math.pi * 930 * i / RATE)
        elif kind == "impulse_burst":
            local = i % (BLOCK * CASE_BLOCKS)
            case = i // (BLOCK * CASE_BLOCKS)
            # Explicit case-local deterministic PRNG, no random module drift.
            value = .4 if local == 0 else 0
            if 1 <= local < BLOCK:
                state = (0x9E3779B9 ^ (case * 1315423911) ^ local) & 0xffffffff
                state ^= (state << 13) & 0xffffffff
                state ^= state >> 17
                state ^= (state << 5) & 0xffffffff
                value = .07 * ((state / 4294967295) * 2 - 1)
        else:
            raise ValueError("unsupported source")
        yield int(round(32767 * value))

def create(root, name, n):
    path = root / (name + ".wav")
    # No overwrite, including symlink; native adapter enforces canonical RIFF.
    with path.open("xb") as f:
        with wave.open(f, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            chunk = bytearray()
            for s in samples(name, n):
                chunk.extend(struct.pack("<h", s))
                if len(chunk) >= 32768:
                    w.writeframesraw(chunk)
                    chunk.clear()
            if chunk:
                w.writeframesraw(chunk)
    with wave.open(str(path), "rb") as w:
        if (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) != (1, 2, RATE, n):
            raise ValueError("incomplete canonical source")
    return sha(path)

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_native_w3.py NATIVE_DIR")
    root = Path(sys.argv[1])
    first = json.loads((root / "source_manifest.json").read_text())
    doe = json.loads((root / "original_doe.json").read_text())
    if (doe["schema"] != "spatial_audio.offaxis_doe.v1"
        or len(doe["cases"]) != 42
        or first["classification"] != RIGHTS
        or first["rate"] != RATE
        or first["channels"] != 1
        or first["blocks_per_case"] != CASE_BLOCKS
        or first["frames"] != 42 * CASE_BLOCKS * BLOCK
        or first["upstream_libear"] != UPSTREAM_EBU
        or first["upstream_videolan"] != UPSTREAM_VLC
        or first["doe_sha256"] != sha(root / "original_doe.json")
        or first["source_wav_sha256"] != sha(root / "original_410hz.wav")
        or first["case_table_sha256"] != sha(root / "w3c_cases.tsv")):
        raise ValueError("W3 custody, pin or timebase drift")
    variants = {"sine_410": first["source_wav_sha256"]}
    for name in ("sine_930", "impulse_burst"):
        variants[name] = create(root, name, first["frames"])
    receipt = {
        "schema": "spatial_audio/w3c_w3_source_variants/1",
        "rights": RIGHTS,
        "frames": first["frames"],
        "sample_rate_hz": RATE,
        "channels": 1,
        "case_count": 42,
        "blocks_per_case": CASE_BLOCKS,
        "doe_sha256": first["doe_sha256"],
        "case_table_sha256": first["case_table_sha256"],
        "upstream_libear": UPSTREAM_EBU,
        "upstream_videolan": UPSTREAM_VLC,
        "variant_source_wav_sha256": variants,
        "method": "ORIGINAL_PUBLIC_TWO_TONES_AND_CASE_LOCAL_DETERMINISTIC_IMPULSE_BURST",
        "direct_stereo": "NAN_QUARANTINED"
    }
    with (root / "w3_source_variants.json").open("x") as f:
        json.dump(receipt, f, sort_keys=True, indent=2)
        f.write("\n")
    print("W3_SOURCE_VARIANT_CUSTODY_PASS", json.dumps(receipt, sort_keys=True))

if __name__ == "__main__":
    main()
