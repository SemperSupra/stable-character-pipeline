"""Native Blender procedural fixture; validates save/reopen rig+morph only."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector

def points(obj):
    dg=bpy.context.evaluated_depsgraph_get()
    eo=obj.evaluated_get(dg);me=eo.to_mesh()
    try:return [tuple(v.co) for v in me.vertices]
    finally:eo.to_mesh_clear()

def delta(a,b):return max((Vector(x)-Vector(y)).length for x,y in zip(a,b))

def create(path):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    data=bpy.data.armatures.new('R014Armature');rig=bpy.data.objects.new('R014Rig',data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    b=data.edit_bones.new('base');b.head=(0,0,0);b.tail=(0,0,1)
    d=data.edit_bones.new('distal');d.head=(0,0,1);d.tail=(0,0,2);d.parent=b
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    N=12;verts=[];faces=[]
    for z in (0.0,0.5,1.0,1.5,2.0):
        for i in range(N):
            a=i*2*math.pi/N;verts.append((0.08*math.cos(a),0.08*math.sin(a),z))
    for r in range(4):
        for i in range(N):
            j=(i+1)%N
            faces.append((r*N+i,r*N+j,(r+1)*N+j,(r+1)*N+i))
    faces.extend([tuple(reversed(range(N))),tuple(4*N+i for i in range(N))])
    mesh=bpy.data.meshes.new('Skin');mesh.from_pydata(verts,[],faces);mesh.update()
    obj=bpy.data.objects.new('R014Body',mesh);bpy.context.collection.objects.link(obj)
    lower=obj.vertex_groups.new(name='base');upper=obj.vertex_groups.new(name='distal')
    for i,v in enumerate(verts):
        t=max(0,min(1,v[2]-0.5))
        if t<1:lower.add([i],1-t,'REPLACE')
        if t>0:upper.add([i],t,'REPLACE')
    obj.shape_key_add(name='Basis',from_mix=False)
    morph=obj.shape_key_add(name='test_corrective',from_mix=False)
    for i in range(4*N,5*N):morph.data[i].co.x+=0.03
    obj.parent=rig
    obj.modifiers.new('Skinning','ARMATURE').object=rig
    rig.pose.bones['distal'].rotation_mode='XYZ'
    bpy.context.view_layer.update()
    before=points(obj)
    rig.pose.bones['distal'].rotation_euler[1]=0.55;morph.value=0.7
    bpy.context.view_layer.update();movement=delta(before,points(obj))
    assert movement>0.05,('no deformation',movement)
    rig.pose.bones['distal'].rotation_euler=(0,0,0);morph.value=0
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(path.resolve()))
    return {'status':'PASS_NATIVE_PRODUCER','blender':bpy.app.version_string,'motion_m':movement,'vertices':len(verts)}

def verify(path):
    assert Path(bpy.data.filepath).resolve()==path.resolve(),'not reopened'
    rig=bpy.data.objects['R014Rig'];obj=bpy.data.objects['R014Body']
    assert obj.data.shape_keys and 'test_corrective' in obj.data.shape_keys.key_blocks
    assert any(x.type=='ARMATURE' and x.object==rig for x in obj.modifiers)
    rig.pose.bones['distal'].rotation_euler=(0,0,0)
    sk=obj.data.shape_keys.key_blocks['test_corrective'];sk.value=0
    bpy.context.view_layer.update();before=points(obj)
    rig.pose.bones['distal'].rotation_euler[1]=0.55;sk.value=0.7
    bpy.context.view_layer.update();movement=delta(before,points(obj))
    assert movement>0.05,('no deformation after fresh reopen',movement)
    bone=rig.pose.bones['distal']
    for frame,a,shape in [(1,0,0),(13,0.55,0.7),(25,0,0)]:
        bone.rotation_euler[1]=a;bone.keyframe_insert(data_path='rotation_euler',frame=frame)
        sk.value=shape;sk.keyframe_insert(data_path='value',frame=frame)
    bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=25
    out=path.parent/'r014_native_synthetic.glb'
    bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',export_animations=True,
                              export_morph=True,export_skins=True,export_yup=True)
    return {'status':'PASS_NATIVE_REOPEN','blender':bpy.app.version_string,'motion_m':movement,'glb':out.name}

p=argparse.ArgumentParser()
p.add_argument('--phase',required=True,choices=['create','verify'])
p.add_argument('--blend',required=True,type=Path)
p.add_argument('--receipt',required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
r=create(a.blend) if a.phase=='create' else verify(a.blend)
r['scope']='synthetic infrastructure ONLY; no human realism or tissue physics'
a.receipt.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
print('R014:',json.dumps(r,sort_keys=True))
