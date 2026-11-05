#!/usr/bin/env python3
"""Stdlib GLB source admission screen: no network, no Blender, no licensing inference."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

def inspect(path, descriptor):
    raw = Path(path).read_bytes()
    expected = descriptor
    assert len(raw) == expected["size_bytes"], "unexpected source byte length"
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert blob == expected["git_blob_sha1"], "source git blob hash mismatch"
    assert len(raw) > 20 and raw[:4] == b"glTF", "not binary glTF"
    assert struct.unpack_from("<I", raw, 4)[0] == 2, "wrong glTF version"
    assert struct.unpack_from("<I", raw, 8)[0] == len(raw), "GLB length mismatch"
    length, kind = struct.unpack_from("<II", raw, 12)
    assert kind == 0x4E4F534A and 20 + length <= len(raw), "missing JSON GLB chunk"
    gltf = json.loads(raw[20:20 + length].decode("utf8").strip())
    assert gltf.get("asset", {}).get("version") == "2.0"
    animations = gltf.get("animations", [])
    assert len(animations) >= 10, "expected horse motions absent"
    assert gltf.get("skins") and gltf.get("meshes"), "no rigged mesh"
    channels = sum(len(a.get("channels", [])) for a in animations)
    assert channels >= len(animations), "implausibly few animated channels"
    return {"schema": "equine.source.screen.v1", "verdict": "STRUCTURAL_SOURCE_SCREEN_PASS",
            "source_sha256": hashlib.sha256(raw).hexdigest(), "source_git_blob_sha1": blob,
            "animation_count": len(animations),
            "animation_names": [a.get("name", "(unnamed)") for a in animations],
            "skin_count": len(gltf["skins"]), "mesh_count": len(gltf["meshes"]),
            "animation_channels": channels,
            "license_state": "SOURCE_CANDIDATE_CC0_DECLARED_NOT_INTEGRATION_ADMITTED",
            "biomechanical_state": "UNKNOWN", "retarget_state": "NOT_RUN"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--descriptor", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    descriptor = json.loads(Path(a.descriptor).read_text())
    report = inspect(a.source, descriptor)
    Path(a.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    main()
