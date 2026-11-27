#!/usr/bin/env python3
"""Original, public-safe Blender Cycles scene donor probe (R139).

This tests Blender itself, NOT Oneirifact compiler integration, geometry fidelity,
source-pinned rendering, scene assembly, or visual realism/critic quality.

Run in a sandbox with a pinned authorized Blender 5.2.4 LTS installation:
  blender --background --factory-startup --disable-autoexec -t 2 \
    --python r139_cycles_synthetic.py -- /existing/private/output/dir
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

SCHEMA = "oneirifact.rdte.cycles-synthetic/v0.1"
OUTPUT_NAMES = ("r139-cycles.png", "r139-cycles-receipt.json")
FIXTURE = {
    "schema": SCHEMA,
    "fixture": "original-synthetic-two-solids-ground-and-area-light",
    "units": "m",
    "camera": {"location": [5.0, -7.0, 4.0], "target": [0.0, 0.0, 0.8]},
    "render": {"resolution": [320, 240], "samples": 32, "seed": 139},
    "objects": [
        {"id": "cube", "type": "box", "location": [-0.8, 0.0, 0.7]},
        {"id": "sphere", "type": "sphere", "location": [0.9, 0.0, 0.85]},
    ],
}


def stable_json(data: object) -> bytes:
    return (json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def digest(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def validate_output_dir(argv: list[str]) -> Path:
    if "--" not in argv:
        raise ValueError("expected -- followed by one preexisting output directory")
    extra = argv[argv.index("--") + 1:]
    if len(extra) != 1:
        raise ValueError("expected exactly one output directory")
    # abspath normalizes relative paths without following symlinks. Inspect
    # every ancestor rather than only the final path: symlinked parents can
    # otherwise escape the pre-existing private output custody directory.
    output = Path(os.path.abspath(extra[0]))
    for ancestor in (output, *output.parents):
        if ancestor.is_symlink():
            raise ValueError("output path traverses a symlink")
    try:
        resolved = output.resolve(strict=True)
    except OSError as exc:
        raise ValueError("output directory must already exist") from exc
    if resolved != output or not output.is_dir():
        raise ValueError("output must be an existing nonsymlink directory")
    if os.name != "nt" and output.stat().st_mode & 0o077:
        raise ValueError("output directory must deny group/other access")
    # Path.exists is false for dangling symlinks; bpy writes by filename and
    # must never be allowed to follow a pre-placed symlink output target.
    if any((output / name).exists() or (output / name).is_symlink()
           for name in OUTPUT_NAMES):
        raise ValueError("will not overwrite an existing donor output or symlink")
    return output


def execute(output: Path) -> None:
    # Import only within a real Blender process. Standard-Python source tests
    # deliberately exercise validation without pretending to execute Cycles.
    import bpy  # type: ignore[import-not-found]
    from mathutils import Vector  # type: ignore[import-not-found]

    if bpy.app.version[:3] != (5, 2, 4):
        raise RuntimeError("Blender 5.2.4 LTS required for this pinned donor fixture")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = FIXTURE["render"]["samples"]
    scene.cycles.seed = FIXTURE["render"]["seed"]
    scene.render.resolution_x, scene.render.resolution_y = FIXTURE["render"]["resolution"]
    scene.render.resolution_percentage = 100
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.filepath = str(output / OUTPUT_NAMES[0])

    def material(name: str, rgba: tuple[float, float, float, float], roughness: float):
        mat = bpy.data.materials.new(name=name)
        mat.diffuse_color = rgba
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is None:
            raise RuntimeError("expected Blender Principled BSDF")
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = roughness
        return mat

    blue = material("synthetic-blue", (0.08, 0.25, 0.7, 1), 0.34)
    red = material("synthetic-red", (0.75, 0.18, 0.12, 1), 0.22)
    neutral = material("synthetic-ground", (0.45, 0.45, 0.45, 1), 0.8)

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(-0.8, 0.0, 0.7))
    cube = bpy.context.object
    cube.name = "synthetic-cube"
    cube.dimensions = (1.25, 1.4, 1.4)
    cube.data.materials.append(blue)
    cube["r139_fixture_object_id"] = "cube"
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.85, location=(0.9, 0.0, 0.85))
    sphere = bpy.context.object
    sphere.name = "synthetic-sphere"
    sphere.data.materials.append(red)
    sphere["r139_fixture_object_id"] = "sphere"
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.01))
    bpy.context.object.data.materials.append(neutral)

    light_data = bpy.data.lights.new("synthetic-area", type="AREA")
    light = bpy.data.objects.new("synthetic-area", light_data)
    scene.collection.objects.link(light)
    light.location = (1, -3, 6)
    light_data.energy = 1000.0
    light_data.shape = "DISK"
    light_data.size = 5.0

    camera_data = bpy.data.cameras.new("synthetic-camera")
    camera = bpy.data.objects.new("synthetic-camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = tuple(FIXTURE["camera"]["location"])
    direction = Vector(FIXTURE["camera"]["target"]) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 45
    scene.camera = camera
    if scene.world is not None:
        scene.world.color = (0.1, 0.1, 0.1)

    bpy.ops.render.render(write_still=True)
    png = output / OUTPUT_NAMES[0]
    content = png.read_bytes()
    if not content.startswith(b"\x89PNG\r\n\x1a\n") or len(content) < 1024:
        raise RuntimeError("Cycles output missing or not PNG")
    receipt = {
        "schema": SCHEMA,
        "status": "SYNTHETIC_CYCLES_EXECUTED_UNVERIFIED",
        "fixture_sha256": digest(stable_json(FIXTURE)),
        "blender_version": bpy.app.version_string,
        "renderer": "CYCLES",
        "device": "CPU",
        "samples": scene.cycles.samples,
        "seed": scene.cycles.seed,
        "png_sha256": digest(content),
        "png_size_bytes": len(content),
        "limitations": [
            "Original synthetic donor only; no private Oneirifact source used",
            "No Oneirifact graph source or revision fidelity attested",
            "No independent visual or geometry acceptance claimed",
        ],
    }
    # New non-overwriting receipt; output was preflighted before invoking Blender.
    fd = os.open(str(output / OUTPUT_NAMES[1]), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(json.dumps(receipt, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        f.flush()
        os.fsync(f.fileno())


if __name__ == "__main__":
    execute(validate_output_dir(sys.argv))
