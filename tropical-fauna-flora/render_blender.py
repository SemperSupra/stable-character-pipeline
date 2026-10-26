#!/usr/bin/env python3
"""Headless Blender adapter for the independent Go-authored fauna/flora GLB.

Import the exported GLB rather than reconstructing animals with Blender-only
primitives. Additional terrain dressing is explicitly kept in the .blend, not
silently claimed as part of the exported GLB. No external assets or network.

Run: blender -b -t 2 --python render_blender.py -- --input out/tropical_scene.glb \
     --out out/blender --frames 48 --fps 12 --width 640 --height 360
"""
import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments():
    cli = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='out/tropical_scene.glb')
    p.add_argument('--out', default='out/blender')
    p.add_argument('--frames', type=int, default=48)
    p.add_argument('--fps', type=int, default=12)
    p.add_argument('--width', type=int, default=640)
    p.add_argument('--height', type=int, default=360)
    p.add_argument('--seed', type=int, default=1337)
    p.add_argument('--samples', type=int, default=8)
    args = p.parse_args(cli)
    if not (12 <= args.frames <= 120 and 8 <= args.fps <= 30 and
            320 <= args.width <= 960 and 180 <= args.height <= 540 and
            1 <= args.samples <= 48):
        p.error('bounded free CPU workload exceeded')
    return args


