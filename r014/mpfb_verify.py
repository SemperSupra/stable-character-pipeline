"""Fresh Blender process independent MPFB body scene QA, research only."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser()
p.add_argument('--blend',required=True,type=Path)
p.add_argument('--receipt',required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve(),'not reopened'
out={'schema':'r014.mpfb.reopened.v1','blender':bpy.app.version_string,'models':[]}
for sex in ('female','male'):
    mesh=bpy.data.objects['R014_'+sex+'_body']
    rig=bpy.data.objects['R014_'+sex+'_rig']
    mods=[m for m in mesh.modifiers if m.type=='ARMATURE' and m.object==rig]
    assert mods,sex+' mesh lost rig modifier'
    assert len(mesh.data.vertices)>1000
    assert len(rig.data.bones)>20
    assert len(mesh.vertex_groups)>20
    valid={v.name for v in mesh.vertex_groups}
    bones=[p for p in rig.pose.bones if p.bone.use_deform and p.name in valid]
    assert bones,'no deformable bone with weight groups'
    dep=bpy.context.evaluated_depsgraph_get()
    def sample():
        obj=mesh.evaluated_get(dep)
        evaluated=obj.to_mesh()
        try:return [tuple(v.co) for v in evaluated.vertices]
        finally:obj.to_mesh_clear()
    base=sample()
    bone=bones[0];bone.rotation_mode='XYZ'
    old=tuple(bone.rotation_euler);bone.rotation_euler[1]=old[1]+0.3
    bpy.context.view_layer.update()
    posed=sample()
    d=max((Vector(x)-Vector(y)).length for x,y in zip(base,posed))
    assert d>1e-4,sex+' deformation did not change'
    bone.rotation_euler=old
    out['models'].append({'sex':sex,'vertices':len(mesh.data.vertices),'bones':len(rig.data.bones),
                          'weighted_deform_bones':len(bones),'max_vertex_delta_m':d})
out['status']='PASS_REOPEN_AND_DEFORM_STRUCTURAL_ONLY'
out['limits']=['No face/hand realism rating','No muscle or tissue physics','No PBR skin/hair/video qualification']
a.receipt.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print('R014_MPFB_REOPEN',json.dumps(out,sort_keys=True))
