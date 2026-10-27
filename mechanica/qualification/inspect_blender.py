#!/usr/bin/env python3
"""Independent Blender headless GLB import, rig sampling, and CPU contact-frame probe.

Read-only: consumes immutable public previews, never edits the generator or the source GLB.
Media qualification is distinct from human visual approval, physics/IK, or iPhone playback.
"""
import argparse
import hashlib
import json
import math
import pathlib
import sys
import traceback

import bpy
from mathutils import Vector

EXPECTED_SHA = "ee3f027a2d1e05b9a1b44dd5c5569a19b35dd4d1"
EXPECTED_RIGS = ("ground/suv", "air/utility-twin", "space/orbital-tug", "titan/iron-atlas")
FRAC_TIMES = (0.0, 0.25, 0.5, 0.75, 1.0)


class QualificationError(Exception):
    pass


def require(ok, why):
    if not ok:
        raise QualificationError(why)


def bounds(mesh_objects):
    xyz = []
    for obj in mesh_objects:
        for pt in obj.bound_box:
            xyz.append(obj.matrix_world @ Vector(pt))
    require(xyz, "no world-space mesh bounds")
    lo = Vector(tuple(min(q[k] for q in xyz) for k in range(3)))
    hi = Vector(tuple(max(q[k] for q in xyz) for k in range(3)))
    require(all(math.isfinite(v) for v in (*lo, *hi)), "nonfinite imported mesh bounds")
    return lo, hi


def projected_corners(mesh_objects):
    return [obj.matrix_world @ Vector(pt)
            for obj in mesh_objects for pt in obj.bound_box]


def frame_receipt(scene, cam, mesh_objects, min_margin=0.075):
    # Independent test in actual Blender camera NDC, not the same arithmetic
    # used to select ortho_scale. Render borders are x/y in [0,1].
    from bpy_extras.object_utils import world_to_camera_view
    corners = projected_corners(mesh_objects)
    require(corners, "camera framing: no geometry")
    values = [world_to_camera_view(scene, cam, pt) for pt in corners]
    xlo, xhi = min(v.x for v in values), max(v.x for v in values)
    ylo, yhi = min(v.y for v in values), max(v.y for v in values)
    require(all(math.isfinite(v) for v in (xlo, xhi, ylo, yhi)),
            "camera framing has nonfinite projected coordinates")
    margin = min(xlo, 1 - xhi, ylo, 1 - yhi)
    require(margin >= min_margin,
            f"camera clips geometry or lacks safe margin: {margin:.5f} "
            f"(x={xlo:.4f}..{xhi:.4f}; y={ylo:.4f}..{yhi:.4f})")
    return {"x_min": round(xlo, 5), "x_max": round(xhi, 5),
            "y_min": round(ylo, 5), "y_max": round(yhi, 5),
            "minimum_safe_margin": round(margin, 5)}