def material(name, color, roughness=0.8, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Metallic'].default_value = metallic
    return mat


def polish_imported_materials():
    """Color-managed original source materials; no source geometry replacement."""
    for m in bpy.data.materials:
        name = m.name.lower()
        if not m.use_nodes:
            continue
        shader = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if shader is None:
            continue
        shader.inputs['Roughness'].default_value = (0.22 if 'water' in name else
                                                      0.77 if 'hide' in name else 0.86)
        shader.inputs['Metallic'].default_value = 0.0
        if 'buffalo-hide' in name or 'soil' in name:
            tex = m.node_tree.nodes.new('ShaderNodeTexNoise')
            tex.inputs['Scale'].default_value = 55 if 'hide' in name else 12
            bump = m.node_tree.nodes.new('ShaderNodeBump')
            bump.inputs['Strength'].default_value = .12 if 'hide' in name else .22
            bump.inputs['Distance'].default_value = .035
            m.node_tree.links.new(tex.outputs['Fac'], bump.inputs['Height'])
            m.node_tree.links.new(bump.outputs['Normal'], shader.inputs['Normal'])


def scenery(seed):
    """Reproducible scene-level visual dressing; it does not change GLB geometry.

    Three earth-color meshes of rice/tall meadow stalks and background tree-line.
    These are illustrative, not botanically qualified OpenAlea outputs.
    """
    rng = random.Random(seed)
    colors = [material('dressing/rice-deep',(.075,.27,.07)),
              material('dressing/rice-mid',(.19,.44,.065)),
              material('dressing/rice-gold',(.43,.48,.11))]
    for layer, mat in enumerate(colors):
        verts, faces = [], []
        for _ in range(475):
            x = rng.uniform(-11.75,11.75)
            y = rng.uniform(-8.65,8.65)
            if -2.78 < y < -0.96:  # irrigation channel stays visible
                continue
            h = rng.uniform(.34,.86)
            angle = rng.uniform(0,math.tau)
            vx,vy = math.cos(angle),math.sin(angle)
            for k in range(3):
                a = angle + k * 2.094
                dx,dy = math.cos(a), math.sin(a)
                sx,sy=x + .06*vx,y + .06*vy
                w = .032 if layer!=2 else .024
                i = len(verts)
                verts.extend([(sx-dy*w,sy+dx*w,-.117),
                              (sx+dy*w,sy-dx*w,-.117),
                              (sx+dx*h*.20,sy+dy*h*.20,h)])
                faces.append((i,i+1,i+2))
        mesh = bpy.data.meshes.new(f'rice-tuft-mesh-{layer}')
        mesh.from_pydata(verts,[],faces)
        mesh.update()
        obj = bpy.data.objects.new(f'dressing/rice-tufts-{layer}',mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.data.materials.append(mat)
    # A deliberately distant treeline to ground the field in a tropical valley.
    hillmat = material('dressing/distant-forest',(.15,.25,.21))
    for band in range(2):
        vs,fs=[],[]
        y=11.0+4.4*band
        for i in range(34):
            x=-24+48*i/33
            z=-.35 + (0.4 if band==0 else 1.2) + \
                (1.6 if band==0 else 2.2)*(0.5+0.5*math.sin(i*.38+band*1.3))
            vs.extend([(x,y,-.55),(x,y,z)])
            if i:
                j=2*i
                fs.append((j-2,j-1,j)); fs.append((j,j-1,j+1))
        me=bpy.data.meshes.new(f'forest-hill-{band}')
        me.from_pydata(vs,[],fs);me.update()
        ob=bpy.data.objects.new(f'dressing/distant-hill-{band}',me)
        bpy.context.scene.collection.objects.link(ob)
        ob.data.materials.append(hillmat)


def setup_camera():
    bpy.ops.object.camera_add(location=(6.5,-19.8,7.3))
    cam=bpy.context.object
    cam.name='camera/tracking-tropical-field'
    goal=Vector((-3.5,-.15,1.5))
    cam.rotation_euler=(goal-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='PERSP'
    cam.data.lens=36
    bpy.context.scene.camera=cam
    return cam


def lighting():
    world=bpy.data.worlds.new('Tropical daylight')
    bpy.context.scene.world=world
    world.use_nodes=True
    background=world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value=(.53,.70,.93,1.)
    background.inputs['Strength'].default_value=.65
    bpy.ops.object.light_add(type='SUN',location=(-7,-3,15))
    sun=bpy.context.object;sun.name='light/tropical-sun'
    sun.rotation_euler=(math.radians(24),math.radians(-28),math.radians(-25))
    sun.data.energy=2.25
    sun.data.angle=math.radians(7)
    bpy.ops.object.light_add(type='AREA',location=(2,-7,11))
    fill=bpy.context.object;fill.name='light/soft-front'
    fill.data.energy=1100
    fill.data.shape='DISK'
    fill.data.size=8
    fill.rotation_euler=(Vector((-3,0,1))-fill.location).to_track_quat('-Z','Y').to_euler()


def animate_camera(cam, count):
    # Camera pan is an authoring affordance, not evidence of animal locomotion.
    origin=cam.location.copy()
    for f,shift in [(1,0),(count,.7)]:
        cam.location=origin+Vector((shift,0,0))
        cam.keyframe_insert(data_path='location',frame=f)


def preflight(imported, frame_count):
    """Reject empty, non-animated or frozen-import renders."""
    meshes=[o for o in imported if o.type=='MESH']
    if len(meshes)<150:
        raise RuntimeError(f'Expected 150+ original source meshes, found {len(meshes)}')
    scene=bpy.context.scene
    roots=[o for o in imported if 'buffalo-' in o.name.lower() and '/root' in o.name.lower()]
    if not roots:
        # Some Blender imports normalize slash characters in names: try semantic tokens.
        roots=[o for o in imported if 'buffalo-' in o.name.lower() and 'root' in o.name.lower()]
    if len(roots)<2:
        raise RuntimeError('GLB buffalo root objects missing; refuse video substitute')
    scene.frame_set(1)
    first=[o.matrix_world.translation.copy() for o in roots]
    scene.frame_set(frame_count)
    second=[o.matrix_world.translation.copy() for o in roots]
    displacement=max((a-b).length for a,b in zip(first,second))
    if displacement<.08:
        raise RuntimeError(f'Imported animal tracks are frozen (max root displacement {displacement:.4f}m)')
    return {'imported_meshes':len(meshes),'buffalo_root_count':len(roots),
            'max_buffalo_root_displacement_m':round(displacement,5),
            'source_actions':len(bpy.data.actions)}


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    args=arguments()
    source=Path(args.input).resolve()
    out=Path(args.out).resolve()
    if not source.is_file() or source.stat().st_size>100*1024*1024:
        raise RuntimeError('Missing or oversized generated GLB input')
    out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    imported=tuple(bpy.context.scene.objects)
    polish_imported_materials()
    scenery(args.seed)
    cam=setup_camera()
    lighting()
    animate_camera(cam,args.frames)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=args.samples
    scene.render.threads_mode='FIXED'
    scene.render.threads=2
    scene.render.resolution_x=args.width
    scene.render.resolution_y=args.height
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.film_transparent=False
    scene.render.fps=args.fps
    scene.frame_start=1
    scene.frame_end=args.frames
    scene.render.image_settings.color_mode='RGB'
    try:
        scene.view_settings.view_transform='AgX'
    except TypeError:
        pass
    metrics=preflight(imported,args.frames)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'tropical_scene.blend'))
    for frame in range(1,args.frames+1):
        scene.frame_set(frame)
        scene.render.filepath=str(out/f'frame_{frame-1:04d}.png')
        bpy.ops.render.render(write_still=True)
        if frame==1 or frame%12==0:
            print(f'BLENDER_FRAME {frame}/{args.frames}',flush=True)
    receipt={'schema':'tropical.blender.receipt.v1', 'renderer':'Blender Cycles CPU',
             'blender_version':bpy.app.version_string, 'input_glb_sha256':sha(source),
             'frames':args.frames, 'fps':args.fps, 'resolution':[args.width,args.height],
             'samples':args.samples,'additional_dressing':'Blender-only deterministic illustrative meadow and treeline',
             'status':'LOW_POLY_UNQUALIFIED_BIOLOGY',**metrics}
    (out/'blender_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print('BLENDER_RENDER_COMPLETE '+json.dumps(receipt,sort_keys=True),flush=True)


if __name__=='__main__':
    main()
