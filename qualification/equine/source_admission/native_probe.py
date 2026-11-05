"""Native Blender inspection of separately source-screened CC0 horse motion candidate."""
import bpy
import hashlib
import json
import math
import sys
from mathutils import Vector
from pathlib import Path

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    source, dest = Path(args[0]), Path(args[1])
    dest.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    rigs = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if not meshes or not rigs:
        raise RuntimeError("source not importable as skinned horse mesh with armature")
    rig = max(rigs, key=lambda r: len(r.data.bones))
    if len(rig.data.bones) < 16:
        raise RuntimeError("insufficient source rig bones")
    bounds = [o.matrix_world @ Vector(corner) for o in meshes for corner in o.bound_box]
    center = sum(bounds, Vector((0,0,0))) / len(bounds)
    radius = max((v-center).length for v in bounds)
    if not (0.05 < radius < 10000):
        raise RuntimeError("invalid source bounds")
    scene = bpy.context.scene
    bpy.ops.object.camera_add(location=center+Vector((radius*1.65,-radius*2.0,radius*1.0)))
    camera = bpy.context.object
    camera.rotation_euler = (center-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = radius*3
    scene.camera = camera
    bpy.ops.object.light_add(type="AREA", location=center+Vector((radius,-radius,radius*3)))
    lamp = bpy.context.object
    lamp.data.energy = 450
    lamp.data.size = radius*2
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 10
    scene.render.resolution_x = 640
    scene.render.resolution_y = 420
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(dest/"horse_native_import.png")
    scene.render.film_transparent = False
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/"horse_native_import.blend"))
    result = {"schema":"equine.source.native.v1","blender":bpy.app.version_string,
        "verdict":"NATIVE_BLENDER_SOURCE_IMPORT_PASS",
        "rig_bones":len(rig.data.bones),
        "source_meshes":len(meshes),
        "imported_actions":len(bpy.data.actions),
        "action_names":sorted(a.name for a in bpy.data.actions),
        "action_ranges":[{"action":a.name,"first_frame":float(a.frame_range[0]),
                          "last_frame":float(a.frame_range[1])}
                         for a in sorted(bpy.data.actions,key=lambda x:x.name)],
        "source_bones":[{"name":b.name,"parent":b.parent.name if b.parent else None,
                         "head":[round(float(x),6) for x in b.head_local],
                         "tail":[round(float(x),6) for x in b.tail_local]}
                        for b in sorted(rig.data.bones,key=lambda x:x.name)],
        "render_view":"static import probe; not retarget acceptance",
        "retarget_state":"NOT_RUN","hoof_contact":"UNKNOWN",
        "files":{}}
    for name in ("horse_native_import.png","horse_native_import.blend"):
        path=dest/name
        result["files"][name]={"size":path.stat().st_size,
                               "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    (dest/"native_report.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
main()
