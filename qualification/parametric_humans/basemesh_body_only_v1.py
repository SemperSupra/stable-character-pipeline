#!/usr/bin/env python3
"""Deterministic visible-body-only extraction from pinned MakeHuman core CC0 OBJ.

Geometry/UV transfer only. Excludes all non-body source groups and never infers
scale, character identity, retargeted bones, quality or release. No network access.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

from basemesh_admission_v1 import inspect, OFFICIAL_BLOB, EXPECTED, AdmissionError

SCHEMA = "scp.r009.cc0.body_only_geometry.v1"

class BodyExtractionError(ValueError):
    pass


def extract(raw: bytes, *, expected_blob: str = OFFICIAL_BLOB,
            expected_shape: dict | None = EXPECTED) -> tuple[bytes, dict]:
    # Reuse existing licensed source parser, not another independently drifting
    # admission policy. Tests supply explicit source-local fake blob/shape.
    try:
        admitted = inspect(raw, expected_blob, expected_shape)
    except (AdmissionError, UnicodeDecodeError) as exc:
        raise BodyExtractionError("SOURCE_NOT_ADMITTED:" + str(exc)) from exc
    lines = raw.decode("utf-8").splitlines()
    vertices: list[str] = []
    uvs: list[str] = []
    faces: list[tuple[tuple[int, int | None], ...]] = []
    group = None
    used_v: set[int] = set()
    used_t: set[int] = set()
    uv_modes: set[bool] = set()
    for line in lines:
        if not line or line.lstrip().startswith("#"):
            continue
        bits = line.split()
        op = bits[0]
        if op == "v":
            vertices.append(" ".join(bits[1:4]))
        elif op == "vt":
            if len(bits) < 3 or len(bits) > 4:
                raise BodyExtractionError("INVALID_UV_ARITY")
            try:
                uv = [float(x) for x in bits[1:]]
            except ValueError as exc:
                raise BodyExtractionError("INVALID_UV_NUMBER") from exc
            if not all(math.isfinite(x) for x in uv):
                raise BodyExtractionError("NONFINITE_UV")
            uvs.append(" ".join(bits[1:]))
        elif op == "g":
            group = bits[1]
        elif op == "f" and group == "body":
            if len(bits) != 5:
                raise BodyExtractionError("NONQUAD_BODY")
            corners: list[tuple[int, int | None]] = []
            for token in bits[1:]:
                elements = token.split("/")
                if len(elements) > 3:
                    raise BodyExtractionError("UNSUPPORTED_FACE_CORNER")
                try:
                    vi = int(elements[0]); ti = int(elements[1]) if len(elements) > 1 and elements[1] else None
                except ValueError as exc:
                    raise BodyExtractionError("BAD_FACE_CORNER") from exc
                if vi < 1 or vi > len(vertices) or (ti is not None and (ti < 1 or ti > len(uvs))):
                    raise BodyExtractionError("BAD_FACE_INDEX")
                corners.append((vi, ti))
                used_v.add(vi)
                if ti is not None:
                    used_t.add(ti)
                uv_modes.add(ti is not None)
            if len(set(vi for vi, _ in corners)) != 4:
                raise BodyExtractionError("DEGENERATE_BODY_CORNER")
            faces.append(tuple(corners))
    if len(uv_modes) > 1:
        raise BodyExtractionError("MIXED_UV_REFERENCE")
    if len(faces) != admitted["quantities"]["body_quads"] or len(used_v) != admitted["quantities"]["body_vertex_indices"]:
        raise BodyExtractionError("BODY_ADMISSION_MISMATCH")
    vmap = {v: i + 1 for i, v in enumerate(sorted(used_v))}
    tmap = {t: i + 1 for i, t in enumerate(sorted(used_t))}
    out = ["# Deterministic derivative from official MakeHuman CC0 core OBJ",
           "# Original source Git blob SHA1: " + expected_blob,
           "# Only g body is emitted. No helper groups, rig or morphology inferred.",
           "# License: CC0-1.0 (as stated in original source header)", "g body"]
    out.extend("v " + vertices[i - 1] for i in sorted(used_v))
    out.extend("vt " + uvs[i - 1] for i in sorted(used_t))
    for quad in faces:
        out.append("f " + " ".join(
            str(vmap[v]) + ("/" + str(tmap[t]) if t is not None else "")
            for v, t in quad))
    data = ("\n".join(out) + "\n").encode("utf-8")
    receipt = {"schema": SCHEMA, "source_git_blob_sha1": expected_blob,
               "source_sha256": admitted["raw_sha256"], "output_sha256": hashlib.sha256(data).hexdigest(),
               "source_license": "CC0-1.0_CORE_ASSET", "selected_group": "body",
               "body_quads": len(faces), "body_vertices": len(vmap), "body_uvs": len(tmap),
               "excluded_helper_quads": admitted["helper_quad_faces"],
               "source_groups": admitted["quantities"]["groups"],
               "body_only_geometry_extracted": True, "body_topology_connected": "UNKNOWN",
               "watertight": "UNKNOWN", "units_calibrated": False,
               "skin_weights_preserved": False, "rig_transfer_qualified": False,
               "texture_fidelity_qualified": False, "human_realism_accepted": False,
               "cloth_fit_qualified": False, "release_approved": False}
    return data, receipt


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--receipt", required=True, type=Path)
    p.add_argument("--expected-blob", default=OFFICIAL_BLOB)
    args = p.parse_args()
    if len({args.input.resolve(), args.out.resolve(), args.receipt.resolve()}) < 3 or args.out.exists() or args.receipt.exists():
        raise BodyExtractionError("NO_OVERWRITE")
    obj, result = extract(args.input.read_bytes(), expected_blob=args.expected_blob)
    args.out.write_bytes(obj)
    args.receipt.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"body_quads": result["body_quads"], "body_vertices": result["body_vertices"],
                      "output_sha256": result["output_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
