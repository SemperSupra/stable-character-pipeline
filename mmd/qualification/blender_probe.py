#!/usr/bin/env python3
"""Real Blender 4.5+ MMD Tools PMX import, CPU render, blend and GLB inspection."""
import argparse
import json
import os
from pathlib import Path
import sys

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    import bpy
    from mathutils import Vector
    if tuple(bpy.app.version[:2]) < (4, 2):
        raise RuntimeError("MMD Tools v4.5.14 requires Blender >= 4.2")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0, str(args.source.resolve()))
    import mmd_tools
    mmd_tools.register()
    outcome = bpy.ops.mmd_tools.import_model(
        filepath=str(args.fixture.resolve()),
        types={"MESH", "ARMATURE"}, scale=1.0,
        rename_bones=False, fix_bone_order=False
    )
    assert "FINISHED" in outcome, outcome
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    assert meshes and arms, "Real MMD Tools import produced no mesh or armature"
    bone_names = {b.name for arm in arms for b in arm.data.bones}
    assert "センター" in bone_names or "Center" in bone_names, sorted(bone_names)
    assert sum(len(o.data.vertices) for o in meshes) >= 3

    camera = bpy.data.cameras.new("SCP proof camera")
    obj = bpy.data.objects.new("SCP proof camera", camera)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = (0., -3., 3.)
    obj.rotation_euler = (Vector((0., 0., 0.)) - obj.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = obj
    lamp = bpy.data.lights.new("SCP softbox", "AREA")
    lamp.energy = 800
    light = bpy.data.objects.new("SCP softbox", lamp)
    bpy.context.scene.collection.objects.link(light)
    light.location = (1., -2., 3.)
    light.rotation_euler = (Vector((0., 0., 0.)) - light.location).to_track_quat("-Z", "Y").to_euler()
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 4
    scene.render.resolution_x = 256
    scene.render.resolution_y = 256
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str((args.out / "pmx_triangle.png").resolve())
    bpy.ops.render.render(write_still=True)
    assert (args.out / "pmx_triangle.png").stat().st_size > 1000
    bpy.ops.wm.save_as_mainfile(filepath=str((args.out / "pmx_triangle.blend").resolve()))
    bpy.ops.export_scene.gltf(filepath=str((args.out / "pmx_triangle.glb").resolve()), export_format="GLB")
    assert (args.out / "pmx_triangle.glb").stat().st_size > 1000
    assert (args.out / "pmx_triangle.blend").stat().st_size > 1000
    report = {
      "schema": "scp.mmd.blender.v1",
      "result": "PASS_REAL_BLENDER_PMX_IMPORT_RENDER_GLTF",
      "blender_version": bpy.app.version_string,
      "mmd_tools_version": mmd_tools.MMD_TOOLS_VERSION,
      "armatures": [{"name": arm.name, "bones": [b.name for b in arm.data.bones]} for arm in arms],
      "mesh_vertex_counts": [len(obj.data.vertices) for obj in meshes],
      "scope": "PMX import + mesh/bone inspection, Cycles CPU PNG, editable .blend and GLB; VMD, IK, MMD physics not qualified"
    }
    (args.out / "blender_receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    # Only bypass Python/blender shared-library teardown after all validation,
    # source exports, receipt writes and output checks have completed.
    # Public GHA rep 40423130061 finished those in <1s, but embedded bpy 4.5
    # hung during interpreter teardown until the job's 7-minute hard timeout.
    main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
