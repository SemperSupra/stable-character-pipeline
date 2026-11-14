#!/usr/bin/env python3
"""Original, deterministic, synthetic 3DGS PLY fixture. No person or asset data."""
import argparse
import hashlib
import math
import struct
from pathlib import Path

N = 12
FIELDS = (
    "x", "y", "z", "nx", "ny", "nz",
    "f_dc_0", "f_dc_1", "f_dc_2", "opacity",
    "scale_0", "scale_1", "scale_2",
    "rot_0", "rot_1", "rot_2", "rot_3",
)

def produce() -> bytes:
    header = (
        "ply\nformat binary_little_endian 1.0\n"
        "comment generated synthetic fixture, no external assets or model weights\n"
        f"element vertex {N*N}\n"
        + "".join(f"property float {name}\n" for name in FIELDS)
        + "end_header\n"
    ).encode("ascii")
    payload = bytearray()
    for iz in range(N):
        for ix in range(N):
            x = (ix - (N-1)/2) * 0.065
            z = (iz - (N-1)/2) * 0.065
            values = (
                x, 0.0, z, 0.0, -1.0, 0.0,
                1.45, -0.8, -0.8, 4.0,
                math.log(0.052), math.log(0.016), math.log(0.052),
                1.0, 0.0, 0.0, 0.0,
            )
            payload.extend(struct.pack("<17f", *values))
    return header + payload

def inspect(blob: bytes) -> dict:
    header, separator, payload = blob.partition(b"end_header\n")
    if not separator:
        raise ValueError("no PLY header terminator")
    expected = [f"property float {f}".encode() for f in FIELDS]
    for item in expected:
        if item + b"\n" not in header:
            raise ValueError(f"missing attribute: {item!r}")
    if b"format binary_little_endian 1.0" not in header:
        raise ValueError("wrong encoding")
    if b"element vertex 144\n" not in header:
        raise ValueError("wrong point count")
    if len(payload) != N*N*17*4:
        raise ValueError("truncated or oversized payload")
    for row in struct.iter_unpack("<17f", payload):
        if not all(math.isfinite(x) for x in row):
            raise ValueError("nonfinite data")
        if abs(sum(q*q for q in row[13:17])-1.0) > 1e-5:
            raise ValueError("invalid quaternion")
    return {"points": N*N, "sha256": hashlib.sha256(blob).hexdigest(),
            "fields": list(FIELDS), "bytes": len(blob)}

def self_test():
    a, b = produce(), produce()
    assert a == b
    result = inspect(a)
    assert result["points"] == 144
    for poison in (a.replace(b"property float opacity\n", b"property float missing\n"),
                   a[:-4], a.replace(b"format binary_little_endian 1.0",
                                     b"format ascii 1.0                 ")):
        try:
            inspect(poison)
        except ValueError:
            pass
        else:
            raise AssertionError("negative fixture was accepted")
    print(f"fixture tests PASS sha256={result['sha256']}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="out/synthetic_gaussians.ply")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = produce()
    out.write_bytes(blob)
    print(inspect(blob))
