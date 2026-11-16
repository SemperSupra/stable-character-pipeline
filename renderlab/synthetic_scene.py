#!/usr/bin/env python3
"""Original synthetic material comparison. Runs ONLY inside Blender Python.
Scientific gate: evidence of actual Cycles renders, NOT photo-real human fidelity.
No assets, trained models, faces, or remote downloads.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

SCENE_ID = "original-synthetic-head-v1"
EXPERIMENT = "r037-synthetic-material-screen"
SEED = 13
RESOLUTION = 256
SAMPLES = 12

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def canonical_hash(obj):
    return sha_bytes(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8"))

def material(name, color, arm, skin=False, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    tree = m.node_tree
    bsdf = next(n for n in tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.68 if arm == "baseline" else 0.43
    bsdf.inputs["Metallic"].default_value = metallic
    if skin and arm == "physical_material":
        sub = bsdf.inputs.get("Subsurface Weight") or bsdf.inputs.get("Subsurface")
        if sub is not None:
            sub.default_value = 0.16
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 105.0
        noise.inputs["Detail"].default_value = 3.0
        bump = tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.12
        bump.inputs["Distance"].default_value = 0.003
        tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        tree.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m

def add_uv(name, loc, scale, mat, seg=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
    ob=bpy.context.object
    ob.name=name
    ob.scale=scale
    ob.data.materials.append(mat)
    ob.pass_index=1
    for p in ob.data.polygons:
        p.use_smooth=True
    return ob

def aim(ob, target):
    direction = Vector(target) - ob.location
    ob.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

def make_scene(arm):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for m in list(bpy.data.materials):
        if m.users == 0: bpy.data.materials.remove(m)

    skin=material("original-synthetic-skin", (0.49,0.27,0.19), arm, skin=True)
    lips=material("synthetic-lips", (0.32,0.10,0.095), arm, skin=True)
    whites=material("eye-sclera", (0.75,0.72,0.67), arm)
    iris=material("iris", (0.10,0.19,0.16), arm)
    pupils=material("pupil", (0.012,0.009,0.01), arm)
    dark=material("brows", (0.045,0.028,0.021), arm)
    cloth=material("clothing", (0.09,0.15,0.24), arm)
    floor=material("matte-floor", (0.28,0.30,0.34), "baseline")

    add_uv("torso", (0,0,0.62), (0.80,0.40,0.67), cloth)
    add_uv("neck", (0,-0.02,1.12), (0.23,0.25,0.35), skin)
    add_uv("head", (0,-0.03,1.92), (0.62,0.46,0.80), skin, 48, 32)
    add_uv("nose", (0,-0.52,1.86), (0.105,0.17,0.19), skin)
    for direction, side in [("left",-1),("right",1)]:
        x=side*0.24
        add_uv(direction+"-sclera", (x,-0.427,2.06), (0.15,0.084,0.087), whites)
        add_uv(direction+"-iris", (x,-0.504,2.06), (0.07,0.018,0.071), iris)
        add_uv(direction+"-pupil", (x,-0.524,2.06), (0.032,0.008,0.035), pupils)
        add_uv(direction+"-brow", (x,-0.445,2.23), (0.18,0.041,0.026), dark)
        add_uv(direction+"-ear", (side*0.61,0.03,1.91), (0.11,0.12,0.20), skin)
    add_uv("mouth", (0,-0.43,1.62), (0.23,0.046,0.028), lips)

    bpy.ops.mesh.primitive_plane_add(size=100,location=(0,0,-0.03))
    ground=bpy.context.object
    ground.name="ground"
    ground.data.materials.append(floor)
    ground.pass_index=2

    bpy.ops.object.camera_add(location=(3.5,-6.5,3.0))
    camera=bpy.context.object
    camera.name="fixed-camera"
    aim(camera,(0,0,1.55))
    camera.data.type='ORTHO'
    camera.data.ortho_scale=3.65
    bpy.context.scene.camera=camera
    for name,loc,power,size in [
        ("key",(2.7,-3.5,4.8),500.0,3.2),
        ("fill",(-3.3,-1.6,3.2),240.0,3.4),
        ("rim",(1.2,2.9,4.2),400.0,2.5),
    ]:
        bpy.ops.object.light_add(type='AREA',location=loc)
        light=bpy.context.object
        light.name=name
        light.data.energy=power
        light.data.shape='DISK'
        light.data.size=size
        aim(light,(0,0,1.7))
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.samples=SAMPLES
    scene.cycles.seed=SEED
    scene.render.resolution_x=RESOLUTION
    scene.render.resolution_y=RESOLUTION
    scene.render.resolution_percentage=100
    scene.render.film_transparent=False
    scene.render.image_settings.color_mode='RGBA'
    view=scene.view_layers[0]
    view.use_pass_z=True
    view.use_pass_normal=True
    view.use_pass_object_index=True
    view.use_pass_vector=True
    scene.world.color=(0.16,0.16,0.16)
    bpy.context.view_layer.update()
    return scene

def geometry_digest():
    items=[]
    for obj in sorted((x for x in bpy.data.objects if x.type=='MESH'),key=lambda x:x.name):
        matrix=obj.matrix_world
        vertices=[
            [round(float(v),7) for v in (matrix @ p.co)]
            for p in obj.data.vertices
        ]
        faces=[list(face.vertices) for face in obj.data.polygons]
        items.append({"name":obj.name,"vertices":vertices,"faces":faces})
    return canonical_hash(items)

def run(arm,out_dir):
    if arm not in ("baseline","physical_material"):
        raise ValueError("Unknown arm")
    out=Path(out_dir)
    out.mkdir(parents=True,exist_ok=True)
    scene=make_scene(arm)
    camera=scene.camera
    geom=geometry_digest()
    cam=canonical_hash({
        "matrix":[round(float(v),7) for row in camera.matrix_world for v in row],
        "projection":"ORTHO","scale":camera.data.ortho_scale,
        "resolution":RESOLUTION
    })
    images={}
    start=time.perf_counter()
    for suffix,fmt in [("png","PNG"),("exr","OPEN_EXR_MULTILAYER")]:
        name="beauty."+suffix if suffix=="png" else "render_passes.exr"
        path=out/name
        scene.render.image_settings.file_format=fmt
        scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True)
        if not path.is_file() or path.stat().st_size<128:
            raise RuntimeError("Render artifact absent/undersized: "+str(path))
        images[suffix]={"file":name,"sha256":sha_bytes(path.read_bytes())}
    elapsed=time.perf_counter()-start
    receipt={
        "schema_version":"renderlab.synthetic.v1",
        "experiment_id":EXPERIMENT,
        "scene_id":SCENE_ID,
        "source_sha256":sha_bytes(SCENE_ID.encode("utf-8")),
        "geometry_sha256":geom,
        "camera_sha256":cam,
        "animation_sha256":sha_bytes(b"STATIC-POSE-ORIGINAL-V1"),
        "arm":arm,"seed":SEED,
        "rights":"ORIGINAL_SYNTHETIC",
        "status":"PASS_RENDER_ONLY",
        "engine":"CYCLES","samples":SAMPLES,
        "resolution":RESOLUTION,
        "elapsed_seconds":round(max(elapsed,0.000001),6),
        "beauty_png":images["png"],
        "render_passes_exr":images["exr"],
    }
    (out/"receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("R037_ACTUAL_SYNTHETIC_CYCLES_RENDER_ONLY",arm,geom,cam,receipt["elapsed_seconds"])

def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    parser=argparse.ArgumentParser()
    parser.add_argument("--arm",required=True,choices=["baseline","physical_material"])
    parser.add_argument("--output",required=True)
    opts=parser.parse_args(argv)
    run(opts.arm,opts.output)

if __name__=="__main__":
    main()
