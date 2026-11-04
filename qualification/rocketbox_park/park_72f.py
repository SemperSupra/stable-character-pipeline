"""72-frame original-source MIT two-camera park *candidate*, not human biomechanical acceptance.

Calls the untouched prior source-native six-texture verifier; derives only original
procedural park geometry, never protected real-person or non-MIT model input.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1] / "rocketbox_material"))
from native_material_uv import ACTORS, SOURCE_BLEND_SHA, SOURCE_COMMIT, native_run  # noqa: E402

FRAMES = 72
FPS = 12
SCHEMA = "scp.r009.original_mit_textured_park72.v1"
TREE_COORDS = ((-5.6, 3.8), (-4.1, 3.7), (4.1, 3.7), (5.6, 3.8),
               (-4.9, 5.2), (0.0, 5.7), (4.9, 5.2))


def check_park_geometry(coords):
    """Reject camera-facing occluders, actor-lane encroachment and invalid grounds."""
    if not coords:
        raise ValueError("NO_PARK_TREES")
    out = []
    seen = set()
    for point in coords:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("INVALID_TREE_COORDINATE")
        x, y = point
        if isinstance(x, bool) or isinstance(y, bool) or not all(
            isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y)
        ):
            raise ValueError("NONFINITE_TREE_COORDINATE")
        if y < 3.0:
            raise ValueError("TREE_IN_ACTOR_OR_CAMERA_FOREGROUND")
        if abs(x) < 3.5 and y < 5.0:
            raise ValueError("TREE_IN_TWO_ACTOR_ACTION_FRAMING")
        if (x, y) in seen:
            raise ValueError("DUPLICATE_PARK_TREE")
        seen.add((x, y))
        out.append((float(x), float(y)))
    return out


def sha256_bytes(blob):
    return hashlib.sha256(blob).hexdigest()


def create_material(bpy, name, rgb, roughness=0.8):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1.0)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    shader.inputs["Base Color"].default_value = (*rgb, 1.0)
    shader.inputs["Roughness"].default_value = roughness
    mat.node_tree.links.new(shader.outputs["BSDF"], out.inputs["Surface"])
    return mat


def cube(bpy, name, xyz, dims, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=xyz)
    ob = bpy.context.object
    ob.name = name
    ob.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.data.materials.append(material)
    return ob


def compose_park(bpy):
    check_park_geometry(TREE_COORDS)
    ground = bpy.data.objects.get("SourceProbeGround")
    if ground is None:
        raise RuntimeError("FROZEN_SOURCE_GROUND_MISSING")
    ground.hide_render = True
    grass = create_material(bpy, "OriginalProcedural_Grass", (0.23, 0.37, 0.21))
    path = create_material(bpy, "OriginalProcedural_Path", (0.56, 0.51, 0.43))
    bark = create_material(bpy, "OriginalProcedural_Bark", (0.31, 0.19, 0.09))
    canopy = create_material(bpy, "OriginalProcedural_Leaves", (0.11, 0.29, 0.10))
    cube(bpy, "OriginalPark_Lawn", (0, 1.2, -0.105), (14, 12, 0.16), grass)
    cube(bpy, "OriginalPark_Walkway", (0, 0.0, -0.024), (12, 2.7, 0.035), path)
    for idx, (x, y) in enumerate(TREE_COORDS):
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.18, depth=2.0,
                                            location=(x, y, 0.98))
        trunk = bpy.context.object
        trunk.name = "OriginalPark_Trunk_%02d" % idx
        trunk.data.materials.append(bark)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1.17,
                                              location=(x, y, 2.25))
        crown = bpy.context.object
        crown.name = "OriginalPark_Crown_%02d" % idx
        crown.data.materials.append(canopy)
    return {"path_width_m": 2.7, "trees": len(TREE_COORDS),
            "geometry_source": "PROJECT_AUTHORED_PROCEDURAL",
            "foreground_tree_rejection": "DETERMINISTIC_Y_GUARD_SOURCE_ONLY"}


def run(src, tex, output):
    import bpy
    from mathutils import Vector

    output.mkdir(parents=True, exist_ok=True)
    # This actual source-qualified operation performs all six official pinned
    # TGA checks and binds genuine 3-way original UV materials. It also renders
    # 4 previously qualified review frames before any park-specific changes.
    native_run(src, tex, output / "source-material-preflight")
    prior = json.loads((output / "source-material-preflight" /
                       "native_material_uv_receipt.json").read_text())
    if prior["uv_assignment"] != "SOURCE_LABELED_MIT_BODY_HEAD_OPACITY_BINDING_VERIFIED":
        raise RuntimeError("UPSTREAM_ACTUAL_MATERIAL_UV_NOT_VERIFIED")

    scene = bpy.context.scene
    park = compose_park(bpy)
    if scene.frame_start != 0 or scene.frame_end != 71 or scene.render.fps != FPS:
        raise RuntimeError("FROZEN_SOURCE_72F_CLOCK_INCOMPATIBLE")
    if len(ACTORS) != 2 or any(bpy.data.objects.get(x) is None for x in ACTORS):
        raise RuntimeError("ACTOR_PAIR_UNAVAILABLE")

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    scene.render.resolution_x = 480
    scene.render.resolution_y = 270
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.camera.data.type = "ORTHO"
    scene.camera.data.ortho_scale = 8.4
    views = [
        ("front", (0.0, -10.0, 2.5)),
        ("oblique", (2.6, -9.5, 3.0)),
    ]
    result = {
        "schema": SCHEMA, "status": "NATIVE_SOURCE_BOUND_72F_COLOR_PARK_CANDIDATE",
        "source_license": "MICROSOFT_ROCKETBOX_MIT_WITH_NOTICE",
        "source_commit": SOURCE_COMMIT, "source_blend_sha256": SOURCE_BLEND_SHA,
        "source_materials": "SIX_ORIGINAL_MIT_BODY_HEAD_OPACITY_TGAS_VERIFIED",
        "source_native_material_receipt_sha256":
            sha256_bytes((output / "source-material-preflight" /
                          "native_material_uv_receipt.json").read_bytes()),
        "procedural_scene": park, "actor_roots": list(ACTORS),
        "frames": FRAMES, "fps": FPS, "views": {},
        "realistic_human_gait": "UNKNOWN", "true_foot_contact": "UNKNOWN",
        "signed_human_rom": "NOT_RUN", "independent_human_visual_acceptance": "NOT_RUN",
        "real_person_identity": "NOT_APPLICABLE_FICTIONAL_MIT_AVATARS",
        "original_naomi_alison_mvp_accepted": False,
        "product_accepted": False,
    }
    manifest = output / "park_render_receipt.json"
    def save():
        manifest.write_text(json.dumps(result, sort_keys=True, indent=2,
                                       allow_nan=False) + "\n", encoding="utf-8")
    save()
    for view, position in views:
        scene.camera.location = position
        scene.camera.rotation_euler = (
            Vector((0, 0, 1.12)) - scene.camera.location
        ).to_track_quat("-Z", "Y").to_euler()
        dest = output / view
        dest.mkdir(exist_ok=True)
        hashes = []
        for frame in range(FRAMES):
            scene.frame_set(frame)
            image_path = dest / ("frame_%03d.png" % frame)
            scene.render.filepath = str(image_path)
            bpy.ops.render.render(write_still=True)
            raw = image_path.read_bytes()
            if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError("BROKEN_NATIVE_PNG:" + view + ":" + str(frame))
            hashes.append(sha256_bytes(raw))
        result["views"][view] = {
            "camera": [float(v) for v in position], "native_frame_count": len(hashes),
            "first_frame_sha256": hashes[0], "last_frame_sha256": hashes[-1],
            "all72_native_png_hashes": hashes,
        }
        save()
    print(json.dumps({"status": result["status"], "views": {x: len(y["all72_native_png_hashes"])
                    for x, y in result["views"].items()}, "product_accepted": False}))


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise RuntimeError("ARGS_REQUIRED")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 3:
        raise RuntimeError("USAGE original-native.blend six-mit-tga-dir output-dir")
    run(*(Path(x).resolve() for x in args))
