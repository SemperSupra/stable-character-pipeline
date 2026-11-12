"""Independent native Blender importer/evaluator for one synthetic 3D test asset.

No Oneirifact source, only a previously-generated synthetic indexed GLB.
"""
import bpy
import bmesh
import json
import sys
from pathlib import Path
from mathutils import Vector


def evaluate(glb_path):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if len(objs) != 1:
        raise AssertionError(f'Expected one mesh, got {len(objs)}')
    obj = objs[0]
    mesh = obj.data
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        verts, edges, faces = len(bm.verts), len(bm.edges), len(bm.faces)
        boundary = sum(1 for e in bm.edges if not e.is_manifold)
        if boundary:
            raise AssertionError(f'{boundary} nonmanifold edges after GLB import')
        if verts - edges + faces != 0:
            raise AssertionError(f'Unexpected Euler characteristic: {verts-edges+faces}')
        seen = set()
        components = 0
        for v in bm.verts:
            if v in seen:
                continue
            components += 1
            pending = [v]
            seen.add(v)
            while pending:
                current = pending.pop()
                for e in current.link_edges:
                    other = e.other_vert(current)
                    if other not in seen:
                        seen.add(other)
                        pending.append(other)
        if components != 1:
            raise AssertionError(f'Expected one connected mesh, got {components}')
        local_volume = bm.calc_volume(signed=True)
        volume = local_volume * obj.matrix_world.determinant()
    finally:
        bm.free()
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    lower = [min(p[i] for p in corners) for i in range(3)]
    upper = [max(p[i] for p in corners) for i in range(3)]
    if not (6.5 < volume < 7.5):
        raise AssertionError(f'Unexpected approximate drilled-cube volume {volume}')
    if any(abs(lower[i]+1.0)>0.002 or abs(upper[i]-1.0)>0.002 for i in range(3)):
        raise AssertionError(f'Unexpected imported bounds {lower}, {upper}')
    return {
        'vertex_count': verts, 'edge_count': edges, 'face_count': faces,
        'euler_characteristic': verts-edges+faces,
        'components': components, 'nonmanifold_edges': boundary,
        'volume_m3': volume, 'bounds_min_m': lower, 'bounds_max_m': upper,
        'blender_version': bpy.app.version_string,
    }


def main():
    argv = sys.argv[sys.argv.index('--')+1:]
    mode, model, receipt = argv
    report = evaluate(Path(model))
    report['phase'] = mode
    if mode == 'import':
        bpy.ops.export_scene.gltf(filepath=str(Path(model).with_name('blender-roundtrip.glb')), export_format='GLB')
    elif mode != 'roundtrip':
        raise SystemExit(f'Unknown phase {mode}')
    Path(receipt).write_text(json.dumps(report, indent=2, sort_keys=True))
    print('ONEIRIFACT_PUBLIC_BLENDER_PASS', json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
