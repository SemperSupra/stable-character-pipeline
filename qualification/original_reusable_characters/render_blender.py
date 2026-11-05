#!/usr/bin/env python3
"""Blender 4.5 original generated GLB import, editable scene and two-camera render.

Only original GLB from local generator is admitted. This is technical media output,
not independent human-appearance, anatomy, or ground-contact acceptance.
"""
import json,hashlib,math,sys
from pathlib import Path
import bpy
from mathutils import Vector

def main(argv):
    src=Path(argv[0]).resolve();out=Path(argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
    expected=argv[2]
    observed=hashlib.sha256(src.read_bytes()).hexdigest()
    if observed!=expected:raise RuntimeError('SOURCE_GLB_DIGEST_MISMATCH')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(src))
    arms=[o for o in bpy.data.objects if o.type=='ARMATURE']
    skinned=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
    if len(arms)!=2 or len(skinned)<2:raise RuntimeError('BLENDER_SKIN_IMPORT_MISSING')
    if any(len(o.data.bones)<17 for o in arms):raise RuntimeError('BLENDER_ARMATURE_TOO_SMALL')
    scene=bpy.context.scene
    scene.frame_start=0;scene.frame_end=71;scene.render.fps=12
    scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
    if scene.world is None:
        scene.world=bpy.data.worlds.new('OriginalSyntheticParkWorld')
    scene.world.color=(.18,.23,.19)
    # Original world environment built in Blender; no external image assets.
    def material(n,color):
        m=bpy.data.materials.new(n);m.diffuse_color=(*color,1);return m
    ground=material('park_grass',(.18,.33,.17));path_mat=material('park_path',(.39,.34,.28))
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.055));floor=bpy.context.object
    floor.name='OriginalParkGround';floor.dimensions=(13,7,.10);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);floor.data.materials.append(ground)
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,-.002));path=bpy.context.object
    path.name='OriginalParkWalkway';path.dimensions=(12.0,1.8,.02);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);path.data.materials.append(path_mat)
    # Trees behind the actor path. No imported scenery.
    bark=material('park_bark',(.33,.21,.11));leaf=material('park_leaf',(.09,.26,.13))
    for x,y in ((-5.2,-2.6),(-2.3,-2.9),(2.6,-2.8),(5.2,-2.5)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=9,radius=.095,depth=1.8,location=(x,y,.88))
        bpy.context.object.data.materials.append(bark)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=.52,location=(x,y,2.0))
        ob=bpy.context.object;ob.scale=(1.,.85,1.0);ob.data.materials.append(leaf)
    camera_data=bpy.data.cameras.new('OriginalParkCamera');camera=bpy.data.objects.new('OriginalParkCamera',camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera=camera;camera_data.type='ORTHO';camera_data.ortho_scale=8.8
    def aim(loc,target):
        camera.location=loc;direction=Vector(target)-camera.location
        camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'original_park_editable.blend'))
    counts={}
    for view,loc in [('front',(0,12,2.0)),('oblique',(4.2,10.5,3.2))]:
        folder=out/view;folder.mkdir(parents=True,exist_ok=True)
        aim(loc,(0,0,1.0))
        for frame in range(72):
            scene.frame_set(frame)
            scene.render.filepath=str(folder/f'frame_{frame:03d}.png')
            bpy.ops.render.render(write_still=True)
        counts[view]=72
    # Independent review close-ups: both directions are rendered because the
    # original rig's world-facing rest axes have not been clinically calibrated.
    portraits=out/'portraits';portraits.mkdir(parents=True,exist_ok=True)
    scene.frame_set(0)
    camera_data.ortho_scale=1.25
    portrait_names=[]
    # Yaw-aligned owner-original approach: Aster faces +world X, Juniper -X.
    # Subject-specific face and back cameras, not assumptions about world Y.
    portrait_isolation={}
    for actor_x,actor_name,forward_x in ((-3.35,'aster',1.0),(3.35,'juniper',-1.0)):
        other='JuniperOriginal' if actor_name=='aster' else 'AsterOriginal'
        hidden={obj:obj.hide_render for obj in bpy.data.objects if obj.name.startswith(other)}
        if len(hidden)<2:
            raise RuntimeError('PORTRAIT_OTHER_ACTOR_ISOLATION_NOT_FOUND')
        portrait_isolation[actor_name]=len(hidden)
        try:
            for obj in hidden:obj.hide_render=True
            for camera_side,direction in (('face',1.0),('rear',-1.0)):
                aim((actor_x+direction*forward_x*3.0,0,1.70),(actor_x,0,1.64))
                name=f'{actor_name}_{camera_side}.png'
                scene.render.filepath=str(portraits/name)
                bpy.ops.render.render(write_still=True)
                portrait_names.append(name)
        finally:
            for obj,previous in hidden.items():obj.hide_render=previous
    camera_data.ortho_scale=8.8
    aim((4.2,10.5,3.2),(0,0,1.0))
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'original_park_editable.blend'))
    receipt={'schema':'scp.original_reusable_blender.v1','status':'NATIVE_IMPORT_RENDERED_UNREVIEWED',
             'input_sha256':observed,'frames':counts,
             'armatures':{a.name:len(a.data.bones) for a in arms},
             'skinned_mesh_objects':[x.name for x in skinned],
             'native_blender_import':True,'camera_corrective':'V2_FACE_SIDE_BACKGROUND_ONLY_FIRST_FAILED_RUN_RETAINED','source_class':'ORIGINAL_SELF_AUTHORED_SYNTHETIC',
             'human_identity':'NOT_APPLICABLE','anatomical_foot_contact':'UNKNOWN',
             'photorealism':'NOT_ACCEPTED','portrait_views':portrait_names,'portrait_partner_objects_hidden':portrait_isolation,'facial_detail_accepted':False,'product_accepted':False}
    (out/'native_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)!=3:raise SystemExit('USAGE GLB OUTPUT_DIR EXPECTED_SHA256')
    main(args)
