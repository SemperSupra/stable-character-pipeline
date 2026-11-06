#!/usr/bin/env python3
"""Reversible actor-specific morphology derivative of the ORIGINAL R009 wardrobe.

Pure stdlib and source-original geometry only. This does not assert sex from
appearance or claim anatomical/cloth/identity realism. Every dimension is
independently controllable; sex is an owner-supplied character attribute.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from modular_wardrobe_v1 import ACTORS
from rig35_v2 import glb_pack
from verify_original_glb import decode, accessory

SCHEMA = "scp.r009.morphology_profile.v1"
BOUNDS = {
    "shoulder_width": (.82, 1.22), "chest_depth": (.82, 1.22),
    "waist_width": (.78, 1.22), "hip_width": (.82, 1.22),
    "jaw_width": (.84, 1.20), "brow_projection_m": (0., .014),
    "chin_projection_m": (0., .015), "bust_projection_m": (0., .035),
}
DEFAULT = {
    "AsterOriginal": {
        "sex": "male", "presentation": "masculine",
        "shoulder_width": 1.09, "chest_depth": 1.065,
        "waist_width": .98, "hip_width": .965, "jaw_width": 1.09,
        "brow_projection_m": .007, "chin_projection_m": .006,
        "bust_projection_m": 0.,
    },
    "JuniperOriginal": {
        "sex": "female", "presentation": "feminine",
        "shoulder_width": .965, "chest_depth": 1.02,
        "waist_width": .93, "hip_width": 1.075, "jaw_width": .955,
        "brow_projection_m": .002, "chin_projection_m": .002,
        "bust_projection_m": .017,
    },
}

def validate(profiles):
    if not isinstance(profiles, dict) or set(profiles) != set(ACTORS):
        raise ValueError("MORPH_PROFILE_ACTORS")
    clean = {}
    for actor in ACTORS:
        p = profiles[actor]
        if not isinstance(p, dict) or set(p) != set(BOUNDS) | {"sex", "presentation"}:
            raise ValueError("MORPH_PROFILE_KEYS:" + actor)
        if p["sex"] not in ("male", "female") or p["presentation"] not in (
                "masculine", "feminine", "androgynous", "custom"):
            raise ValueError("MORPH_PROFILE_SEMANTICS:" + actor)
        for key, (lo, hi) in BOUNDS.items():
            v = p[key]
            if type(v) not in (float, int) or not math.isfinite(v) or not lo <= v <= hi:
                raise ValueError("MORPH_PROFILE_BOUNDS:" + actor + ":" + key)
        clean[actor] = dict(p)
    return clean

def gaussian(v, center, sigma):
    return math.exp(-.5 * ((v - center) / sigma) ** 2)

def deform(xyz, slot, p):
    x, y, z = xyz
    if slot in ("body", "top", "alt_top", "bottom", "alt_bottom"):
        torso = max(0., 1. - max(0., abs(x) - .23) / .13)
        if slot in ("body", "top", "alt_top"):
            shoulder = gaussian(y, 1.315, .105)
            sx = 1. + torso * shoulder * (p["shoulder_width"] - 1.)
            depth = 1. + gaussian(y, 1.270, .105) * (p["chest_depth"] - 1.)
            if y < 1.49 and abs(x) < .30:
                z *= depth
            if z < -.022 and abs(x) < .25:
                left = gaussian(x, -.085, .050)
                right = gaussian(x, .085, .050)
                projection = (left + right) * gaussian(y, 1.258, .067)
                z -= p["bust_projection_m"] * projection * (
                    1.20 if slot != "body" else 1.)
        else:
            sx = 1.
        sx *= 1. + torso * gaussian(y, 1.050, .088) * (p["waist_width"] - 1.)
        sx *= 1. + torso * gaussian(y, .875, .110) * (p["hip_width"] - 1.)
        x *= sx
    if slot == "body" and 1.50 < y < 1.77 and abs(x) < .17:
        x *= 1. + gaussian(y, 1.605, .064) * (p["jaw_width"] - 1.)
        if z < -.026:
            z -= p["brow_projection_m"] * gaussian(y, 1.688, .023) * (
                gaussian(x, -.057, .037) + gaussian(x, .057, .037))
            z -= p["chin_projection_m"] * gaussian(y, 1.565, .033) * gaussian(x, 0., .055)
    if slot == "hair" and y > 1.67 and abs(x) < .18:
        x *= 1. + .24 * (p["jaw_width"] - 1.) * gaussian(y, 1.724, .072)
    return (x, y, z)

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])

def transformed_normal(pos, normal, slot, profile):
    # Inverse-transpose of local deformation Jacobian; corrects shading for
    # the non-rigid morphology change without editing source bone weights.
    eps = 1.e-4
    tangents = []
    for axis in range(3):
        a = list(pos); b = list(pos)
        a[axis] += eps; b[axis] -= eps
        fa = deform(a, slot, profile); fb = deform(b, slot, profile)
        tangents.append(tuple((fa[k]-fb[k])/(2.*eps) for k in range(3)))
    tx, ty, tz = tangents
    a, b, c = cross(ty, tz), cross(tz, tx), cross(tx, ty)
    out = tuple(normal[0]*a[i] + normal[1]*b[i] + normal[2]*c[i] for i in range(3))
    norm = math.sqrt(sum(v*v for v in out))
    if norm < 1.e-8: raise ValueError("MORPH_SINGULAR_NORMAL")
    return tuple(v/norm for v in out)

def write_vec3(doc, bb, idx, points):
    a = doc["accessors"][idx]
    view = doc["bufferViews"][a["bufferView"]]
    if a["componentType"] != 5126 or a["type"] != "VEC3" or (
            a["count"] != len(points)) or "byteStride" in view or view["buffer"] != 0:
        raise ValueError("MORPH_UNSUPPORTED_ACCESSOR")
    off = view["byteOffset"] + a.get("byteOffset", 0)
    if off < 0 or off + len(points)*12 > view["byteOffset"] + view["byteLength"] or (
            off + len(points)*12 > len(bb)):
        raise ValueError("MORPH_ACCESSOR_BOUNDS")
    for k, xyz in enumerate(points):
        if not all(math.isfinite(v) for v in xyz): raise ValueError("MORPH_NONFINITE")
        struct.pack_into("<fff", bb, off + 12*k, *xyz)
    if "min" in a: a["min"] = [min(v[axis] for v in points) for axis in range(3)]
    if "max" in a: a["max"] = [max(v[axis] for v in points) for axis in range(3)]

def apply(src, src_manifest, out, out_manifest, receipt_path, profiles=None):
    paths = [Path(x).resolve() for x in (src, src_manifest, out, out_manifest, receipt_path)]
    if len(set(paths)) != 5: raise ValueError("MORPH_SOURCE_OVERWRITE")
    profiles = validate(DEFAULT if profiles is None else profiles)
    raw = Path(src).read_bytes()
    manifest = json.loads(Path(src_manifest).read_text())
    if manifest.get("schema") != "scp.original_wardrobe_manifest.v1" or (
            manifest.get("derived_sha256") != hashlib.sha256(raw).hexdigest()):
        raise ValueError("MORPH_SOURCE_MANIFEST_SHA")
    doc, binary = decode(raw)
    if doc.get("extras", {}).get("source_class") != "ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("MORPH_SOURCE_CLASS")
    if len(doc.get("skins", [])) != 2 or any(len(s["joints"]) != 35 for s in doc["skins"]):
        raise ValueError("MORPH_RIG_CONTRACT")
    bb = bytearray(binary)
    seen = set()
    counts = {a: 0 for a in ACTORS}
    for actor in ACTORS:
        slots = manifest["actor_slots"][actor]
        for slot in sorted(slots):
            mesh = doc["meshes"][slots[slot]["mesh"]]
            for prim in mesh["primitives"]:
                attrs = prim["attributes"]
                key = (actor, attrs["POSITION"])
                if key in seen: continue  # alternative colorways share base geometry
                seen.add(key)
                positions = accessory(doc, binary, attrs["POSITION"])
                normals = accessory(doc, binary, attrs["NORMAL"])
                if len(positions) != len(normals): raise ValueError("MORPH_NORMAL_COUNT")
                new = [deform(p, slot, profiles[actor]) for p in positions]
                nn = [transformed_normal(p, n, slot, profiles[actor])
                      for p, n in zip(positions, normals)]
                write_vec3(doc, bb, attrs["POSITION"], new)
                write_vec3(doc, bb, attrs["NORMAL"], nn)
                counts[actor] += sum(any(abs(a-b) > 1.e-6 for a, b in zip(p, q))
                                     for p, q in zip(positions, new))
    if not all(counts.values()): raise ValueError("MORPH_NO_VERTEX_EFFECT")
    doc["extras"]["parametric_morphology"] = {
        "schema": SCHEMA, "profiles": profiles,
        "owner_asserted_character_sex": True,
        "skin_and_animation_retained": True,
        "visual_anatomical_and_cloth_fit_accepted": False,
    }
    output = glb_pack(doc, bb)
    new_manifest = json.loads(json.dumps(manifest))
    new_manifest["morphology_source_sha256"] = hashlib.sha256(raw).hexdigest()
    new_manifest["derived_sha256"] = hashlib.sha256(output).hexdigest()
    new_manifest["morphology_profiles"] = profiles
    new_manifest["appearance_accepted"] = False
    rec = {
        "schema": "scp.r009.morphology_receipt.v1",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "derived_sha256": hashlib.sha256(output).hexdigest(),
        "actor_vertex_changes": counts,
        "profile_schema": SCHEMA, "structural_qualification": "CANDIDATE",
        "human_appearance_accepted": False, "garment_fit_accepted": False,
        "animation_contact_accepted": False,
    }
    for path, payload in ((out, output),
                          (out_manifest, (json.dumps(new_manifest, sort_keys=True, indent=2)+"\n").encode()),
                          (receipt_path, (json.dumps(rec, sort_keys=True, indent=2)+"\n").encode())):
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(payload)
    return rec

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--out-manifest", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--profiles", help="Optional JSON with schema and complete per-actor profiles")
    a = ap.parse_args()
    profiles = None
    if a.profiles:
        payload = json.loads(Path(a.profiles).read_text())
        if payload.get("schema") != SCHEMA: raise ValueError("MORPH_PROFILE_SCHEMA")
        profiles = payload.get("actors")
    print(json.dumps(apply(a.input, a.manifest, a.out, a.out_manifest,
                           a.receipt, profiles), sort_keys=True))
