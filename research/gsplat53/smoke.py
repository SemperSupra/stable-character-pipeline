#!/usr/bin/env python3
"""Real Blender 5.3 background import/render/edit smoke, synthetic public assets only."""
import hashlib
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(os.environ.get("BAKEOFF_OUT", "out/gsplat53")).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
PLY = Path(os.environ.get("BAKEOFF_PLY", "out/synthetic_gaussians.ply")).resolve()
DELTA_M = 0.6096
SCENE_UNITS = "meter"

def world():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 8
    scene.render.resolution_x = 160
    scene.render.resolution_y = 160
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    camera_data = bpy.data.cameras.new("orthographic-matched")
    camera = bpy.data.objects.new("orthographic-matched", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (0.0, -4.0, 0.0)
    direction = Vector((0,0,0)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.1
    scene.camera = camera
    return scene

def measure(scene, label):
    output = ROOT / (label + ".png")
    scene.render.filepath = str(output)
    started = time.monotonic()
    bpy.ops.render.render(write_still=True)
    render_ms = int((time.monotonic() - started) * 1000)
    if not output.exists():
        raise RuntimeError("render did not produce PNG")
    image = bpy.data.images.load(str(output), check_existing=False)
    try:
        pix = image.pixels[:]
        w,h = image.size
        hits = []
        for y in range(h):
            for x in range(w):
                a = pix[4*(y*w+x)+3]
                if a > 0.10:
                    hits.append((x, y, a))
        if not hits:
            raise AssertionError("render produced no visible alpha pixels: " + label)
        weight = sum(p[2] for p in hits)
        cx = sum(p[0]*p[2] for p in hits) / weight
        cy = sum(p[1]*p[2] for p in hits) / weight
    finally:
        bpy.data.images.remove(image)
    return {"file": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "render_ms": render_ms, "alpha_pixel_count": len(hits),
            "centroid_x": round(cx,3), "centroid_y": round(cy,3),
            "resolution": [w,h]}

def exercise(kind):
    scene = world()
    before_names = set(o.name for o in bpy.data.objects)
    if kind == "splat":
        bpy.ops.wm.ply_import(filepath=str(PLY))
        imports = [o for o in bpy.data.objects if o.name not in before_names]
        if len(imports) != 1:
            raise AssertionError(f"expected exactly 1 imported object, got {len(imports)}")
        obj = imports[0]
        if obj.type != "POINTCLOUD":
            raise AssertionError(f"expected Blender 5.3 POINTCLOUD, got {obj.type}")
        pc_type = str(getattr(obj.data, "type", "UNAVAILABLE"))
        if pc_type != "GAUSSIAN_SPLAT":
            raise AssertionError(f"expected GAUSSIAN_SPLAT type, got {pc_type}")
    else:
        bpy.ops.mesh.primitive_cube_add(size=0.65)
        obj = bpy.context.object
        pc_type = "MESH"
    obj.location = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()
    a = measure(scene, kind + "_origin")
    obj.location.x = DELTA_M
    bpy.context.view_layer.update()
    b = measure(scene, kind + "_translated")
    displacement = b["centroid_x"] - a["centroid_x"]
    if abs(obj.location.x-DELTA_M) > 1e-8:
        raise AssertionError("loss of geometric edit precision")
    expected_px = scene.render.resolution_x * DELTA_M / scene.camera.data.ortho_scale
    if not (math.isfinite(displacement) and abs(displacement-expected_px) <= 1.0):
        raise AssertionError(
            f"{kind}: observed {displacement:.3f}px vs {expected_px:.3f}px projection truth"
        )
    return {"kind":kind,"native_type":obj.type,"pointcloud_type":pc_type,
            "translation_m":DELTA_M,"pixel_shift_x":round(displacement,3),
            "expected_pixel_shift_x":round(expected_px,3),
            "pixel_shift_error_x":round(displacement-expected_px,3),
            "at_origin":a,"after_edit":b}

def main():
    if not PLY.exists():
        raise RuntimeError(f"fixture missing: {PLY}")
    if bpy.app.version[:2] != (5, 3):
        raise AssertionError(f"not Blender 5.3: {bpy.app.version_string}")
    info = {
        "bakeoff":"gsplat53-CPU-R0", "status":"FAIL",
        "limit":"synthetic import and rendered rigid edit only, not trained reconstruction, rigging or realism",
        "blender_version":bpy.app.version_string, "python_version":sys.version,
        "platform":platform.platform(), "render_device":"CPU", "render_engine":"CYCLES",
        "fixture_sha256":hashlib.sha256(PLY.read_bytes()).hexdigest(),
        "source_commit":os.environ.get("GITHUB_SHA","LOCAL"),
        "units":SCENE_UNITS,"camera":"orthographic locked; origin (0,-4,0); scale 2.1",
        "trials": []
    }
    try:
        for kind in ("mesh","splat"):
            info["trials"].append(exercise(kind))
        info["status"] = "PASS"
    except BaseException as exc:
        info["error"] = {"type":type(exc).__name__, "message":str(exc)}
        raise
    finally:
        (ROOT/"receipt.json").write_text(json.dumps(info,indent=2,sort_keys=True)+"\n")
        print(json.dumps(info,indent=2,sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
