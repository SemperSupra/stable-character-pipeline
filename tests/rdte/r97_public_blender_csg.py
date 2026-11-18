# Original, source-safe Blender donor qualification fixture.
# This file does not import Oneirifact or any private repository code/assets.
# It independently tests Blender's geometric treatment of nested Boolean
# operands under rigid transforms, disconnected components and native/glTF output.
import bmesh
import bpy
import json
import math
import os
import pathlib
import sys
from mathutils import Matrix, Vector

def cube(name, transform):
    bpy.ops.mesh.primitive_cube_add(size=2.0)
    obj = bpy.context.object
    obj.name = name
    obj.matrix_world = transform
    return obj

def cylinder(name, transform):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=.4, depth=3.0)
    obj = bpy.context.object
    obj.name = name
    obj.matrix_world = transform
    return obj

def sphere(name, radius, transform):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=radius)
    obj = bpy.context.object
    obj.name = name
    obj.matrix_world = transform
    return obj

def boolean(left, right, operation, name):
    result = left.copy()
    result.data = left.data.copy()
    result.name = name
    bpy.context.scene.collection.objects.link(result)
    modifier = result.modifiers.new('independent_csg', 'BOOLEAN')
    modifier.operation = operation
    modifier.solver = 'EXACT'
    modifier.object = right
    return result

def inspect(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        bm = bmesh.new()
        try:
            bm.from_mesh(mesh)
            bm.verts.ensure_lookup_table()
            volume = abs(bm.calc_volume(signed=True))
            remaining = set(v.index for v in bm.verts)
            groups = []
            while remaining:
                root = remaining.pop()
                queue = [bm.verts[root]]
                n = 1
                while queue:
                    current = queue.pop()
                    for edge in current.link_edges:
                        adjacent = edge.other_vert(current)
                        if adjacent.index in remaining:
                            remaining.remove(adjacent.index)
                            queue.append(adjacent)
                            n += 1
                groups.append(n)
            bbox = [tuple(obj.matrix_world @ Vector(v)) for v in mesh.vertices]
            lo = [min(p[i] for p in bbox) for i in range(3)]
            hi = [max(p[i] for p in bbox) for i in range(3)]
            return {
                'vertices': len(bm.verts), 'faces': len(bm.faces),
                'components': len(groups), 'component_vertices': sorted(groups),
                'volume': volume, 'lo': lo, 'hi': hi,
            }
        finally:
            bm.free()
    finally:
        evaluated.to_mesh_clear()

def check(condition, message):
    if not condition:
        raise AssertionError(message)

def main(out_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    # A 2x2x2 cube with its .4-radius 3m cylinder should have volume ~6.997m3.
    # Both are translated 3m. A broken transform acting on result only leaves
    # the cutter behind and produces the wrong volume 8m3.
    t = Matrix.Translation(Vector((3, 0, 0)))
    left = cube('translated_cube', t)
    right = cylinder('translated_cutter', t)
    correct = boolean(left, right, 'DIFFERENCE', 'correct_outer_translation')
    observed = inspect(correct)
    target = 8.0 - 2.0 * math.pi * 0.4**2
    check(abs(observed['volume'] - target) < 0.015,
          'Boolean operand failed to follow translated source frame: ' + str(observed))
    check(abs(observed['lo'][0] - 2.0) < 1e-5 and abs(observed['hi'][0] - 4.0) < 1e-5,
          'Translated source bounds did not survive')
    # A deliberate invalid construction is a sensitivity/negative control.
    wrong_left = cube('wrong_parent_transform', t)
    wrong_right = cylinder('wrong_unmoved_cutter', Matrix.Identity(4))
    wrong = boolean(wrong_left, wrong_right, 'DIFFERENCE', 'negative_control')
    negative = inspect(wrong)
    check(abs(negative['volume'] - 8.0) < .015,
          'Negative control no longer distinguishes misplaced cutter')
    # A tiny detached component must survive the Boolean union.
    large = sphere('large', 1.0, Matrix.Identity(4))
    tiny = sphere('tiny', .01, Matrix.Translation(Vector((1.8, 0, 0))))
    joined = boolean(large, tiny, 'UNION', 'tiny_disconnected_union')
    result = inspect(joined)
    check(result['components'] == 2,
          'Independent tiny sphere disappeared or merged: ' + str(result))
    check(result['hi'][0] > 1.809,
          'Small component x-bound was truncated: ' + str(result))
    # Geometry of evaluated result should remain unchanged when hidden operands
    # are excluded from visible editor output. Blender relies on references.
    for obj in bpy.context.scene.objects:
        if obj != joined:
            obj.hide_render = True
            obj.hide_set(True)
    joined.hide_set(False)
    after_hide = inspect(joined)
    check(after_hide['components'] == 2, 'Hidden Boolean operand changed evaluated result')
    bpy.ops.object.select_all(action='DESELECT')
    joined.select_set(True)
    bpy.context.view_layer.objects.active = joined
    blend = out / 'synthetic-csg.blend'
    glb = out / 'synthetic-csg.glb'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.export_scene.gltf(
        filepath=str(glb), export_format='GLB',
        use_selection=True, export_apply=True, export_extras=True)
    check(blend.exists() and glb.exists(), 'Native or runtime artifact missing')
    receipt = {
        'fixture': 'r97-independent-public-synthetic-csg',
        'blender_version': bpy.app.version_string,
        'translated_difference': observed,
        'known_wrong_negative': negative,
        'tiny_sphere_union': result,
        'hidden_operand_union': after_hide,
        'native_blend_bytes': blend.stat().st_size,
        'glb_bytes': glb.stat().st_size,
        'status': 'NATIVE_HEADLESS_ASSERTIONS_PASSED',
        'limitations': 'No Oneirifact source, compiler, private materials, rig, UI or full-repo tests were used',
    }
    (out / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print('R97 SYNTHETIC BLENDER PASS', json.dumps(receipt, sort_keys=True))

if __name__ == '__main__':
    if '--' not in sys.argv or len(sys.argv[sys.argv.index('--') + 1:]) != 1:
        raise SystemExit('usage: blender --background --python public_blender_csg.py -- OUTDIR')
    main(sys.argv[sys.argv.index('--') + 1])
