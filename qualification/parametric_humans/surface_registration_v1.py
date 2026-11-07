"""Bounded, correspondence-driven surface registration primitive (synthetic-safe).

This does not discover nearest mesh points, infer anatomy, generate skin weights,
or claim visual acceptance. An external admitted BVH/landmark stage must provide
per-vertex correspondences with independently classified anatomical surface evidence.
"""
import json
import math
from pathlib import Path

SCHEMA = "scp.synthetic_surface_registration.v1"


class FitRejected(ValueError):
    pass


def _vec3(v):
    if not isinstance(v, (list, tuple)) or len(v) != 3 or any(
        isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x)
        for x in v
    ):
        raise FitRejected("NONFINITE_OR_INVALID_VEC3")
    return tuple(float(x) for x in v)


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _length(a):
    return math.sqrt(_dot(a, a))


def _clamp(x, max_abs):
    return max(-max_abs, min(max_abs, x))


def _unit(v):
    n = _length(v)
    if n <= 1e-12:
        raise FitRejected("ZERO_LENGTH_NORMAL")
    if abs(n - 1.0) > 1e-3:
        raise FitRejected("NORMAL_NOT_UNIT")
    return v


def fit_once(document):
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise FitRejected("UNKNOWN_SCHEMA")
    options = document.get("options")
    if not isinstance(options, dict):
        raise FitRejected("MISSING_OPTIONS")
    numeric_options = ("max_normal_step_m", "max_tangent_step_m",
                       "min_confidence", "max_triangle_area_ratio")
    if any(type(options.get(key)) not in (int, float) for key in numeric_options):
        raise FitRejected("INVALID_OPTIONS")
    try:
        max_normal = float(options["max_normal_step_m"])
        max_tangent = float(options["max_tangent_step_m"])
        min_confidence = float(options["min_confidence"])
        max_area = float(options["max_triangle_area_ratio"])
    except (ValueError, TypeError, KeyError) as exc:
        raise FitRejected("INVALID_OPTIONS") from exc
    if not (0 < max_normal <= 0.25 and 0 <= max_tangent <= max_normal and
            0 < min_confidence <= 1 and 1 < max_area <= 4 and
            all(math.isfinite(v) for v in (max_normal, max_tangent, min_confidence, max_area))):
        raise FitRejected("OUT_OF_RANGE_OPTIONS")
    vertices = [_vec3(v) for v in document.get("vertices", [])]
    normals = [_unit(_vec3(v)) for v in document.get("normals", [])]
    observations = document.get("correspondences", [])
    if not vertices or len(vertices) != len(normals) or len(vertices) != len(observations):
        raise FitRejected("BAD_CORRESPONDENCE_LENGTH")
    if not isinstance(observations, list):
        raise FitRejected("BAD_CORRESPONDENCE_TYPE")
    triangles = document.get("triangles", [])
    if not isinstance(triangles, list) or not triangles:
        raise FitRejected("MISSING_TRIANGLES")
    for f in triangles:
        if (not isinstance(f, list) or len(f) != 3 or len(set(f)) != 3 or
                any(type(i) is not int or i < 0 or i >= len(vertices) for i in f)):
            raise FitRejected("INVALID_TRIANGLE")
    result = list(vertices)
    stats = {"fitted": 0, "held": 0, "unknown": 0, "clamped": 0,
             "positive_normal": 0, "negative_normal": 0, "lateral": 0}
    for i, obs in enumerate(observations):
        if not isinstance(obs, dict):
            raise FitRejected("BAD_OBSERVATION")
        status = obs.get("status")
        if status == "UNKNOWN":
            stats["unknown"] += 1
            continue
        if status == "HOLD":
            stats["held"] += 1
            continue
        if status != "ADMITTED" or obs.get("surface") != "BODY":
            raise FitRejected("UNADMITTED_OR_NONANATOMICAL_SOURCE")
        conf = obs.get("confidence")
        if (type(conf) not in (int, float) or not math.isfinite(conf) or
                not 0 <= conf <= 1):
            raise FitRejected("INVALID_CONFIDENCE")
        if conf < min_confidence:
            stats["unknown"] += 1
            continue
        target = _vec3(obs.get("point"))
        delta = _sub(target, vertices[i])
        n = normals[i]
        signed = _dot(delta, n)
        tangent = _sub(delta, tuple(signed * x for x in n))
        tangent_length = _length(tangent)
        nmove = _clamp(signed, max_normal)
        tmult = min(1., max_tangent / tangent_length) if tangent_length > 0 else 0.
        move = tuple(nmove * n[j] + tangent[j] * tmult for j in range(3))
        result[i] = tuple(vertices[i][j] + move[j] for j in range(3))
        stats["fitted"] += 1
        stats["positive_normal" if signed > 0 else "negative_normal"] += int(signed != 0)
        stats["lateral"] += int(tangent_length > 1e-12)
        stats["clamped"] += int(abs(signed) > max_normal or tangent_length > max_tangent)
    def area_normal(vs, face):
        a, b, c = [vs[index] for index in face]
        return _cross(_sub(b, a), _sub(c, a))
    for face in triangles:
        before = area_normal(vertices, face)
        after = area_normal(result, face)
        before_area = _length(before)
        after_area = _length(after)
        if before_area <= 1e-12 or after_area <= 1e-12:
            raise FitRejected("DEGENERATE_FACE")
        if _dot(before, after) <= 0:
            raise FitRejected("INVERTED_FACE")
        ratio = after_area / before_area
        if ratio > max_area or ratio < 1. / max_area:
            raise FitRejected("FACE_AREA_DISTORTION")
    return {"schema": SCHEMA, "vertices": [list(v) for v in result],
            "triangles": triangles, "stats": stats,
            "qualification": "SYNTHETIC_GEOMETRIC_CONTRACT_ONLY",
            "motion_accepted": False, "identity_accepted": False}


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit("STOP: output exists")
    result = fit_once(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
