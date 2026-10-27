#!/usr/bin/env python3
"""Independent, pure-Python GLB animation inspector and PNG falsification gate.

Does not import bpy, MMD Tools or trust self-reported Blender success strings.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from PIL import Image, ImageChops


def parse_glb(path):
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("invalid GLB magic or truncated header")
    magic, version, length = struct.unpack_from("<4sII", data)
    if version != 2 or length != len(data):
        raise ValueError("invalid GLB version or length")
    position = 12
    chunks = {}
    while position < length:
        if position + 8 > length:
            raise ValueError("truncated GLB chunk header")
        size, typ = struct.unpack_from("<I4s", data, position)
        position += 8
        if position + size > length:
            raise ValueError("truncated GLB chunk")
        if typ in chunks:
            raise ValueError("duplicate GLB chunk type")
        chunks[typ] = data[position:position + size]
        position += size
    if b"JSON" not in chunks or bytes((66, 73, 78, 0)) not in chunks:
        raise ValueError("GLB requires JSON and BIN chunks")
    payload = json.loads(chunks[b"JSON"].decode("utf-8").rstrip(" \t\n\r"))
    return payload, chunks[bytes((66, 73, 78, 0))]


def accessor_samples(gltf, blob, index):
    accessor = gltf["accessors"][index]
    if accessor.get("componentType") != 5126 or accessor.get("type") not in ("SCALAR", "VEC3"):
        raise ValueError("unsupported channel accessor type")
    if accessor.get("sparse"):
        raise ValueError("unsupported sparse accessor")
    view = gltf["bufferViews"][accessor["bufferView"]]
    if view.get("buffer", 0) != 0:
        raise ValueError("external buffer not accepted")
    width = 1 if accessor["type"] == "SCALAR" else 3
    item_size = 4 * width
    stride = view.get("byteStride", item_size)
    if stride < item_size:
        raise ValueError("invalid byteStride")
    count = accessor["count"]
    if not 1 <= count <= 10000:
        raise ValueError("unbounded or empty accessor")
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    fmt = "<" + ("f" * width)
    values = []
    for i in range(count):
        cursor = start + stride * i
        if cursor + item_size > len(blob):
            raise ValueError("buffer accessor out of bounds")
        value = struct.unpack_from(fmt, blob, cursor)
        if not all(math.isfinite(float(v)) for v in value):
            raise ValueError("NaN/Inf animation sample")
        values.append(value if width > 1 else value[0])
    return values


def inspect_animations(gltf, binary):
    skin_nodes = {i for skin in gltf.get("skins", []) for i in skin.get("joints", [])}
    if not skin_nodes:
        raise AssertionError("export omitted skinned rig metadata")
    verdicts = []
    for anim in gltf.get("animations", []):
        samplers = anim["samplers"]
        for channel in anim["channels"]:
            target = channel["target"]
            if target.get("path") != "translation" or target.get("node") not in skin_nodes:
                continue
            sampler = samplers[channel["sampler"]]
            times = accessor_samples(gltf, binary, sampler["input"])
            points = accessor_samples(gltf, binary, sampler["output"])
            if len(times) != len(points) or len(times) < 2:
                raise AssertionError("translation channel length mismatch")
            if any(b < a for a, b in zip(times, times[1:])):
                raise AssertionError("non-monotonic motion times")
            distance = math.dist(points[0], points[-1])
            verdicts.append({
                "animation": anim.get("name", "unnamed"),
                "node": target["node"],
                "samples": len(times),
                "first_second": times[0],
                "last_second": times[-1],
                "translation_displacement": distance,
                "interpolation": sampler.get("interpolation", "LINEAR")
            })
    accepted = [v for v in verdicts if v["last_second"] - v["first_second"] >= .8
                and v["translation_displacement"] > .1]
    if not accepted:
        raise AssertionError("no animated skinned joint with >=.8 second duration and >.1 translation; candidates=" + str(verdicts))
    return {"skins": len(gltf["skins"]), "joint_nodes": len(skin_nodes), "moving_channels": accepted}


def fake_glb(json_obj):
    payload = json.dumps(json_obj).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    binary = bytes(4)
    size = 12 + 8 + len(payload) + 8 + len(binary)
    return struct.pack("<4sII", b"glTF", 2, size) + struct.pack("<I4s", len(payload), b"JSON") + payload + struct.pack("<I4s", len(binary), bytes((66, 73, 78, 0))) + binary


def self_test(out):
    out.mkdir(parents=True, exist_ok=True)
    good = fake_glb({"asset": {"version": "2.0"}})
    p = out / "negative.glb"
    p.write_bytes(good)
    cases = [
        ("bad_magic", b"NOPE" + good[4:]),
        ("truncation", good[:-1]),
        ("missing_animation", good),
    ]
    for name, data in cases:
        p.write_bytes(data)
        try:
            if name == "missing_animation":
                scene, raw = parse_glb(p)
                inspect_animations(scene, raw)
            else:
                parse_glb(p)
        except (ValueError, AssertionError, KeyError):
            print("EXPECTED_REJECTION", name)
        else:
            raise AssertionError("negative control incorrectly admitted " + name)
    p.unlink()


def verify(directory):
    model = directory / "animated_mmd.glb"
    scene, raw = parse_glb(model)
    motion = inspect_animations(scene, raw)
    images = [directory / f"frame_{n:04d}.png" for n in range(31)]
    for f in images:
        if not f.exists() or f.stat().st_size < 500:
            raise AssertionError("missing/empty frame " + str(f))
    with Image.open(images[0]) as a, Image.open(images[15]) as b, Image.open(images[30]) as c:
        im0, im15, im30 = a.convert("RGB"), b.convert("RGB"), c.convert("RGB")
        if len({im0.size, im15.size, im30.size}) != 1 or im0.size != (320, 240):
            raise AssertionError("frame dimensions inconsistent")
        changes_mid = ImageChops.difference(im0, im15)
        changes_end = ImageChops.difference(im0, im30)
        count_mid = sum(1 for p in changes_mid.getdata() if max(p) > 20)
        count_end = sum(1 for p in changes_end.getdata() if max(p) > 20)
        if count_mid < 100 or count_end < 100:
            raise AssertionError("frames did not change enough to demonstrate rendered motion")
        contact = Image.new("RGB", (960, 240))
        for k, im in enumerate((im0, im15, im30)):
            contact.paste(im, (320 * k, 0))
        contact.save(directory / "contact_sheet.png")
    receipt = json.loads((directory / "interchange_source_receipt.json").read_text(encoding="utf-8"))
    if receipt.get("frame_count") != 31 or receipt.get("evaluated_mesh_displacement", 0) <= .1:
        raise AssertionError("failed mesh deformation reference evidence")
    result = {
        "schema": "scp.mmd.interchange.verification.v1",
        "result": "PASS_INDEPENDENT_GLTF_ANIMATED_SKIN_AND_RENDER_FRAMES",
        "gltf": motion,
        "changed_pixels_at_frame_15": count_mid,
        "changed_pixels_at_frame_30": count_end,
        "source_glb_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
        "scope": "independent binary glTF skin/bone animation + perceptual frame drift; no physical or MMD engine parity claims"
    }
    (directory / "interchange_verified.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test(args.out)
    else:
        verify(args.out)
