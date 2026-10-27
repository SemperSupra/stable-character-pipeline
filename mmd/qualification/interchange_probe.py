#!/usr/bin/env python3
"""G4: native MMD VMD -> skinned Blender animation -> glTF + sampled frames.

Uses the real pinned MMD Tools Blender add-on and original synthetic assets.
No external MMD models, motions, photos, textures or private source.
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys


def evaluated_centroid(obj, depsgraph):
    mesh_obj = obj.evaluated_get(depsgraph)
    mesh = mesh_obj.to_mesh()
    try:
        assert mesh and mesh.vertices, "export mesh has no evaluated vertices"
        world = mesh_obj.matrix_world
        positions = [world @ v.co for v in mesh.vertices]
        return [sum(float(p[i]) for p in positions) / len(positions) for i in range(3)]
    finally:
        mesh_obj.to_mesh_clear()


def main():
    p = argparse.ArgumentParser()
    for key in ("source", "model", "motion", "out"):
        p.add_argument("--" + key, required=True, type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    import bpy
    from mathutils import Vector
    assert bpy.app.version >= (4, 2, 0), bpy.app.version
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0, str(args.source.resolve()))
    import mmd_tools
    mmd_tools.register()
    result = bpy.ops.mmd_tools.import_model(
        filepath=str(args.model.resolve()), scale=1.0,
        types={"MESH", "ARMATURE"}, rename_bones=False, fix_bone_order=False)
    assert "FINISHED" in result, f"PMX import failed: {result}"
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    assert len(arms) == 1 and len(meshes) >= 1, (len(arms), len(meshes))
    arm = arms[0]
    assert arm.pose.bones.get("センター") is not None
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    result = bpy.ops.mmd_tools.import_vmd(
        filepath=str(args.motion.resolve()), scale=1.0,
        margin=0, bone_mapper="PMX", update_scene_settings=False)
    assert "FINISHED" in result, f"VMD import failed: {result}"

    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 0, 30
    scene.render.fps = 30
    positions = {}
    bone_positions = {}
    for f in (0, 15, 30):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        positions[str(f)] = evaluated_centroid(meshes[0], dg)
        bone_positions[str(f)] = [float(x) for x in arm.pose.bones["センター"].location]
    disp = math.dist(positions["0"], positions["30"])
    assert disp > 0.1, "VMD moved bone but did not visibly deform evaluated skin: " + str(positions)
    bone_disp = math.dist(bone_positions["0"], bone_positions["30"])
    assert bone_disp > 0.1, "VMD bone did not move"

    # Save editable source before interchange, preserving native imported action.
    bpy.ops.wm.save_as_mainfile(filepath=str((args.out / "animated_mmd.blend").resolve()))
    glb = args.out / "animated_mmd.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb.resolve()), export_format="GLB",
        export_animations=True, export_skins=True,
        export_force_sampling=True,
        export_anim_slide_to_zero=True)
    assert glb.stat().st_size > 1000, "GLB not exported"

    # Render *the imported and evaluated mesh*, not a substitute/proxy.
    # Keep unmodified original MMD materials in the already-exported GLB.
    # The synthetic PMX references toon01.bmp without a corresponding image;
    # our separate interchange proof uses a deliberate diagnostic emissive
    # display material, rather than claiming faithful MMD toon rendering.
    before_visibility = [{
        "name": obj.name, "type": obj.type,
        "hide_render": bool(obj.hide_render),
        "hide_viewport": bool(obj.hide_viewport)
    } for obj in bpy.data.objects if obj.type in ("MESH", "ARMATURE", "EMPTY")]
    for collection in bpy.data.collections:
        collection.hide_render = False
        collection.hide_viewport = False
    for obj in bpy.data.objects:
        if obj.type in ("MESH", "ARMATURE", "EMPTY"):
            obj.hide_render = False
            obj.hide_viewport = False
            obj.hide_set(False)
    diagnostic = bpy.data.materials.new("SCP_DIAGNOSTIC_EMISSION_NOT_MMD_SHADING")
    diagnostic.use_nodes = True
    diagnostic.diffuse_color = (0.9, 0.2, 0.05, 1.0)
    diagnostic.use_backface_culling = False
    nodes = diagnostic.node_tree.nodes
    nodes.clear()
    surface = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.95, 0.15, 0.02, 1.0)
    emission.inputs["Strength"].default_value = 3.0
    diagnostic.node_tree.links.new(emission.outputs["Emission"], surface.inputs["Surface"])
    for obj in meshes:
        obj.data.materials.clear()
        obj.data.materials.append(diagnostic)
    scene.view_settings.view_transform = "Standard"
    camera_data = bpy.data.cameras.new("G4 camera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 3.6
    camera = bpy.data.objects.new("G4 camera", camera_data)
    scene.collection.objects.link(camera)
    camera.location = (2.6, -3.4, 3.2)
    camera.rotation_euler = (Vector((0.0, 0.35, 0.0)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    light_data = bpy.data.lights.new("G4 light", "AREA")
    light_data.energy = 500
    light = bpy.data.objects.new("G4 light", light_data)
    scene.collection.objects.link(light)
    light.location = (1.0, -1.2, 3.5)
    light.rotation_euler = (Vector((0.0, 0.3, 0.0)) - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 2
    scene.render.resolution_x = 320
    scene.render.resolution_y = 240
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    for f in range(31):
        scene.frame_set(f)
        scene.render.filepath = str((args.out / f"frame_{f:04d}.png").resolve())
        bpy.ops.render.render(write_still=True)
        assert Path(scene.render.filepath).stat().st_size > 500, f"empty frame {f}"

    receipt = {
        "schema": "scp.mmd.interchange.v1",
        "result": "SOURCE_GENERATED_PENDING_INDEPENDENT_GLTF_AND_VIDEO_VALIDATION",
        "blender": bpy.app.version_string,
        "mmd_tools": mmd_tools.MMD_TOOLS_VERSION,
        "original_rights": "synthetic self-authored triangle, one-bone rig and 2-key VMD",
        "visual_material": "DIAGNOSTIC EMISSION ONLY, NOT faithful original MMD material or toon textures",
        "visibility_before_diagnostic": before_visibility,
        "frame_range": [0, 30],
        "fps": 30,
        "bone_centers": bone_positions,
        "evaluated_mesh_centroids": positions,
        "evaluated_mesh_displacement": disp,
        "native_glb": glb.name,
        "native_blend": "animated_mmd.blend",
        "frame_count": 31,
        "not_verified": ["IK parity", "MMD rigid body dynamics", "humanoid retarget", "morphs", "native MMD visual parity"]
    }
    (args.out / "interchange_source_receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    sys.stderr.flush()
    # Previous bpy 4.5 embedded Python teardown hung after successful export.
    # Only exit this way after all asserts, rendered frames and receipts succeed.
    os._exit(0)
