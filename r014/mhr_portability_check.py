"""Cross-application native .blend vs GLB mesh height and rig scale evidence."""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--phase',required=True,choices=['native','glb'])
p.add_argument('--glb',type=Path,required=True)
p.add_argument('--receipt',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
if a.phase=='glb':
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(a.glb))
objects=[o for o in bpy.data.objects if o.type=='MESH']
assert objects,'no meshes to evaluate'
body=max(objects,key=lambda o:len(o.data.vertices))
dg=bpy.context.evaluated_depsgraph_get()
evaluated=body.evaluated_get(dg)
mesh=evaluated.to_mesh()
try:
    pts=[evaluated.matrix_world @ v.co for v in mesh.vertices]
finally:
    evaluated.to_mesh_clear()
assert pts,'evaluated mesh is empty'
bounds=[tuple(min(p[i] for p in pts) for i in range(3)),
        tuple(max(p[i] for p in pts) for i in range(3))]
extent=[b-a for a,b in zip(bounds[0],bounds[1])]
r={'status':'MEASURED_NOT_YET_QUALIFIED','phase':a.phase,'mesh':body.name,
   'native_blender_version':bpy.app.version_string,'evaluated_vertices':len(pts),
   'bounds_world':bounds,'extent_world':extent,
   'mesh_world_scale':[float(x) for x in body.matrix_world.to_scale()],
   'unit_system':bpy.context.scene.unit_settings.system,
   'limits':['No FPS/rig animation pose parity','glTF skin import vs native size only',
             'Absolute correct human height requires explicit units contract']}
a.receipt.parent.mkdir(parents=True,exist_ok=True)
a.receipt.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print('R014_MHR_BOUNDS',json.dumps(r,sort_keys=True))
