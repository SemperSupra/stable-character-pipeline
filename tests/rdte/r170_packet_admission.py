"""Independent strict receiver for original synthetic Go->Blender scene packets.

This ONLY admits the two frozen, original R167 synthetic fixtures. Hash matching
detects pipeline drift, not actor authentication or genuine Oneirifact source.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
from pathlib import Path
import re

MAX_BYTES = 65536
SCHEMA = "synthetic.cycles-scene-packet/v0.1"
REQUEST_SCHEMA = "synthetic.render-request/v0.1"
FRAME = "Z_UP_METERS_RIGHT_HANDED"
ENGINE = "BLENDER_CYCLES_5_2_4_CPU"
FIDELITY = "UNVERIFIED_SYNTHETIC_GEOMETRY_REGISTRY"
PLACEHOLDER_SOURCE = "sha256:" + "a" * 64
FROZEN_FINGERPRINTS = {
    "A": "sha256:5d31f87a612fb964638eb45d37f837ba40e67e352441e0f115d3029f7c855c86",
    "B": "sha256:a91475b4230293079128c7bca6dbc73c52b9712ba2279041708460c10fc5f3ed",
}
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite_constant(token):
    raise ValueError("nonfinite JSON token")


def _keys(value, fields, optional=()):
    if not isinstance(value, dict) or not set(fields) <= value.keys() or set(value) - set(fields) - set(optional):
        raise ValueError("missing or unknown typed fields")


def _number(value, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
        raise ValueError("invalid/nonfinite numerical field")
    return value


def _vector(value, low=-1000, high=1000):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError("invalid vector shape")
    return [_number(v, low, high) for v in value]


def _name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError("invalid semantic name")
    return value


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def validate_bytes(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("oversized/missing input bytes")
    packet = json.loads(raw, object_pairs_hook=_unique_keys, parse_constant=_nonfinite_constant)
    _keys(packet, ("schema", "variant", "request", "synthetic_request_fingerprint", "source_fidelity"))
    if packet["schema"] != SCHEMA or packet["variant"] not in FROZEN_FINGERPRINTS or packet["source_fidelity"] != FIDELITY:
        raise ValueError("unapproved synthetic packet or fidelity claim")
    variant = packet["variant"]
    request = packet["request"]
    _keys(request, ("schema", "source", "frame", "objects", "materials", "cameras", "lights", "options"))
    if request["schema"] != REQUEST_SCHEMA or request["frame"] != FRAME:
        raise ValueError("wrong render schema/frame")

    source = request["source"]
    _keys(source, ("document_id", "revision", "graph_sha256"), ("instance_sha256",))
    _name(source["document_id"])
    _name(source["revision"])
    if source != {
        "document_id": "OriginalSynthetic",
        "revision": "syntheticRevision1",
        "graph_sha256": PLACEHOLDER_SOURCE,
    }:
        raise ValueError("synthetic source binding changed or forged as real")

    opts = request["options"]
    _keys(opts, ("engine", "width", "height", "samples", "seed"))
    if opts != {"engine": ENGINE, "width": 320, "height": 240, "samples": 32, "seed": 139}:
        raise ValueError("unadmitted engine or resource setting")
    if not isinstance(request["materials"], list) or len(request["materials"]) != 2:
        raise ValueError("material count")
    materials = []
    for m in request["materials"]:
        _keys(m, ("id", "base_color", "metallic", "roughness"))
        name = _name(m["id"])
        rgb = _vector(m["base_color"], 0, 1)
        metal = _number(m["metallic"], 0, 1)
        rough = _number(m["roughness"], 0, 1)
        materials.append({"id": name, "base_color": rgb, "metallic": metal, "roughness": rough})
    materials.sort(key=lambda m: m["id"])
    if [m["id"] for m in materials] != ["blue", "red"]:
        raise ValueError("unknown or duplicate materials")

    if not isinstance(request["objects"], list) or len(request["objects"]) != 2:
        raise ValueError("object count")
    objects = []
    for item in request["objects"]:
        _keys(item, ("id", "feature_path", "material_id", "translation", "uniform_scale"))
        name = _name(item["id"])
        path = item["feature_path"]
        if path not in ("root/cube", "root/sphere"):
            raise ValueError("unknown synthetic geometry occurrence")
        material_id = _name(item["material_id"])
        if material_id not in ("blue", "red"):
            raise ValueError("unknown material binding")
        position = _vector(item["translation"])
        scale = _number(item["uniform_scale"], 1, 1)
        objects.append({"id": name, "feature_path": path, "material_id": material_id, "translation": position, "uniform_scale": scale})
    objects.sort(key=lambda o: o["id"])
    if [o["id"] for o in objects] != ["cube", "sphere"]:
        raise ValueError("unknown/duplicate objects")
    if objects[0]["feature_path"] != "root/cube" or objects[1]["feature_path"] != "root/sphere":
        raise ValueError("changed source identity")
    if objects[0]["translation"] != [-0.8, 0, 0.7] or objects[1]["translation"] != [0.9, 0, 0.85]:
        raise ValueError("changed frozen synthetic geometry position")

    if not isinstance(request["cameras"], list) or len(request["cameras"]) != 1:
        raise ValueError("camera count")
    camera = request["cameras"][0]
    _keys(camera, ("id", "position", "target", "up", "fov_degrees"))
    if camera["id"] != "camera":
        raise ValueError("camera identity")
    eye, target, up = (_vector(camera[key]) for key in ("position", "target", "up"))
    fov = _number(camera["fov_degrees"], 1, 179)
    direction = [b - a for a, b in zip(eye, target)]
    cross = [direction[1] * up[2] - direction[2] * up[1],
             direction[2] * up[0] - direction[0] * up[2],
             direction[0] * up[1] - direction[1] * up[0]]
    if sum(x * x for x in direction) <= 1e-12 or sum(x * x for x in up) <= 1e-12 or sum(x * x for x in cross) <= 1e-12:
        raise ValueError("degenerate camera frame")

    if not isinstance(request["lights"], list) or len(request["lights"]) != 1:
        raise ValueError("light count")
    light = request["lights"][0]
    _keys(light, ("id", "type", "position", "power_watts", "size_meters"))
    if light["id"] != "area" or light["type"] != "AREA":
        raise ValueError("unknown emitter type/identity")
    light_pos = _vector(light["position"])
    power = _number(light["power_watts"], 0, 1e7)
    size = _number(light["size_meters"], 1e-6, 1e4)

    canonical = {
        "schema": REQUEST_SCHEMA,
        "source": source,
        "frame": FRAME,
        "objects": objects,
        "materials": materials,
        "cameras": [{"id": "camera", "position": eye, "target": target, "up": up, "fov_degrees": fov}],
        "lights": [{"id": "area", "type": "AREA", "position": light_pos, "power_watts": power, "size_meters": size}],
        "options": opts,
    }
    # Same field order and compact encoding as the frozen R166 Go typed struct.
    # Only these two source-free fixture numeric profiles are admitted.
    encoded = json.dumps(canonical, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    actual = _sha(encoded)
    claimed = packet["synthetic_request_fingerprint"]
    if not isinstance(claimed, str) or not hmac.compare_digest(actual, claimed) or not hmac.compare_digest(actual, FROZEN_FINGERPRINTS[variant]):
        raise ValueError("typed scene request fingerprint mismatched frozen fixture")
    return packet


def validate_file(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    return validate_bytes(raw), raw
