"""R062 matched-camera CPU Cycles synthetic-proxy image witness.

Fixed view, samples, lighting, material, rig scene and seeded renderer for two
separate Blender importer processes. The original model is unchanged. PNG and
raw pixels remain on disposable public CI worker; only digest/statistics logged.
"""
import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
import bpy
from mathutils import Vector

NAMES=("R036_AnatomyProxy_Left","R036_AnatomyProxy_Right")

def hold(s):raise RuntimeError("R062_RENDER_HOLD "+s)
def digest(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--glb",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--pixels",required=True)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(args.glb))
    objs=[]
    for name in NAMES:
        matches=[o for o in bpy.data.objects if o.name==name and o.type=="MESH"]
        if len(matches)!=1:hold("missing unique proxy "+name)
        objs.append(matches[0])
    for obj in bpy.data.objects:
        if obj.type=="MESH" and obj not in objs:
            obj.hide_render=True
    coords=[obj.matrix_world @ v.co for obj in objs for v in obj.data.vertices]
    if len(coords)!=840:hold("expected 840 original-synthetic proxy vertices")
    minimum=Vector(tuple(min(float(v[i]) for v in coords) for i in range(3)))
    maximum=Vector(tuple(max(float(v[i]) for v in coords) for i in range(3)))
    center=(minimum+maximum)/2
    span=max(maximum[i]-minimum[i] for i in range(3))
    if not math.isfinite(span) or span<=0:hold("invalid synthetic organ bounds")
    # Material override isolates imported geometry/corner-normal shading from
    # glTF texture and vendor material differences, deliberately not a PBR audit.
    mat=bpy.data.materials.new("R062_Frozen_Gray_Original_Synthetic")
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:hold("standard shading node unavailable")
    bsdf.inputs["Base Color"].default_value=(0.47,0.55,0.62,1)
    bsdf.inputs["Roughness"].default_value=0.8
    bsdf.inputs["Metallic"].default_value=0
    for obj in objs:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    cam_data=bpy.data.cameras.new("R062_fixed_ortho")
    cam=bpy.data.objects.new("R062_fixed_ortho",cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location=center+Vector((2.0,-3.0,1.7))*span
    direction=center-cam.location
    cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler()
    cam_data.type="ORTHO"
    cam_data.ortho_scale=span*2.3
    bpy.context.scene.camera=cam
    light_data=bpy.data.lights.new("R062_frozen_sun",type="SUN")
    sun=bpy.data.objects.new("R062_frozen_sun",light_data)
    bpy.context.scene.collection.objects.link(sun)
    sun.location=center+Vector((2.0,-4.0,6.0))*span
    sun.rotation_euler=(center-sun.location).to_track_quat("-Z","Y").to_euler()
    light_data.energy=2.0
    light_data.angle=0.05
    scene=bpy.context.scene
    world=bpy.data.worlds.new("R062_frozen_ambient")
    scene.world=world
    world.use_nodes=True
    bg=world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value=(0.7,0.7,0.7,1.0)
        bg.inputs["Strength"].default_value=0.4
    scene.render.engine="CYCLES"
    scene.cycles.device="CPU"
    scene.cycles.samples=8
    scene.cycles.seed=17
    scene.cycles.use_animated_seed=False
    scene.render.threads_mode="FIXED"
    scene.render.threads=2
    scene.render.resolution_x=128
    scene.render.resolution_y=128
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format="PNG"
    scene.render.image_settings.color_mode="RGBA"
    scene.render.image_settings.color_depth="8"
    scene.camera.data.lens=40
    scene.render.film_transparent=False
    scene.render.filepath=str(Path(args.out).with_suffix(".png"))
    scene.frame_set(1)
    bpy.ops.render.render(write_still=True)
    png=Path(scene.render.filepath)
    if not png.is_file() or png.stat().st_size<500:hold("native Blender CPU render missing")
    img=bpy.data.images.load(str(png),check_existing=False)
    if tuple(img.size)!=(128,128):hold("CPU render dimensions wrong")
    floats=list(img.pixels)
    if len(floats)!=128*128*4:hold("CPU rendered pixel count wrong")
    rgba=bytes(max(0,min(255,round(float(x)*255))) for x in floats)
    nonflat=len(set(rgba[0::4]))+len(set(rgba[1::4]))+len(set(rgba[2::4]))
    if nonflat<30:hold("uninformative flat image")
    Path(args.pixels).write_bytes(rgba)
    record={
      "schema":"r062.original-synthetic-blender-cycles-render.v1",
      "status":"PASS_NARROW_NATIVE_CPU_IMAGE_CAPTURE_ONLY",
      "glb_sha256":digest(Path(args.glb).read_bytes()),
      "pixels_rgba8_sha256":digest(rgba),
      "png_sha256":digest(png.read_bytes()),
      "blender_version":".".join(str(v) for v in bpy.app.version),
      "engine":"CYCLES_CPU_SAMPLES_8_SEED_17",
      "camera":"FROZEN_ORTHO_FROM_2_PROXY_BBOX",
      "image_size":[128,128],
      "channel_unique_value_counts":[len(set(rgba[i::4])) for i in range(4)],
      "original_synthetic_proxy_vertices":len(coords),
      "limits":"Only deliberately neutralized-material 128x128 seeded Cycles CPU proxy pixels at frame 1. Not human anatomical realism, vendor PBR, animation, collision or H.264 film."
    }
    Path(args.out).write_text(json.dumps(record,sort_keys=True)+"\n")
    print("R062_CYCLES_IMAGE_CAPTURE "+json.dumps(record,sort_keys=True))
    # All PNG, rendered pixels, GLB bytes stay in per-job temp; no upload.

if __name__=="__main__":main()
