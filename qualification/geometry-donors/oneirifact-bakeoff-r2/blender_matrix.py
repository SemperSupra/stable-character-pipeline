"""Real DCC independent importer and exporter for public synthetic GLBs."""
import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector


def measure(path):
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 bpy.ops.import_scene.gltf(filepath=str(path))
 objs=[o for o in bpy.context.scene.objects if o.type=='MESH']
 assert len(objs)==1, (path,len(objs))
 obj=objs[0];bm=bmesh.new()
 try:
  bm.from_mesh(obj.data)
  nv,ne,nf=len(bm.verts),len(bm.edges),len(bm.faces)
  bad=sum(1 for edge in bm.edges if not edge.is_manifold)
  assert bad==0,(path,bad)
  seen=set();components=0
  for v in bm.verts:
   if v in seen:continue
   components+=1;stack=[v];seen.add(v)
   while stack:
    for edge in stack.pop().link_edges:
     # loop vertices directly so no dependence on bmesh edge vertex order
     for w in edge.verts:
      if w not in seen:seen.add(w);stack.append(w)
  chi=nv-ne+nf
  vol=bm.calc_volume(signed=True)*obj.matrix_world.determinant()
 finally:bm.free()
 corners=[obj.matrix_world@Vector(c) for c in obj.bound_box]
 lo=[min(v[i] for v in corners) for i in range(3)]
 hi=[max(v[i] for v in corners) for i in range(3)]
 assert (2*components-chi)%2==0
 return {'vertices':nv,'edges':ne,'faces':nf,'components':components,'chi':chi,'genus_sum':(2*components-chi)//2,'nonmanifold_edges':bad,'volume':vol,'bounds_min':lo,'bounds_max':hi,'blender_version':bpy.app.version_string}


def main():
 args=sys.argv[sys.argv.index('--')+1:]
 phase,path,report=args
 model=Path(path);out=measure(model)
 out['phase']=phase
 if phase=='import':
  bpy.ops.export_scene.gltf(filepath=str(model.with_suffix('.roundtrip.glb')),export_format='GLB')
 elif phase!='reimport':raise RuntimeError('bad phase')
 Path(report).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print('ONEIRIFACT_BLENDER_MATRIX_PASS',model.name,json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
