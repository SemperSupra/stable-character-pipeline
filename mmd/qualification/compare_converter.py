#!/usr/bin/env python3
"""Independent MMD-to-glTF comparison: upstream Blender vs headless MIT CLI.

Both sources operate on our generated 1-bone synthetic PMX/VMD, not downloaded
MMD character or motion media. The binary inspector is upstream-independent.
"""
import argparse
import hashlib
import json
from pathlib import Path
from verify_interchange import inspect_animations, parse_glb


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(direct, blender, output):
    c, cbin = parse_glb(direct)
    b, bbin = parse_glb(blender)
    ctrack = inspect_animations(c, cbin)
    btrack = inspect_animations(b, bbin)
    extras = c.get("extras", {}).get("mmd", {})
    if extras.get("format") != "pmx":
        raise AssertionError("direct exporter did not preserve native PMX metadata")
    if extras.get("unitScale") != 1:
        raise AssertionError("direct exporter silently altered explicit unitScale=1")
    if extras.get("nameEn") != "SCP synthetic triangle":
        raise AssertionError("original authored model name lost in extras.mmd")
    bones = extras.get("bones", [])
    if len(bones) != 1 or bones[0].get("name") != "センター":
        raise AssertionError("source Japanese bone name missing in raw extras.mmd")
    x = ctrack["moving_channels"][0]["translation_displacement"]
    y = btrack["moving_channels"][0]["translation_displacement"]
    if abs(x-y) > 0.12:
        raise AssertionError(f"independent converter displacement differs: direct={x}, blender={y}")
    report = {
      "schema": "scp.mmd.converter-qualification.v1",
      "result": "PASS_INDEPENDENT_HEADLESS_PMX_VMD_CONVERTER_COMPARISON",
      "direct_tool": "mmd2gltf-gui at immutable GitHub commit, MIT software; original synthetic assets only",
      "direct_sha256": digest(direct),
      "blender_sha256": digest(blender),
      "direct_motion": ctrack,
      "blender_motion": btrack,
      "units": "explicit 1.0 MMD source scale; displacement uses exported glTF metric",
      "extras_raw_model": {"nameEn": extras["nameEn"], "bones": len(bones), "rigidBodies": len(extras.get("rigidBodies", []))},
      "unqualified": ["physical accuracy", "native engine IK and rigidbody parity", "third-party models/motions", "expressive morphs"]
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


def main():
    p=argparse.ArgumentParser()
    for n in ("direct", "blender", "out"):
        p.add_argument("--"+n, required=True, type=Path)
    a=p.parse_args()
    compare(a.direct,a.blender,a.out)


if __name__ == "__main__":
    main()
