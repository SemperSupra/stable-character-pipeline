#!/usr/bin/env python3
"""R040 bounded real OpenEXR decoded-pixel independent render QA.

Uses only original synthetic R037 Cycles output. Decoding and coverage are
not photorealism, anatomical truth, or human intent preference measurements.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import OpenEXR

SIZE = 256
MAX_FILE_BYTES = 16 * 1024 * 1024
GROUPS = {
    "beauty": ("combined", ("R", "G", "B")),
    "depth": ("depth", ("Z",)),
    "normal": ("normal", ("X", "Y", "Z")),
    "vector": ("vector", ("X", "Y")),
    "object": ("indexob", ("X",)),
}


def reject(message):
    raise ValueError("R040_EXR_PIXEL_REJECT " + message)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def group_name(names, search, comp):
    matches = [
        key for key in names
        if "." in key
        and search in key.rsplit(".", 1)[0].lower()
        and key.rsplit(".", 1)[1].upper() == comp
    ]
    if len(matches) != 1:
        reject("missing or ambiguous " + search + "." + comp)
    return matches[0]


def analyze_numeric(arr, kind):
    if arr.dtype.kind not in ("i", "u", "f") or arr.shape != (SIZE, SIZE):
        reject(kind + " unexpected dtype or dimensions")
    if arr.dtype.kind == "f" and not np.any(np.isfinite(arr)):
        reject(kind + " no finite pixels")
    vals = arr.astype(np.float64)
    finite = np.isfinite(vals)
    finite_count = int(np.count_nonzero(finite))
    if finite_count == 0:
        reject(kind + " missing finite values")
    finite_vals = vals[finite]
    return {
        "finite": finite_count,
        "nonfinite": int(vals.size - finite_count),
        "min": float(np.min(finite_vals)),
        "max": float(np.max(finite_vals)),
        "mean": float(np.mean(finite_vals)),
        "nonzero": int(np.count_nonzero(np.abs(finite_vals) > 1e-7)),
    }


def decode(path):
    if path.is_symlink() or not path.is_file() or not 512 <= path.stat().st_size <= MAX_FILE_BYTES:
        reject("EXR input must be bounded, non-symlink regular file")
    with OpenEXR.File(str(path), separate_channels=True) as exr:
        if len(exr.parts) != 1:
            reject("R037 expected exactly one EXR part")
        part = exr.parts[0]
        if part.width() != SIZE or part.height() != SIZE:
            reject("unexpected OpenEXR pixel dimensions")
        channels = part.channels
        if len(channels) > 64:
            reject("unexpected EXR channel count")
        decoded = {}
        summaries = {}
        for group, (search, components) in GROUPS.items():
            decoded[group] = {}
            summaries[group] = {}
            for c in components:
                name = group_name(channels.keys(), search, c)
                pix = np.asarray(channels[name].pixels)
                summaries[group][c] = analyze_numeric(pix, group + "." + c)
                decoded[group][c] = pix.astype(np.float32)
        # Background Z may be +Inf in Cycles: require a nonempty valid
        # foreground depth mask, not all pixels finite.
        valid_z = np.isfinite(decoded["depth"]["Z"]) & (decoded["depth"]["Z"] > 0)
        if np.count_nonzero(valid_z) < SIZE * SIZE // 100:
            reject("missing >1% valid positive depth foreground")

        for c in "RGB":
            stat = summaries["beauty"][c]
            if stat["nonfinite"]:
                reject("nonfinite beauty component " + c)
        if all(summaries["beauty"][c]["nonzero"] == 0 for c in "RGB"):
            reject("black/empty beauty passes")
        if not any(summaries["object"]["X"]["nonzero"] for _ in [0]):
            reject("no nonzero object segmentation foreground")
        if sum(summaries["normal"][c]["nonzero"] for c in "XYZ") == 0:
            reject("normal pass is entirely empty")

        report = {
            "sha256": digest(path),
            "bytes": path.stat().st_size,
            "dimensions": [SIZE, SIZE],
            "declared_channel_count": len(channels),
            "pixel_summary": summaries,
            "finite_positive_depth_pixels": int(np.count_nonzero(valid_z)),
        }
        return decoded, report


def paired_verify(a, b):
    x, ax = decode(a)
    y, by = decode(b)
    beauty = [
        np.abs(x["beauty"][c].astype(np.float64) -
               y["beauty"][c].astype(np.float64))
        for c in "RGB"
    ]
    altered = int(np.count_nonzero(np.any(np.stack(beauty) > 1e-5, axis=0)))
    if altered < SIZE * SIZE // 1000:
        reject("real decoded beauty pass has no material treatment change")

    # Stable geometry and object-index layers are expected across shader-only
    # treatments, unlike surface normal maps that may alter shading normals.
    idx_same = np.array_equal(x["object"]["X"], y["object"]["X"])
    if not idx_same:
        reject("object-index segmentation changed under material-only edit")
    depth_a = x["depth"]["Z"]
    depth_b = y["depth"]["Z"]
    foreground = (np.isfinite(depth_a) & np.isfinite(depth_b)
                  & (depth_a > 0) & (depth_b > 0))
    if np.count_nonzero(foreground) < SIZE * SIZE // 100:
        reject("not enough paired depth samples")
    diff = np.abs(depth_a[foreground].astype(np.float64) -
                  depth_b[foreground].astype(np.float64))
    max_depth_delta = float(np.max(diff))
    if max_depth_delta > 1e-4:
        reject("depth changed despite frozen mesh and camera")

    return {
        "schema": "r040.cycles.exr.pixels.v1",
        "status": "PASS_NARROW_DECODED_RENDER_PASS_SEMANTICS",
        "qualification": "NOT_PHOTOREALISM_OR_ANATOMICAL_OR_OWNER_PREFERENCE_ACCEPTANCE",
        "arm_baseline": ax,
        "arm_material": by,
        "actual_changed_beauty_pixels": altered,
        "max_paired_foreground_depth_delta": max_depth_delta,
        "object_id_exact_equal": idx_same,
        "rights": "ORIGINAL_SYNTHETIC",
        "decoder": "OpenEXR Python File(separate_channels=True) pinned wheel",
        "source_and_scene_identity": "cross-arm geometric pin remains owned by existing Go renderlab",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--material", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = paired_verify(args.baseline, args.material)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("R040_EXR_DECODED_RECEIPT", json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
