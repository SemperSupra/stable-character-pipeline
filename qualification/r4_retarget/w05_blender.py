"""Native Blender wheel target skin and source-bound GLB roundtrip.

Original synthetic data only. No physical gait, human anatomy, true depth.
"""
import bpy
import hashlib
import json
import math
import sys
from pathlib import Path
from w05_contract import read_motion

if len(sys.argv)!=3:
    raise SystemExit('usage: python w05_blender.py MOTION_JSON OUT_DIR')
src=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
xs,src_sha=read_motion(src)
fps=24
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.fps=fps
arm_data=bpy.data.armatures.new('OriginalPublicSyntheticTarget4Joint')
arm=bpy.data.objects.new('TargetFourJointRig',arm_data)
scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm
arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
# Rest shape in Blender XY camera plane. This is an authored synthetic rig.
parts=[
('base',None,(0,0,0),(0,.2,0)),
('pivot','base',(0,0,0),(0,1.5,0)),
('hinge','pivot',(0,1.5,0),(0,1.1,0)),
('tip','hinge',(0,1.1,0),(0,.1,0))]
for name,parent,head,tail in parts:
    b=arm_data.edit_bones.new(name)
    b.head=head
    b.tail=tail
    if parent:
        b.parent=arm_data.edit_bones[parent]
        b.use_connect=False
bpy.ops.object.mode_set(mode='OBJECT')
mesh=bpy.data.meshes.new('HingeSkinTriangleOriginalSynthetic')
mesh.from_pydata([(-.06,1.2,0),(.06,1.2,0),(-.06,1.3,0),(.06,1.3,0)],[],[(0,1,2),(1,3,2)])
mesh.update()
obj=bpy.data.objects.new('SyntheticWeightedHingeSkin',mesh)
scene.collection.objects.link(obj)
group=obj.vertex_groups.new(name='hinge')
group.add([0,1,2,3],1.0,'REPLACE')
m=obj.modifiers.new('PublicSyntheticSkin','ARMATURE');m.object=arm
obj.parent=arm
pose=arm.pose.bones['hinge']
for idx,value in enumerate(xs):
    scene.frame_set(idx*fps)
    pose.location=(value,0,0)
    pose.keyframe_insert(data_path='location',frame=idx*fps,group='synthetic_hinge',index=-1)
pose.location=(0,0,0)
scene.frame_set(0)
def sample_mesh():
    bpy.context.view_layer.update()
    dep=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(dep)
    m=ev.to_mesh()
    pts=[tuple(ev.matrix_world@v.co) for v in m.vertices]
    ev.to_mesh_clear()
    return pts
first=sample_mesh()
sampled=[]
for i,x in enumerate(xs):
    scene.frame_set(i*fps)
    pts=sample_mesh()
    dx=[p[0]-q[0] for p,q in zip(pts,first)]
    if len(pts)!=4 or max(abs(v-x) for v in dx)>1e-5:
        raise ValueError('BLENDER_NATIVE_WEIGHTED_TARGET_SKIN_MISMATCH')
    if any(abs(p[2])>1e-6 for p in pts):
        raise ValueError('SYNTHETIC_DEPTH_INVENTED')
    sampled.append({'source_ms':i*1000,'blender_frame':i*fps,'delta_x':[round(v,9) for v in dx]})
bpy.ops.wm.save_as_mainfile(filepath=str((out/'r4-w05-native-target.blend').resolve()))
bpy.ops.export_scene.gltf(filepath=str((out/'r4-w05-native-target.glb').resolve()),
                         export_format='GLB',export_animations=True)
glb=out/'r4-w05-native-target.glb'
if not glb.exists() or glb.stat().st_size<1000:raise RuntimeError('NO_NATIVE_BLENDER_GLB')
# Genuine independent import into fresh bpy scene, not a copy of in-memory mesh.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.fps=fps
bpy.ops.import_scene.gltf(filepath=str(glb.resolve()))
skinned=[ob for ob in bpy.data.objects if ob.type=='MESH' and
         any(mod.type=='ARMATURE' for mod in ob.modifiers)]
if len(skinned)!=1 or not bpy.data.actions:raise RuntimeError('NO_IMPORTED_SKIN_ANIMATION')
imp=skinned[0]
def imported_pts(frame):
    scene.frame_set(frame);bpy.context.view_layer.update()
    ev=imp.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=ev.to_mesh()
    pts=[tuple(ev.matrix_world@v.co) for v in mesh.vertices]
    ev.to_mesh_clear()
    return pts
original=imported_pts(0)
readback=[]
for i,x in enumerate(xs):
    pts=imported_pts(i*fps)
    if len(pts)!=4:raise RuntimeError('REIMPORTED_VERTEX_COUNT_CHANGED')
    shifts=[p[0]-q[0] for p,q in zip(pts,original)]
    if max(abs(delta-x) for delta in shifts)>0.0005:
        raise RuntimeError('REIMPORTED_GLB_ANIMATED_SKIN_PARITY_FAIL')
    readback.append({'source_ms':i*1000,'blender_frame':i*fps,'indexed_x_delta':shifts})
receipt={'schema':'stable-character/r4-w05-native-blender-synthetic/1',
         'status':'PASS_NATIVE_BLENDER_SKIN_AND_GLB_REIMPORT',
         'source_rights':'ORIGINAL_SELF_AUTHORED_SYNTHETIC',
         'source_w04_motion_sha256':src_sha,
         'blender':bpy.app.version_string,'glb_sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),
         'native_animated_target':sampled,'reimport_evaluated':readback,
         'camera_plane_source_only':True,'real_3d_or_biomechanics':'NOT_MEASURED',
         'human_identity':'NOT_TESTED','physical_contact':'NOT_TESTED',
         'independent_external_gltf_reader':'NOT_TESTED'}
(out/'r4-w05-native-receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print('R4_W05_NATIVE_TARGET_SKIN_PASS',json.dumps(receipt,sort_keys=True))
