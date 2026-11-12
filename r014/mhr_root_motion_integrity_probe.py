"""R014 MHR source-native root-motion integrity and hierarchy falsifier.

This intentionally disables IK: a pure root displacement must move every
weighted body vertex rigidly, not blow up skin geometry. Green Actions means
evidence collection; cinematic, gait, anatomical and photoreal gates stay HOLD.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=("object", "pose-root"), required=True)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:])
a.out.mkdir(parents=True, exist_ok=True)
assert Path(bpy.data.filepath).name == "R014_MHR_neutral_lod1.blend"
body = bpy.data.objects["R014_MHR_neutral_body"]
rig = bpy.data.objects["R014_MHR_neutral_rig"]
assert len(body.data.vertices) == 18439
assert len(rig.data.bones) == 126
assert body.type == "MESH" and rig.type == "ARMATURE"
assert "root" in rig.pose.bones
assert any(m.type == "ARMATURE" and m.object == rig for m in body.modifiers)
assert len(body.data.shape_keys.key_blocks) == 118
assert all(not bone.constraints for bone in rig.pose.bones), "source has unexpected active rig constraint"

scene = bpy.context.scene
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 24
root = rig.pose.bones["root"]
root.rotation_mode = "QUATERNION"
rig.rotation_mode = "QUATERNION"
rig.animation_data_clear()
init_loc = rig.location.copy()
init_root_loc = root.location.copy()

def set_position(frame, displacement):
    scene.frame_set(frame)
    if a.mode == "object":
        rig.location = init_loc + Vector((displacement, 0.0, 0.0))
        rig.keyframe_insert(data_path="location", frame=frame)
    else:
        root.location = init_root_loc + Vector((displacement, 0.0, 0.0))
        root.keyframe_insert(data_path="location", frame=frame)
    bpy.context.view_layer.update()

for frame, displacement in ((1, 0.0), (12, 0.20), (24, 0.0)):
    set_position(frame, displacement)

def state(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    erig = rig.evaluated_get(dg)
    root_world = erig.matrix_world @ erig.pose.bones["root"].head
    obj = body.evaluated_get(dg)
    mesh = obj.to_mesh()
    try:
        vertices = np.asarray([list(obj.matrix_world @ v.co) for v in mesh.vertices],
                              dtype=np.float64)
        polygons = [tuple(int(i) for i in p.vertices) for p in mesh.polygons]
    finally:
        obj.to_mesh_clear()
    assert vertices.shape == (18439, 3) and np.isfinite(vertices).all()
    return vertices, polygons, np.asarray(root_world, dtype=np.float64)

neutral, polygons, neutral_root = state(1)
shifted, moved_polygons, moved_root = state(12)
restored, restored_polygons, restored_root = state(24)
assert polygons == moved_polygons == restored_polygons
tri = np.asarray([(p[0], p[j], p[j+1]) for p in polygons
                  for j in range(1, len(p)-1)], dtype=np.int32)
assert len(tri) == 36874

def orient(x):
    n = np.cross(x[tri[:, 1]]-x[tri[:, 0]],x[tri[:, 2]]-x[tri[:, 0]])
    return n,np.linalg.norm(n,axis=1)

n0, mag0 = orient(neutral)
n1, mag1 = orient(shifted)
valid = mag0 > 1e-11
foldovers = int(np.count_nonzero(valid & (np.einsum("ij,ij->i",n0,n1) <= 0)))
collapses = int(np.count_nonzero(valid & (mag1 < 0.10*mag0)))
root_translation = moved_root - neutral_root
skin_translation = shifted - neutral
residual = np.linalg.norm(skin_translation-root_translation[None,:], axis=1)
return_residual = np.linalg.norm(restored-neutral,axis=1)
bone_return_error = float(np.linalg.norm(restored_root-neutral_root))
r95 = float(np.percentile(residual,95))
maxr = float(np.max(residual))
candidate = (0.1 <= float(np.linalg.norm(root_translation)) <= .3
             and r95 < .01 and maxr < .03
             and foldovers == 0 and collapses == 0
             and float(np.max(return_residual)) < .001 and bone_return_error < .001)

# Keep a native editable, keyed scene for independent hierarchy inspection.
scene.frame_set(1)
native = a.out / ("R014_MHR_" + a.mode + "_root_only_HELD.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size > 100000

# Two small true Blender images: separate source neutral and pure displacement.
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 6
scene.render.threads_mode = "FIXED"
scene.render.threads = 4
scene.render.resolution_x = 320
scene.render.resolution_y = 420
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("R014_Root_Integrity_World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Strength"].default_value = .85
scene.world = world
light_data = bpy.data.lights.new("R014_Root_Light", "AREA")
light = bpy.data.objects.new("R014_Root_Light", light_data)
bpy.context.collection.objects.link(light)
light.location = (1.5, -2.5, 3.0)
light_data.energy = 500
light_data.size = 3
camera_data = bpy.data.cameras.new("R014_Root_Camera")
camera = bpy.data.objects.new("R014_Root_Camera", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
camera_data.type = "ORTHO"
both = np.vstack((neutral, shifted))
lo = both.min(axis=0); hi = both.max(axis=0)
middle = (lo+hi)*.5
extents = hi-lo
camera_data.ortho_scale = max(float(extents[2]*1.30),
                              float(extents[0]/(320/420))*1.3,2.0)
camera.location = (float(middle[0]),float(middle[1]-4.0),float(middle[2]))
camera.rotation_euler = (Vector(middle.tolist())-camera.location).to_track_quat("-Z","Y").to_euler()
rendered=[]
for frame,label in ((1,"neutral"),(12,"translation")):
    scene.frame_set(frame)
    scene.render.filepath = str(a.out / (a.mode+"_"+label+".png"))
    bpy.ops.render.render(write_still=True)
    path=Path(scene.render.filepath)
    assert path.stat().st_size>5000
    rendered.append(path.name)

receipt={
    "schema":"r014.mhr.root_motion_hierarchy.v1",
    "status":"PASS_PURE_ROOT_TRANSLATION_GEOMETRY_ONLY" if candidate else "HOLD_ROOT_HIERARCHY_OR_SKIN_DEFORMATION",
    "mode":a.mode,
    "original_source":"facebookresearch/MHR v1.0.1 official native LOD1",
    "source_archive_sha256":"e4f4f205cd87c0fa106577ba1de4fc763e4eb197c924461d2ef7e6944e9d6b94",
    "geometry_units":"MHR_NATIVE_BLENDER_UNITS_NOT_INDEPENDENTLY_METRIC_CALIBRATED",
    "body_parent_name": body.parent.name if body.parent else None,
    "body_parent_type":body.parent_type,
    "body_world_matrix":[list(row) for row in body.matrix_world],
    "rig_world_matrix":[list(row) for row in rig.matrix_world],
    "root_rest_world":neutral_root.tolist(),
    "root_moved_world":moved_root.tolist(),
    "root_shift_world":root_translation.tolist(),
    "root_shift_norm":float(np.linalg.norm(root_translation)),
    "vertex_count":len(neutral),
    "triangles":len(tri),
    "inverted_triangles":foldovers,
    "severely_collapsed_triangles":collapses,
    "translation_residual_p95":r95,
    "translation_residual_max":maxr,
    "restoration_vertex_error_max":float(np.max(return_residual)),
    "restoration_root_error":bone_return_error,
    "vertices_with_translation_error_gt_1mm":int(np.count_nonzero(residual>.001)),
    "native_blend":native.name,
    "technical_frames":rendered,
    "limits":[
        "No IK, no gait, no planted-contact or heel/toe test",
        "Pure rigid root motion only; nonlinear pose correctives and body shape variants untested",
        "No verified true centimeters, measured anatomy or production body-morphology range",
        "No full anatomy, skin, eyes, hair, hands, clothing, tissue or cinematic realism",
        "All evidence research-only, public synthetic adult model, no identity media"
    ]
}
(a.out/"mhr_root_motion_integrity.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_ROOT_MOTION_INTEGRITY",json.dumps({
    "status":receipt["status"],"mode":a.mode,
    "root_shift_norm":receipt["root_shift_norm"],
    "p95":r95,"max_error":maxr,"inversions":foldovers,
    "collapsed":collapses,"parent":receipt["body_parent_name"]
},sort_keys=True),flush=True)
