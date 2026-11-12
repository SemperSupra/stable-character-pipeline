"""R014: non-destructive Surface Deform cage bakeoff on actual failed CC0 sculpt -> MPFB rig.

Bounded research. The input .blend and original rig are preserved. Never qualifies
anatomy, L3 sculpt, photorealism, collisions or final character animation.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view

p = argparse.ArgumentParser()
p.add_argument("--sex", choices=("female", "male"), required=True)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--baseline", type=Path, required=True)
p.add_argument("--out", type=Path, required=True)
args = p.parse_args(sys.argv[sys.argv.index("--") + 1:])
args.out.mkdir(parents=True, exist_ok=True)
assert Path(bpy.data.filepath).resolve() == args.source.resolve()
baseline = json.loads(args.baseline.read_text())
assert baseline["sex_source_macro"] == {"female": 0.0, "male": 1.0}[args.sex]
assert baseline["source_mesh_vertices"] == 13380
assert baseline["target_mesh_vertices"] == 10582

source = bpy.data.objects["R014_" + args.sex + "_body_clean_export"]
target = bpy.data.objects["GEO-body_" + args.sex + "_realistic"]
rigs = [m.object for m in source.modifiers if m.type == "ARMATURE" and m.object]
assert len(rigs) == 1
rig = rigs[0]
assert len(rig.data.bones) == 163
assert len(source.data.vertices) == 13380 and len(target.data.vertices) == 10582
original_modifiers = [(m.name, m.type) for m in target.modifiers]

# The earlier held source scene retained an incorrect object transform. Repair
# only the experimental in-memory copy, with displacement captured in receipt.
source.hide_set(False)
source.hide_viewport = False
for bname in ("upperarm01.L", "upperleg01.L"):
    pb = rig.pose.bones[bname]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()


def points(obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        return np.array([list(evaluated.matrix_world @ v.co) for v in mesh.vertices],
                        dtype=np.float64)
    finally:
        evaluated.to_mesh_clear()


def base_points(obj):
    return np.array([list(obj.matrix_world @ v.co) for v in obj.data.vertices],
                    dtype=np.float64)


src = base_points(source)
tgt = base_points(target)
original_offset = src.mean(axis=0) - tgt.mean(axis=0)
if float(np.linalg.norm(original_offset)) > 4.0:
    raise ValueError("Unbounded source/sculpt rest transform mismatch: " +
                     repr(original_offset.tolist()))
# For this test alone, align mean positions; NOT anatomical correspondence.
target.location += Vector(original_offset.tolist())
bpy.context.view_layer.update()
tgt = base_points(target)

source.data.calc_loop_triangles()
src_faces = [tuple(t.vertices) for t in source.data.loop_triangles]
bvh = BVHTree.FromPolygons([Vector(v.tolist()) for v in src],
                           src_faces, all_triangles=True)
nearest = []
for v in tgt:
    hit = bvh.find_nearest(Vector(v.tolist()))
    if hit[0] is None:
        raise ValueError("Source BVH had no nearest surface")
    nearest.append(float(hit[3]))
nearest = np.array(nearest, dtype=np.float64)
registration_p95 = float(np.percentile(nearest, 95))
registration_far = float(np.mean(nearest > 0.05))

# Original nearest triangle vertex weights already failed; remove ONLY their
# experimental deformer. Retain vertex groups so they can be inspected later.
for modifier in list(target.modifiers):
    if modifier.type == "ARMATURE" and modifier.name.startswith("R014_Experimental"):
        target.modifiers.remove(modifier)
multires = [m for m in target.modifiers if m.type == "MULTIRES"]
for m in multires:
    m.show_viewport = True
    m.show_render = True
    m.levels = 0
    m.sculpt_levels = 0
    m.render_levels = 0

# A surface cage transmits the existing good rig deformation without copying
# bone weights onto the different sculpt topology. Large source/sculpt offsets
# can still cause catastrophic artifacts: fail-closed independent tests follow.
bpy.ops.object.select_all(action="DESELECT")
target.select_set(True)
bpy.context.view_layer.objects.active = target
cage = target.modifiers.new("R014_Experimental_Surface_Cage", "SURFACE_DEFORM")
cage.target = source
cage.falloff = 4.0
reorder_error = None
for _ in range(len(target.modifiers)):
    old = target.modifiers.find(cage.name)
    if old == 0:
        break
    try:
        bpy.ops.object.modifier_move_up(modifier=cage.name)
    except Exception as ex:
        reorder_error = str(ex)[:300]
        break
    if target.modifiers.find(cage.name) >= old:
        reorder_error = "Modifier precedence could not be changed"
        break
bpy.context.view_layer.update()
bind_error = reorder_error
try:
    outcome = bpy.ops.object.surfacedeform_bind(modifier=cage.name)
    if "FINISHED" not in outcome or not cage.is_bound:
        bind_error = "Blender SurfaceDeform bind did not produce bound modifier"
except Exception as ex:
    bind_error = type(ex).__name__ + ": " + str(ex)

target.data.calc_loop_triangles()
triangles = np.array([list(t.vertices) for t in target.data.loop_triangles], dtype=int)


def geometry_quality(neutral, moved):
    if len(neutral) != len(moved):
        return {"status": "FAIL_VERTEX_CENSUS_CHANGED",
                "rest_vertices": len(neutral), "posed_vertices": len(moved)}
    a0, b0, c0 = (neutral[triangles[:, j]] for j in range(3))
    a1, b1, c1 = (moved[triangles[:, j]] for j in range(3))
    n0 = np.cross(b0 - a0, c0 - a0)
    n1 = np.cross(b1 - a1, c1 - a1)
    mag0 = np.linalg.norm(n0, axis=1)
    mag1 = np.linalg.norm(n1, axis=1)
    valid = mag0 > 1e-11
    inverted_mask = valid & ((n0 * n1).sum(axis=1) <= 0)
    collapsed_mask = valid & (mag1 < mag0 * 0.10)
    bad = int(np.count_nonzero(inverted_mask))
    collapse = int(np.count_nonzero(collapsed_mask))

    # Produce actionable original mesh face IDs / world-space locations rather
    # than only counting inversions. Values are forensic samples, not semantic
    # anatomical labels (the rig-to-sculpt correspondence is still invalid).
    ratio = mag1 / np.maximum(mag0, 1e-11)
    implicated = np.flatnonzero(inverted_mask | collapsed_mask)
    bad_faces = []
    for face_id in implicated[:80]:
        verts = [int(x) for x in triangles[face_id]]
        bad_faces.append({
            "face_index": int(face_id),
            "mesh_vertex_ids": verts,
            "rest_centroid_world_m": neutral[triangles[face_id]].mean(axis=0).tolist(),
            "posed_centroid_world_m": moved[triangles[face_id]].mean(axis=0).tolist(),
            "posed_to_rest_area_ratio": float(ratio[face_id]),
            "orientation_flipped": bool(inverted_mask[face_id]),
            "severe_area_collapse": bool(collapsed_mask[face_id]),
        })
    move = np.linalg.norm(moved - neutral, axis=1)
    return {
        "rest_vertices": len(neutral),
        "posed_vertices": len(moved),
        "triangles": len(triangles),
        "degenerate_neutral_triangles": int(np.count_nonzero(~valid)),
        "inverted_triangles": bad,
        "area_below_10pct": collapse,
        "implicated_face_count": int(len(implicated)),
        "implicated_face_samples": bad_faces,
        "face_sample_limit": 80,
        "max_vertex_motion_m": float(move.max()),
        "p95_vertex_motion_m": float(np.percentile(move, 95)),
        "moving_vertices_gt_1mm": int(np.count_nonzero(move > .001)),
    }


scene = bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()
neutral = points(target)
for name, angle in (("upperarm01.L", .32), ("upperleg01.L", -.20)):
    rig.pose.bones[name].rotation_euler[1] = angle
bpy.context.view_layer.update()
posed = points(target)
quality = geometry_quality(neutral, posed)

# Test whether actual author-sculpted Multires data still evaluates AFTER
# the cage deformation (not a new subdivided low-poly imitation).
lod = {"authored_levels": [m.total_levels for m in multires], "level_1": "NOT_RUN"}
if multires and cage.is_bound:
    try:
        for m in multires:
            m.levels = 1
        bpy.context.view_layer.update()
        l1 = points(target)
        lod["level_1"] = ("EVALUATED" if len(l1) == 42342
                          else "HOLD_WRONG_VERTEX_COUNT")
        lod["level_1_evaluated_vertices"] = len(l1)
    except Exception as ex:
        lod["level_1"] = "HOLD_EVALUATION_ERROR"
        lod["level_1_error"] = str(ex)[:300]
    finally:
        for m in multires:
            m.levels = 0
        bpy.context.view_layer.update()

# Separate technical renders are useful even for a rejected cage attempt.
for name, angle in (("upperarm01.L", .0), ("upperleg01.L", .0)):
    rig.pose.bones[name].rotation_euler[1] = angle
bpy.context.view_layer.update()
original_materials = [m.name for m in target.data.materials if m]
target.data.materials.clear()
clay = bpy.data.materials.new("R014_HOLD_Cage_Technical_Clay")
clay.diffuse_color = (0.65, 0.61, 0.56, 1)
target.data.materials.append(clay)
source.hide_render = True
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 8
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.resolution_x = 512
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("R014_Cage_QA_World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
scene.world = world
lightdata = bpy.data.lights.new("R014_Cage_QA_Light", "AREA")
light = bpy.data.objects.new("R014_Cage_QA_Light", lightdata)
bpy.context.collection.objects.link(light)
lightdata.energy = 650
lightdata.size = 3
camdata = bpy.data.cameras.new("R014_Cage_QA_Camera")
cam = bpy.data.objects.new("R014_Cage_QA_Camera", camdata)
bpy.context.collection.objects.link(cam)
scene.camera = cam
camdata.type = "ORTHO"
both = np.vstack([neutral, posed])
lower = both.min(axis=0)
upper = both.max(axis=0)
middle = .5 * (upper + lower)
size = upper - lower
camdata.ortho_scale = max(float(size[2]) * 1.35,
                          float(size[0]) / (.8) * 1.35, 2.1)
cam.location = (float(middle[0]), float(middle[1] - max(4, size[1] * 3)),
                float(middle[2]))
cam.rotation_euler = (Vector(middle.tolist()) -
                      cam.location).to_track_quat("-Z", "Y").to_euler()
light.location = (float(middle[0] + 1), float(middle[1] - 2),
                  float(middle[2] + 2))
bpy.context.view_layer.update()
def coverage(pts):
    views = [world_to_camera_view(scene, cam, Vector(x.tolist()))
             for x in pts]
    px = np.array([[x.x, x.y, x.z] for x in views])
    return {"min_xy": px[:, :2].min(axis=0).tolist(),
            "max_xy": px[:, :2].max(axis=0).tolist(),
            "min_depth": float(px[:, 2].min())}

camera = {"neutral": coverage(neutral), "posed": coverage(posed)}
clipped = any(
    min(v["min_xy"]) <= 0 or max(v["max_xy"]) >= 1 or v["min_depth"] <= 0
    for v in camera.values())
render_error = None
if not clipped:
    try:
        for phase in ("neutral", "posed"):
            for name, angle in (("upperarm01.L", .32 if phase == "posed" else 0),
                                ("upperleg01.L", -.20 if phase == "posed" else 0)):
                rig.pose.bones[name].rotation_euler[1] = angle
            bpy.context.view_layer.update()
            scene.render.filepath = str(args.out / (phase + ".png"))
            bpy.ops.render.render(write_still=True)
    except Exception as ex:
        render_error = type(ex).__name__ + ": " + str(ex)
else:
    render_error = "REJECT_CAMERA_CROPPED"
scene.render.filepath = ""
for name in ("upperarm01.L", "upperleg01.L"):
    rig.pose.bones[name].rotation_euler[1] = 0
bpy.context.view_layer.update()

# No automatic anatomical or high-res promotion from bind/render success.
cage_structural = (
    cage.is_bound and quality.get("moving_vertices_gt_1mm", 0) > 100
    and quality.get("inverted_triangles", 1) == 0
    and quality.get("area_below_10pct", 1) == 0
    and quality.get("max_vertex_motion_m", 10) < .6
)
receipt = {
    "schema_version": "r014.surface_cage_bakeoff.v1",
    "source_DLE": "SemperSupra/stable-character-pipeline-private#138",
    "status": "HOLD_NOT_PHOTOREAL_NOT_ANATOMY_QUALIFIED",
    "structural_cage_candidate": bool(cage_structural),
    "sex_preset_macro": baseline["sex_source_macro"],
    "source_mpbf_mesh_vertices": len(src),
    "source_bone_count": len(rig.data.bones),
    "target_studio_base_vertices": len(tgt),
    "source_tissue_baseline": "failed nearest-triangle weights; retained as negative control",
    "experimental_method": "Blender Surface Deform; rigged MPFB skin is cage",
    "prior_target_modifiers": original_modifiers,
    "experimental_transform_repair_m": original_offset.tolist(),
    "prebind_source_distance_p95_m": registration_p95,
    "prebind_source_distance_over_50mm": registration_far,
    "cage_bound": bool(cage.is_bound),
    "bind_error": bind_error,
    "posed_geometry": quality,
    "authored_multires_test": lod,
    "camera_coverage": camera,
    "render_error": render_error,
    "source_materials_replaced_for_diagnostic_only": original_materials,
    "limitations": [
        "Experimental transfer, not region/landmark anatomical correspondence.",
        "Large rest-surface separation can cause artifacts even if bind succeeds.",
        "No genital anatomy, facial expression, thumb contact, cloth or tissue physics acceptance.",
        "L1 evaluated vertex count alone does not prove authored sculpt detail survived.",
        "Realistic moving 4K human release remains HOLD."
    ],
}
native = args.out / ("R014_" + args.sex + "_surface_cage_HELD.blend")
try:
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    receipt["native_blend_saved"] = native.exists()
except Exception as ex:
    receipt["native_save_error"] = str(ex)[:300]
path = args.out / "surface_cage_receipt.json"
path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print("R014_SURFACE_CAGE_BAKEOFF", json.dumps(receipt, sort_keys=True), flush=True)