def set_camera(mesh_objects, frame):
    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    lo, hi = bounds(mesh_objects)
    center = (lo + hi) * 0.5
    span = max(hi - lo)
    require(span > 0.1 and span < 1000, "implausible mesh bounds")
    cam_data = bpy.data.cameras.new("qualification-camera-data")
    cam = bpy.data.objects.new("qualification-camera", cam_data)
    scene.collection.objects.link(cam)
    direction = Vector((1.15, -1.4, 0.9)).normalized()
    cam.location = center + direction * span * 2.7
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.type = "ORTHO"
    scene.camera = cam
    bpy.context.view_layer.update()

    corners = projected_corners(mesh_objects)
    local = [cam.matrix_world.inverted() @ pt for pt in corners]
    xlo, xhi = min(v.x for v in local), max(v.x for v in local)
    ylo, yhi = min(v.y for v in local), max(v.y for v in local)
    aspect = ((scene.render.resolution_x * scene.render.pixel_aspect_x) /
              (scene.render.resolution_y * scene.render.pixel_aspect_y))
    # Blender ortho_scale measures horizontal span, not world-Z bounding height.
    # The previous span*1.75 erroneously ignored 16:9 aspect and clipped Titan.
    cam_data.ortho_scale = max(xhi - xlo, (yhi - ylo) * aspect) * 1.36
    center_offset = cam.matrix_world.to_quaternion() @ Vector(
        ((xlo + xhi) * 0.5, (ylo + yhi) * 0.5, 0))
    cam.location += center_offset
    bpy.context.view_layer.update()

    fitted = frame_receipt(scene, cam, mesh_objects)
    # Red-team negative control: shrink fitted camera until projected geometry
    # clips, proving the checker detects the exact previously observed defect.
    correct_scale = cam_data.ortho_scale
    cam_data.ortho_scale = correct_scale * 0.35
    bpy.context.view_layer.update()
    clipped_detected = False
    try:
        frame_receipt(scene, cam, mesh_objects)
    except QualificationError:
        clipped_detected = True
    finally:
        cam_data.ortho_scale = correct_scale
        bpy.context.view_layer.update()
    require(clipped_detected, "tight-camera negative control escaped")
    return (cam, [round(float(v), 4) for v in lo],
            [round(float(v), 4) for v in hi], fitted)


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    # Ubuntu's Blender 4.0.2 package lacks OpenImageDenoiser; never invoke it.
    # Denoising is a renderer option, not a condition for assessing articulation.
    for layer in scene.view_layers:
        if hasattr(layer, "cycles"):
            layer.cycles.use_denoising = False
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    scene.render.resolution_x = 480
    scene.render.resolution_y = 270
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("qualification-world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.12, 0.14, 0.18, 1)
        bg.inputs["Strength"].default_value = 0.8
    light_data = bpy.data.lights.new("qualification-area-light-data", "AREA")
    light_data.energy = 4500
    light_data.shape = "DISK"
    light_data.size = 24
    light = bpy.data.objects.new("qualification-area-light", light_data)
    scene.collection.objects.link(light)
    light.location = (8, -12, 24)
    light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()


def write_json(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def imported_action_extent(scene):
    spans = []
    for action in bpy.data.actions:
        lo, hi = action.frame_range
        if hi > lo:
            spans.append([float(lo), float(hi)])
    require(spans, "Blender did not import animation actions")
    return min(s[0] for s in spans), max(s[1] for s in spans), spans


def sample_world_motion(joints, frames, scene):
    transforms = {name: [] for name in joints}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name, obj in joints.items():
            vals = [round(float(v), 5) for row in obj.matrix_world for v in row]
            require(all(math.isfinite(v) for v in vals),
                    "nonfinite Blender world matrix: " + name)
            transforms[name].append(vals)
    changed = []
    static = []
    for name, snapshots in transforms.items():
        max_delta = max(
            max(abs(a - b) for a, b in zip(snapshots[0], sample))
            for sample in snapshots[1:]
        )
        (changed if max_delta > 0.0005 else static).append(name)
    return sorted(changed), sorted(static)


def verify_rig(scene, manifest):
    joints_by_name = {
        j["Name"]: j
        for rig in manifest["Rigs"] for j in rig["Joints"]
    }
    require(len(joints_by_name) == 50, "expected 50 uniquely named rig joints")
    all_objs = list(bpy.data.objects)
    mesh_objects = [x for x in all_objs if x.type == "MESH"]
    require(len(mesh_objects) >= 110, "Blender imported too few mesh objects")
    require(sum(len(x.vertices) for x in (o.data for o in mesh_objects)) > 2000,
            "imported meshes appear empty")
    objects = {j: bpy.data.objects.get(j) for j in joints_by_name}
    missing = [j for j, obj in objects.items() if obj is None]
    require(not missing, "Blender missing named joint objects: " + ", ".join(missing[:8]))
    joints = {j: obj for j, obj in objects.items()}
    nonempty_parent = [
        j for j, obj in joints.items() if obj.parent is not None
    ]
    require(len(nonempty_parent) == len(joints),
            "orphaned mechanical joint(s) detected")
    start, stop, actions = imported_action_extent(scene)
    require(stop - start >= 8, "animation duration appears truncated in Blender")
    frames = [
        round(start + (stop - start) * frac)
        for frac in FRAC_TIMES
    ]
    require(len(set(frames)) == len(frames), "animation sample frames overlap")
    moving, static = sample_world_motion(joints, frames, scene)
    require(len(moving) >= 35,
            "too few animated world-space joint transforms: " + str(len(moving)))
    rig_summary = {}
    for rig in manifest["Rigs"]:
        names = [j["Name"] for j in rig["Joints"]]
        rig_moving = sorted(set(names) & set(moving))
        require(len(rig_moving) >= max(2, len(names) // 2),
                "Blender movement absent in rig " + rig["Name"])
        rig_summary[rig["Name"]] = {
            "joint_count": len(names), "moving_joint_count": len(rig_moving)
        }
    return mesh_objects, frames, actions, moving, static, rig_summary


def execute(args):
    preview = pathlib.Path(args.preview_dir).resolve()
    manifest = json.loads((preview / "rig_manifest.json").read_text())
    provenance = dict(
        line.split("=", 1)
        for line in (preview / "provenance.txt").read_text().splitlines()
        if "=" in line
    )
    require(provenance.get("source_sha") == EXPECTED_SHA,
            "pinned preview source digest mismatch")
    require({r["Name"] for r in manifest["Rigs"]} == set(EXPECTED_RIGS),
            "unexpected Mechanica rig inventory")
    glb = preview / "mechanical_scene.glb"
    require(glb.is_file() and glb.stat().st_size > 10000, "GLB not present")
    sha256 = hashlib.sha256(glb.read_bytes()).hexdigest()
    require(sha256 == "19573f420f8c089842a04ec15664afb35829d587ed87a81c45ee00752c3a1aa8",
            "published GLB content hash mismatch")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    scene = bpy.context.scene
    mesh_objects, frames, actions, moving, static, rig_summary = verify_rig(
        scene, manifest
    )
    reports = {
        "schema": "mechanica.blender_qualification.v1",
        "status": "PASS_IMPORT_AND_ARTICULATION",
        "blender_version": bpy.app.version_string,
        "source_sha": EXPECTED_SHA,
        "glb_sha256": sha256,
        "imported_object_count": len(bpy.data.objects),
        "imported_mesh_count": len(mesh_objects),
        "imported_actions": len(actions),
        "action_ranges": actions[:15],
        "sampled_frames": frames,
        "moving_joint_count": len(moving),
        "static_joint_count": len(static),
        "static_joint_names": static,
        "rigs": rig_summary,
        "cpu_render_frames": [],
        "gate_limit": "Blender structural and sampled-world-motion only; not physics or visual human signoff"
    }
    setup_render()
    out = pathlib.Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Full-scene and independent per-rig closeups are separate evidence.
    first_frame, middle_frame, last_frame = frames[0], frames[2], frames[-1]
    focus_sets = {
        "scene": mesh_objects,
        "titan": [obj for obj in mesh_objects
                  if obj.name.startswith("titan/iron-atlas/")],
        "space": [obj for obj in mesh_objects
                  if obj.name.startswith("space/")],
    }
    require(all(focus_sets.values()), "missing rig geometry for close-up views")
    for focus, selected in focus_sets.items():
        for frame in (first_frame, middle_frame, last_frame):
            for obj in mesh_objects:
                obj.hide_render = bool(focus != "scene" and obj not in selected)
            cam, lo, hi, camera_fit = set_camera(selected, frame)
            name = f"{focus}_frame_{frame:04d}.png"
            output = out / name
            scene.render.filepath = str(output)
            bpy.ops.render.render(write_still=True)
            require(output.is_file() and output.stat().st_size > 2500,
                    "Blender did not produce substantial PNG: " + name)
            reports["cpu_render_frames"].append({
                "file": name, "frame": frame, "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "world_bbox_min": lo, "world_bbox_max": hi,
                "camera_framing": camera_fit,
                "tight_camera_negative_control_detected": True,
            })
            bpy.data.objects.remove(cam, do_unlink=True)
    require(len({s["sha256"] for s in reports["cpu_render_frames"]}) == len(samples),
            "Blender rendered identical PNGs across different articulation samples")
    reports["status"] = "PASS_BLENDER_IMPORT_MOTION_AND_RENDER"
    return reports


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-dir")
    parser.add_argument("--output-dir")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:]
                             if "--" in sys.argv else [])
    require(args.preview_dir and args.output_dir, "required --preview-dir and --output-dir")
    out = pathlib.Path(args.output_dir)
    try:
        report = execute(args)
    except Exception as exc:
        report = {
            "schema": "mechanica.blender_qualification.v1",
            "status": "FAIL", "first_failure": str(exc),
            "traceback": traceback.format_exc()[-5500:],
            "blender_version": bpy.app.version_string
        }
    write_json(out / "blender_report.json", report)
    print("MECHANICA_BLENDER_REPORT=" + json.dumps(report, sort_keys=True))
    if report["status"] != "PASS_BLENDER_IMPORT_MOTION_AND_RENDER":
        sys.exit(1)


if __name__ == "__main__":
    main()
