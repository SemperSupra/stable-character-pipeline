#!/usr/bin/env python3
"""Read-only two-view camera intrinsics challenger on declared synthetic correspondences.

Only camera-coordinate 3D -> 2D reprojection is measured. Neither source PNG
bytes nor independent physical extrinsics, natural human/pony photographs,
protected identities, or camera pose are authenticated by this module.
"""
import hashlib
import json
import math
import re

HEX = re.compile(r"^[0-9a-f]{64}$")


class AdmissionError(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise AdmissionError(reason)


def _digest(value):
    return isinstance(value, str) and HEX.fullmatch(value) is not None


def _finite(values):
    return all(type(v) in (int, float) and math.isfinite(v) for v in values)


def _fit(rows, dimension):
    # Least-squares p = focal * (camera_axis / depth) + principal_point.
    pair = [(r["xyz"][dimension] / r["xyz"][2], r["uv"][dimension]) for r in rows]
    count = len(pair)
    st = sum(t for t, _ in pair)
    sp = sum(p for _, p in pair)
    stt = sum(t * t for t, _ in pair)
    stp = sum(t * p for t, p in pair)
    denominator = count * stt - st * st
    _require(denominator > 1e-10, "degenerate calibration axis")
    focal = (count * stp - st * sp) / denominator
    center = (sp - focal * st) / count
    _require(math.isfinite(focal) and 1 < focal < 100000, "inadmissible focal")
    _require(math.isfinite(center), "nonfinite principal point")
    return focal, center


def _error(rows, fx, fy, cx, cy):
    squared = []
    for r in rows:
        x, y, z = r["xyz"]
        u, v = r["uv"]
        squared.append((fx * x / z + cx - u) ** 2 + (fy * y / z + cy - v) ** 2)
    return math.sqrt(sum(squared) / len(squared))


def assess(rows, max_heldout_error_px=1.0):
    """Fit two or more view-specific intrinsics; challenge independent heldout points.

    family, image SHA, source SHA and extrinsics SHA are *declarations*, not
    proofs of authentic photographs/poses. Refuses split leakage and false PASS.
    """
    _require(isinstance(rows, list) and len(rows) <= 5000, "invalid observation set")
    _require(type(max_heldout_error_px) in (int, float)
             and math.isfinite(max_heldout_error_px)
             and 0 < max_heldout_error_px <= 5, "invalid error budget")
    groups = {}
    for row in rows:
        _require(isinstance(row, dict), "observation must be object")
        needed = ("view", "role", "family", "image_sha256", "source_sha256",
                  "extrinsics_sha256", "point_id", "xyz", "uv", "size")
        _require(all(k in row for k in needed), "missing source/camera receipt")
        _require(row["role"] in ("train", "heldout"), "invalid role")
        _require(all(isinstance(row[k], str) and 0 < len(row[k]) <= 120
                     for k in ("view", "family", "point_id")), "invalid identity")
        _require(all(_digest(row[k]) for k in
                     ("image_sha256", "source_sha256", "extrinsics_sha256")),
                 "invalid SHA-256 declaration")
        _require(type(row["xyz"]) in (tuple, list) and len(row["xyz"]) == 3
                 and _finite(row["xyz"]) and row["xyz"][2] > 0.001,
                 "invalid camera-coordinate 3D point")
        _require(type(row["uv"]) in (tuple, list) and len(row["uv"]) == 2
                 and _finite(row["uv"]), "invalid 2D observation")
        _require(type(row["size"]) in (tuple, list) and len(row["size"]) == 2
                 and all(type(x) is int and 16 <= x <= 16384 for x in row["size"]),
                 "invalid image size")
        _require(0 <= row["uv"][0] <= row["size"][0]
                 and 0 <= row["uv"][1] <= row["size"][1], "pixel outside image")
        groups.setdefault(row["view"], []).append(row)
    _require(2 <= len(groups) <= 16, "two or more calibrated views required")
    report = []
    all_train_families, all_hold_families = set(), set()
    all_train_images, all_hold_images = set(), set()
    for view, samples in sorted(groups.items()):
        train = [r for r in samples if r["role"] == "train"]
        held = [r for r in samples if r["role"] == "heldout"]
        _require(len(train) >= 4 and len(held) >= 2, "insufficient split features")
        _require(len({r["point_id"] for r in samples}) == len(samples),
                 "repeated camera view point ID")
        _require(len({tuple(r["size"]) for r in samples}) == 1, "image-size mismatch")
        _require(len({r["source_sha256"] for r in samples}) == 1, "source change within view")
        _require(len({r["extrinsics_sha256"] for r in samples}) == 1,
                 "unbound/mismatched extrinsics declaration")
        train_fams = {r["family"] for r in train}
        held_fams = {r["family"] for r in held}
        train_imgs = {r["image_sha256"] for r in train}
        held_imgs = {r["image_sha256"] for r in held}
        _require(not (train_fams & held_fams), "capture-family holdout leakage")
        _require(not (train_imgs & held_imgs), "image-byte holdout leakage")
        all_train_families.update(train_fams)
        all_hold_families.update(held_fams)
        all_train_images.update(train_imgs)
        all_hold_images.update(held_imgs)
        fx, cx = _fit(train, 0)
        fy, cy = _fit(train, 1)
        w, h = samples[0]["size"]
        _require(0 <= cx <= w and 0 <= cy <= h, "principal point outside image")
        rmse_train = _error(train, fx, fy, cx, cy)
        rmse_heldout = _error(held, fx, fy, cx, cy)
        report.append({"view": view, "fx_px": round(fx, 6), "fy_px": round(fy, 6),
                       "cx_px": round(cx, 6), "cy_px": round(cy, 6),
                       "train_rmse_px": round(rmse_train, 6),
                       "heldout_rmse_px": round(rmse_heldout, 6),
                       "train_points": len(train), "heldout_points": len(held),
                       "extrinsics": "DECLARED_NOT_INDEPENDENTLY_MEASURED",
                       "heldout_geometry": "PASS_SYNTHETIC_CORRESPONDENCES"
                       if rmse_heldout <= max_heldout_error_px else "FAIL_REPROJECTION"})
    _require(not (all_train_families & all_hold_families), "global family leakage")
    _require(not (all_train_images & all_hold_images), "global image leakage")
    _require(len({samples[0]["extrinsics_sha256"] for samples in groups.values()}) ==
             len(groups), "identical extrinsics receipt on distinct views")
    return {"schema": "scp.camera_intrinsics_declared_holdout.v1",
            "observation_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest(),
            "views": report,
            "geometry": "PASS_DECLARED_SYNTHETIC_ONLY" if all(
                v["heldout_geometry"] == "PASS_SYNTHETIC_CORRESPONDENCES"
                for v in report) else "FAIL_HELDOUT_REPROJECTION",
            "external_photo_fit": "NOT_RUN",
            "independent_extrinsics": "NOT_PROVEN",
            "image_byte_capture": "NOT_VERIFIED_BY_THIS_WORKCELL",
            "character_anatomy": "UNKNOWN",
            "model_mutation": False,
            "release_or_CPE_admission": False}
