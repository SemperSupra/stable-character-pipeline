"""Render actual exported GLB animation frames for independent multi-coat visual QA.

This intentionally imports GLB (not producer .blend), so animation tracks,
skin weights, and transforms must survive export. No source photographs.
"""
import bpy
import json
import hashlib
import sys
from pathlib import Path
from mathutils import Vector

def track(obj, target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat("-Z","Y").to_euler()

def main():
    args=sys.argv[sys.argv.index("--")+1:]
    if len(args)!=2:
        raise ValueError("usage: Blender --python video_probe.py -- <source.glb> <output-dir>")
    glb=Path(args[0])
    out=Path(args[1])
    out.mkdir(parents=True,exist_ok=True)
    frames=out/"frames"
    frames.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    scene=bpy.context.scene
    armatures=[obj for obj in bpy.data.objects if obj.type=="ARMATURE"]
    meshes=[obj for obj in bpy.data.objects if obj.type=="MESH"]
    if not armatures or len(meshes)<4:
        raise RuntimeError("GLB import missing rig/meshes")
    if len(max(armatures,key=lambda x:len(x.data.bones)).data.bones)<26:
        raise RuntimeError("GLB missing 26 source joints")
    if not bpy.data.actions:
        raise RuntimeError("GLB missing native animation action")
    scene.frame_start=1
    scene.frame_end=48
    scene.render.fps=24
    scene.render.engine="BLENDER_WORKBENCH"
    scene.display.shading.light="STUDIO"
    scene.display.shading.color_type="MATERIAL"
    scene.display.shading.show_shadows=True
    scene.display.shading.show_cavity=True
    scene.display.shading.cavity_type="BOTH"
    scene.render.resolution_x=640
    scene.render.resolution_y=360
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    bpy.ops.object.camera_add(location=(0.05,-3.2,1.28))
    camera=bpy.context.object
    camera.data.type="ORTHO"
    camera.data.ortho_scale=2.75
    track(camera,(.12,0,.72))
    scene.camera=camera
    samples=[]
    for frame in range(1,49):
        scene.frame_set(frame)
        scene.render.filepath=str(frames/f"side_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
        if frame in (1,13,25,37):
            path=Path(scene.render.filepath)
            samples.append({"frame":frame,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    if len(set(x["sha256"] for x in samples))<2:
        raise RuntimeError("GLB playback produced identical key frame images")
    camera.location=(2.2,-3.0,1.65)
    camera.data.ortho_scale=3.05
    track(camera,(.17,0,.72))
    scene.frame_set(25)
    scene.render.filepath=str(out/"oblique_frame25.png")
    bpy.ops.render.render(write_still=True)
    receipt={
      "schema":"equine.visual.glb.v1",
      "source_glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
      "source_glb_bytes":glb.stat().st_size,
      "blender":bpy.app.version_string,
      "imported_armature_count":len(armatures),
      "imported_mesh_count":len(meshes),
      "imported_action_count":len(bpy.data.actions),
      "rendered_frames":48,"fps":24,
      "resolution":[640,360],
      "first_four_keyframe_hashes":samples,
      "validation":"GLB_PLAYBACK_RENDERED_NOT_BIOLOGICAL_ACCEPTANCE",
      "limitation":"Stylized procedural pony; stance, anatomy, fur, and gaze require manual and biomechanical inspection"
    }
    (out/"video_probe.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
main()
