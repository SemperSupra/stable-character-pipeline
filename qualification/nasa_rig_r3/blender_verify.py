"""Independent headless Blender readback and CPU raster media proof.

Run after the Go exporter: Blender is an independent consumer of generated GLB;
it does not establish source-camera 3D accuracy or human anatomical realism.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from frame_clock import source_aligned_frames

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
        for v in mesh.vertices:
            p = ev.matrix_world @ v.co
            points.append((p.x, p.y, p.z))
        ev.to_mesh_clear()
    return points

# glTF seconds are mapped to frames at the Blender import-time FPS (normally 24).
fps = scene.render.fps / scene.render.fps_base
n = int(manifest["glb_sample_count"])
# This specific NASA GLB uses animation keys at source-relative t=0..9s.
# The former 1+i*fps began 1/24s ahead and visually misaligned the samples.
frames = source_aligned_frames(n, fps)
first, last = sample_vertices(frames[0]), sample_vertices(frames[-1])
if len(first) != len(last) or not first:
    raise RuntimeError("deformed mesh vertex capture mismatch")
max_displacement = max(math.dist(a, b) for a,b in zip(first,last))
if max_displacement < 0.002:
    raise RuntimeError("imported animation is static or disconnected from skin")

# Assert geometry is represented in Blender XZ after import, not blindly
# projected through the wrong plane. Covers *all* skinned vertices, not just 50.
def extent(points, coordinate):
    return max(p[coordinate] for p in points)-min(p[coordinate] for p in points)
blender_axes = {
    "native_x_horizontal_extent_at_first": extent(first,0),
    "native_y_depth_extent_at_first": extent(first,1),
    "native_z_vertical_extent_at_first": extent(first,2),
    "projection_axes": "Blender native XZ (glTF source XY), depth Blender Y",
}
if blender_axes["native_z_vertical_extent_at_first"] < 0.10:
    raise RuntimeError("GLB camera-plane vertical collapsed during Blender glTF import")
if blender_axes["native_z_vertical_extent_at_first"] <= 4*blender_axes["native_y_depth_extent_at_first"]:
    raise RuntimeError("camera-plane axis unexpectedly oriented; Blender XZ projection not justified")


# Evaluate skin with Blender, but rasterize from evaluated polygons on CPU.
# Ubuntu public Actions has no EGL; a Blender workbench engine would require a
# graphics context. A dependency-free Pillow raster is explicitly NOT Blender
# workbench rendering or a photorealistic/source-image comparison.
from PIL import Image, ImageDraw
# Imported glTF is Y-up; bpy maps that source Y vertical to Blender Z-up.
# The source rig is glTF camera plane XY with authored Z=0. After import it is
# native Blender XZ, with Y used only for source depth (approximately zero).
# Project X/Z for human previews. Never call this recovered metric 3D.
def project(p):
    return (int(round(320+160*p.x)), int(round(180-160*p.z)))

def cpu_preview(frame_number, output_png, source_second):
    scene.frame_set(frame_number)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    image = Image.new("RGB", (640,360), (13,22,38))
    draw = ImageDraw.Draw(image)
    count = 0
    for ob in skinned:
        ev = ob.evaluated_get(deps)
        mesh = ev.to_mesh()
        transformed = [ev.matrix_world @ v.co for v in mesh.vertices]
        for polygon in mesh.polygons:
            if len(polygon.vertices) < 3:
                continue
            pts = [project(transformed[j]) for j in polygon.vertices]
            draw.polygon(pts, fill=(40,165,215), outline=(135,230,255))
            count += 1
        ev.to_mesh_clear()
    if count == 0:
        raise RuntimeError("Blender evaluated zero skinned triangles")
    draw.rectangle((0,0,640,35), fill=(7,12,25))
    draw.text((12,11), "NASA R3 | Blender evaluated skin | 2D camera-plane proxy", fill=(242,245,250))
    draw.text((14,332), "NASA source second %d | Z=0, no body shape or true depth" % source_second, fill=(210,221,235))
    image.save(output_png)

for i, frame in enumerate(frames):
    cpu_preview(frame, str(out / ("rig_frame_%03d.png" % i)),
                int(manifest["glb_frame_start_source_ms"]/1000)+i)
    if not (out / ("rig_frame_%03d.png" % i)).exists():
        raise RuntimeError("CPU rasterized frame missing: %d" % i)
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
    "source_glb_animation_time_origin_seconds": 0,
    "native_blender_scene_frames": frames,
    "source_frame_to_scene_mapping": "source-relative-second-i -> scene frame round(i*fps) (zero-based)",
    "evaluated_animated_vertex_max_displacement_camera_plane_units": max_displacement,
    "rendered_png_frames": len(frames),
    "native_blender_axis_validation": blender_axes,
    "blender_total_sampled_mesh_vertices": len(first),
    "raster_pipeline": "Blender evaluated skin geometry -> Pillow CPU polygons; NOT Blender render engine",
    "camera_plane_not_true_3d": True,
    "skin_import_and_cpu_preview_pass": True,
    "biomechanical_or_image_similarity": "NOT_VALIDATED"
}
(out / "blender_independent_readback.json").write_text(json.dumps(receipt,indent=2)+"\n")
print("R3_NATIVE_BLENDER_RECEIPT "+json.dumps(receipt,sort_keys=True))
