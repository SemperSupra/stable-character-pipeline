"""MIT Rocketbox independent native visual/skeleton probe, not gait acceptance."""
import bpy, json, math, sys, hashlib
from pathlib import Path
from mathutils import Vector


def ensure(cond, msg):
    if not cond: raise RuntimeError(msg)


def pose_actor(source, name, x):
    before={o.name for o in bpy.data.objects}
    bpy.ops.import_scene.fbx(filepath=str(source), use_anim=True)
    obs=[o for o in bpy.data.objects if o.name not in before]
    arms=[o for o in obs if o.type=='ARMATURE']
    meshes=[o for o in obs if o.type=='MESH']
    ensure(len(arms)>=1 and len(meshes)>=1, 'FBX_MISSING_ARMATURE_OR_MESH:'+name)
    top=[o for o in obs if o.parent is None]
    group=bpy.data.objects.new('RB_'+name+'_root',None)
    bpy.context.scene.collection.objects.link(group)
    # Preserve world transform while grouping independent imported top-level objects.
    for o in top:
        mx=o.matrix_world.copy();o.parent=group;o.matrix_world=mx
    deps=bpy.context.evaluated_depsgraph_get()
    bounds=[]
    for o in meshes:
        for pt in o.bound_box:
            p=o.matrix_world@Vector(pt)
            bounds.append((float(p.x),float(p.y),float(p.z)))
    ensure(bounds and all(math.isfinite(v) for p in bounds for v in p),'FBX_NONFINITE_BOUNDS')
    lo=[min(p[i] for p in bounds) for i in range(3)];hi=[max(p[i] for p in bounds) for i in range(3)]
    ext=[hi[i]-lo[i] for i in range(3)]
    vertical=ext[2]
    ensure(vertical>0.01 and vertical<100000,'FBX_INVALID_VERTICAL_EXTENT')
    scale=1.70/vertical
    group.scale=(scale,scale,scale)
    center=((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2])
    group.location=(x-scale*center[0], -scale*center[1], -scale*center[2])
    # preserve raw rig evidence; no synthetic animation or human locomotion claim.
    skin=[m for o in meshes for m in o.modifiers if m.type=='ARMATURE']
    report={'source_file':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'actor':name,'armatures':[{'name':a.name,'bone_count':len(a.data.bones),
           'bone_names':[b.name for b in a.data.bones]} for a in arms],
        'mesh_objects':len(meshes),'mesh_vertices':sum(len(o.data.vertices) for o in meshes),
        'skin_armature_modifiers':len(skin),'mesh_shape_keys':sum(len(o.data.shape_keys.key_blocks) for o in meshes if o.data.shape_keys),
        'source_vertical_extent':vertical,'converted_height_m':1.70,
        'motion':'NOT_RUN_STATIC_POSE_RIG_PROBE', 'photorealism':'UNKNOWN', 'rights':'MICROSOFT_ROCKETBOX_MIT_WITH_NOTICE',
        'product_accepted':False}
    ensure(report['mesh_vertices']>500 and report['skin_armature_modifiers']>0,'NO_SKINNED_BODY')
    return report


def main(argv):
    first=Path(argv[0]);second=Path(argv[1]);out=Path(argv[2]);out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    one=pose_actor(first,'RB_F01',-1.6)
    two=pose_actor(second,'RB_F02',1.6)
    scene=bpy.context.scene
    if scene.world is None:scene.world=bpy.data.worlds.new('MIT_Rocketbox_Source_Probe_World')
    scene.world.color=(.19,.22,.20)
    scene.render.engine='BLENDER_WORKBENCH'
    scene.display.shading.light='STUDIO'
    scene.display.shading.color_type='MATERIAL'
    scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    def matte(name,color):
        m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
    m=matte('GrayFloor',(.36,.38,.36))
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.065))
    floor=bpy.context.object;floor.name='SourceProbeGround';floor.dimensions=(9,4,.1)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);floor.data.materials.append(m)
    camd=bpy.data.cameras.new('ProbeCamera');cam=bpy.data.objects.new('ProbeCamera',camd)
    scene.collection.objects.link(cam);scene.camera=cam
    camd.type='ORTHO';camd.ortho_scale=7.0
    for label,loc in [('front',(0,-9,2.2)),('oblique',(3,-8,3.0))]:
        cam.location=loc;cam.rotation_euler=(Vector((0,0,.95))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/(label+'.png'))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'rocketbox_mit_rig_probe.blend'))
    receipt={'schema':'scp.r009.mit_rocketbox_native_probe.v1','source_commit':'0943055db6ec570bcef9f2c8b41c9e5467c808f9',
      'actors':[one,two],'source_rights':'MIT_LICENSE_NOTICE_PRESERVED','status':'NATIVE_STATIC_RIG_PROBE_ONLY',
      'walking':'NOT_RUN','independent_visual_acceptance':'UNKNOWN','product_accepted':False}
    (out/'native_probe.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':receipt['status'],'actors':[{'actor':i['actor'],'armatures':len(i['armatures']),'mesh_vertices':i['mesh_vertices'],'skin_modifiers':i['skin_armature_modifiers']} for i in receipt['actors']]},sort_keys=True))

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    ensure(len(args)==3,'USAGE: F01 F02 OUTPUT')
    main(args)
