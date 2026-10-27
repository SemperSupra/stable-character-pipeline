"""Independent headless Blender readback and minimal workbench media proof.

Run after the Go exporter: Blender is an independent consumer of generated GLB;
it does not establish source-camera 3D accuracy or human anatomical realism.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index("--")+1:]
if len(args) != 3:
    raise SystemExit("expect -- <glb> <manifest> <output-directory>")
glb, manifest_file, out = Path(args[0]), Path(args[1]), Path(args[2])
out.mkdir(parents=True, exist_ok=True)
manifest = json.loads(manifest_file.read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(glb))
scene = bpy.context.scene
armatures = [x for x in bpy.data.objects if x.type == "ARMATURE"]
skinned = [x for x in bpy.data.objects if x.type == "MESH" and
           any(m.type == "ARMATURE" for m in x.modifiers)]
if not armatures:
    raise RuntimeError("GLB imported without a native Blender armature")
if not skinned:
    raise RuntimeError("GLB imported without a mesh bound to a Blender armature")
bone_counts = [len(a.data.bones) for a in armatures]
weight_count = sum(len(v.groups) for ob in skinned for v in ob.data.vertices)
if weight_count <= 0:
    raise RuntimeError("GLB skin lost all skin weights on independent Blender import")
if not bpy.data.actions:
    raise RuntimeError("GLB imported without animation action")

def sample_vertices(frame):
    scene.frame_set(int(frame))
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    points = []
    for ob in skinned:
        ev = ob.evaluated_get(deps)
        mesh = ev.to_mesh()
        for v in list(mesh.vertices)[:50]:
            p = ev.matrix_world @ v.co
            points.append((p.x, p.y, p.z))
        ev.to_mesh_clear()
    return points

# glTF seconds are mapped to frames at the Blender import-time FPS (normally 24).
fps = scene.render.fps / scene.render.fps_base
n = int(manifest["glb_sample_count"])
frames = [int(round(1 + i * fps)) for i in range(n)]
first, last = sample_vertices(frames[0]), sample_vertices(frames[-1])
if len(first) != len(last) or not first:
    raise RuntimeError("deformed mesh vertex capture mismatch")
max_displacement = max(math.dist(a, b) for a,b in zip(first,last))
if max_displacement < 0.002:
    raise RuntimeError("imported animation is static or disconnected from skin")

camera_data = bpy.data.cameras.new("camera_plane_proxy_oracle")
camera = bpy.data.objects.new("camera_plane_proxy_oracle", camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera
camera.location = (0,0,8)
camera.rotation_euler = (0,0,0)
camera_data.type = 'ORTHO'
camera_data.ortho_scale = 4.0
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_cavity = True
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = str(out / "rig_frame_000.png")
for i, frame in enumerate(frames):
    scene.frame_set(frame)
    scene.render.filepath = str(out / ("rig_frame_%03d.png" % i))
    bpy.ops.render.render(write_still=True)
    if not Path(scene.render.filepath).exists():
        raise RuntimeError("Blender rendered frame missing: %d" % i)
receipt = {
    "classification": "INDEPENDENT_BLENDER_SKIN_AND_ANIMATION_READBACK",
    "input_glb_sha256": manifest["glb_sha256"],
    "blender_version": bpy.app.version_string,
    "armatures": len(armatures),
    "bone_counts": bone_counts,
    "skinned_meshes": len(skinned),
    "vertex_skin_weight_groups_observed": weight_count,
    "actions": len(bpy.data.actions),
    "source_sampled_frames": n,
    "native_animation_fps": fps,
    "evaluated_animated_vertex_max_displacement_camera_plane_units": max_displacement,
    "rendered_png_frames": len(frames),
    "camera_plane_not_true_3d": True,
    "skin_import_render_pass": True,
    "biomechanical_or_image_similarity": "NOT_VALIDATED"
}
(out / "blender_independent_readback.json").write_text(json.dumps(receipt,indent=2)+"\n")
print("R3_NATIVE_BLENDER_RECEIPT "+json.dumps(receipt,sort_keys=True))
