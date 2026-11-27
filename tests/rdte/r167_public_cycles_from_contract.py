#!/usr/bin/env python3
"""Public-only typed scene overlay into Blender Cycles.

The two primitive shapes are defined by an ORIGINAL SYNTHETIC registry here;
the Go render request controls only objects' placements, material bindings,
lighting and camera. No private Oneirifact graph or source-fidelity claim.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import sys

EXPECTED_PACKET = "synthetic.cycles-scene-packet/v0.1"
EXPECTED_RENDER = "BLENDER_CYCLES_5_2_4_CPU"
SOURCE_GEOMETRY = {
    "root/cube": {"kind": "BOX", "dimensions": (1.25, 1.4, 1.4)},
    "root/sphere": {"kind": "SPHERE", "radius": 0.85},
}
OUTPUT_FILES = ("r167-scene.png", "r167-scene-receipt.json")


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def safe_paths(argv: list[str]) -> tuple[Path, Path]:
    if "--" not in argv or len(argv[argv.index("--") + 1:]) != 2:
        raise ValueError("required: -- existing-regular-input.json existing-private-output-dir")
    in_name, out_name = argv[argv.index("--") + 1:]
    source, target = Path(os.path.abspath(in_name)), Path(os.path.abspath(out_name))
    for p in (source, target):
        if any(x.is_symlink() for x in (p, *p.parents)):
            raise ValueError("symlink in input or output ancestry")
        if p.resolve(strict=True) != p:
            raise ValueError("noncanonical path")
    if not source.is_file() or source.stat().st_size > 65536:
        raise ValueError("input must be an existing small regular JSON file")
    if not target.is_dir():
        raise ValueError("output directory must preexist")
    if os.name != "nt" and target.stat().st_mode & 0o077:
        raise ValueError("output directory must deny group and other access")
    if any((target / name).exists() or (target / name).is_symlink()
           for name in OUTPUT_FILES):
        raise ValueError("will not overwrite result or symlink")
    return source, target


def load_packet(source: Path) -> tuple[dict, bytes]:
    raw = source.read_bytes()
    packet = json.loads(raw, parse_constant=lambda value:
                        (_ for _ in ()).throw(ValueError("nonfinite JSON token")))
    if not isinstance(packet, dict) or packet.get("schema") != EXPECTED_PACKET:
        raise ValueError("unsupported synthetic packet schema")
    if packet.get("variant") not in ("A", "B") or not isinstance(packet.get("request"), dict):
        raise ValueError("invalid synthetic request")
    req = packet["request"]
    if packet.get("source_fidelity") != "UNVERIFIED_SYNTHETIC_GEOMETRY_REGISTRY":
        raise ValueError("unqualified source-fidelity claim")
    options = req.get("options")
    if not isinstance(options, dict) or options.get("engine") != EXPECTED_RENDER:
        raise ValueError("unsupported renderer")
    if not all(isinstance(options.get(k), int) for k in ("width", "height", "samples", "seed")):
        raise ValueError("invalid render options")
    if not (64 <= options["width"] <= 2048 and 64 <= options["height"] <= 2048 and
            1 <= options["samples"] <= 256 and
            options["width"] * options["height"] * options["samples"] <= 100_000_000):
        raise ValueError("synthetic render exceeds budget")
    objects = req.get("objects")
    if not isinstance(objects, list) or {o.get("feature_path") for o in objects} != set(SOURCE_GEOMETRY):
        raise ValueError("unexpected synthetic source occurrence")
    if not all(isinstance(v, list) and len(v) == 3 for o in objects
               for v in (o.get("translation"),)):
        raise ValueError("malformed object transform")
    for o in objects:
        if any(not isinstance(n, (int, float)) or not math.isfinite(n) for n in o["translation"]):
            raise ValueError("nonfinite transform")
        if o.get("uniform_scale") != 1:
            raise ValueError("only unit source-safe scale admitted")
    if len(req.get("materials", [])) != 2 or len(req.get("cameras", [])) != 1 or len(req.get("lights", [])) != 1:
        raise ValueError("unexpected synthetic scene resource count")
    return packet, raw


def execute(packet: dict, input_bytes: bytes, output: Path) -> None:
    import bpy  # type: ignore[import-not-found]
    from mathutils import Matrix, Vector  # type: ignore[import-not-found]

    if tuple(bpy.app.version[:3]) != (5, 2, 4):
        raise RuntimeError("required official Blender 5.2.4 LTS")
    req = packet["request"]
    opts = req["options"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = opts["samples"]
    scene.cycles.seed = opts["seed"]
    scene.render.resolution_x = opts["width"]
    scene.render.resolution_y = opts["height"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output / OUTPUT_FILES[0])
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.view_settings.view_transform = "Standard"

    material_by_id = {}
    for spec in req["materials"]:
        mat = bpy.data.materials.new(spec["id"])
        rgba = tuple(spec["base_color"]) + (1.0,)
        mat.diffuse_color = rgba
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get("Principled BSDF")
        if shader is None:
            raise RuntimeError("Principled BSDF unavailable")
        shader.inputs["Base Color"].default_value = rgba
        shader.inputs["Metallic"].default_value = spec["metallic"]
        shader.inputs["Roughness"].default_value = spec["roughness"]
        material_by_id[spec["id"]] = mat

    object_positions = {}
    for spec in req["objects"]:
        shape = SOURCE_GEOMETRY[spec["feature_path"]]
        if shape["kind"] == "BOX":
            bpy.ops.mesh.primitive_cube_add(size=1)
            obj = bpy.context.object
            obj.dimensions = shape["dimensions"]
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(
                segments=48, ring_count=24, radius=shape["radius"])
            obj = bpy.context.object
        obj.name = "synthetic_" + spec["id"]
        obj.location = tuple(spec["translation"])
        obj.data.materials.append(material_by_id[spec["material_id"]])
        obj["synthetic_feature_path"] = spec["feature_path"]
        object_positions[spec["id"]] = list(obj.location)

    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.01))
    ground = bpy.context.object
    ground.name = "synthetic_ground"
    mat = bpy.data.materials.new("synthetic_ground_gray")
    mat.diffuse_color = (0.45, 0.45, 0.45, 1.0)
    ground.data.materials.append(mat)

    light = req["lights"][0]
    if light["type"] != "AREA":
        raise ValueError("source-free demo supports one area light")
    data = bpy.data.lights.new(light["id"], type="AREA")
    lamp = bpy.data.objects.new(light["id"], data)
    scene.collection.objects.link(lamp)
    lamp.location = tuple(light["position"])
    data.energy = light["power_watts"]
    data.shape = "DISK"
    data.size = light["size_meters"]
    lamp.rotation_euler = (Vector((0, 0, 0)) - lamp.location).to_track_quat("-Z", "Y").to_euler()

    camera = req["cameras"][0]
    data = bpy.data.cameras.new(camera["id"])
    eye = bpy.data.objects.new(camera["id"], data)
    scene.collection.objects.link(eye)
    eye.location = tuple(camera["position"])
    forward = (Vector(camera["target"]) - eye.location).normalized()
    up = Vector(camera["up"]).normalized()
    right = forward.cross(up).normalized()
    true_up = right.cross(forward).normalized()
    orientation = Matrix((right, true_up, -forward)).transposed()
    eye.rotation_euler = orientation.to_euler()
    data.angle = math.radians(camera["fov_degrees"])
    scene.camera = eye
    if scene.world is not None:
        scene.world.color = (0.08, 0.08, 0.08)

    bpy.ops.render.render(write_still=True)
    image = (output / OUTPUT_FILES[0]).read_bytes()
    if not image.startswith(b"\x89PNG\r\n\x1a\n") or len(image) < 1024:
        raise RuntimeError("Cycles did not emit plausible PNG")
    receipt = {
        "schema": "synthetic.cycles-render-receipt/v0.1",
        "status": "PUBLIC_SYNTHETIC_DONOR_EXECUTED_NOT_PRIVATE_SOURCE",
        "variant": packet["variant"],
        "source_fidelity": packet["source_fidelity"],
        "synthetic_request_fingerprint": packet["synthetic_request_fingerprint"],
        "source_binding": req["source"],
        "request_file_sha256": sha(input_bytes),
        "blender_version": bpy.app.version_string,
        "engine": opts["engine"],
        "objects": object_positions,
        "camera_position": list(eye.location),
        "light_energy": data.energy if False else light["power_watts"],
        "image_sha256": sha(image),
        "image_size": len(image),
        "resolution": [opts["width"], opts["height"]],
        "samples": opts["samples"],
        "limitations": [
            "Geometry comes from a fixed original synthetic registry, not Oneirifact",
            "Source binding digest is a synthetic placeholder, not an authenticated revision",
            "No private adapter, graph/CSG, scene hierarchy, rights or human preference acceptance",
        ],
    }
    fd = os.open(str(output / OUTPUT_FILES[1]), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(json.dumps(receipt, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == "__main__":
    p, folder = safe_paths(sys.argv)
    packet, raw = load_packet(p)
    execute(packet, raw, folder)
