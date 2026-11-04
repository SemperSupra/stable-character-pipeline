"""First-source-bound 80-bone gait candidate in real native Blender; does NOT certify human biomechanics."""
import bpy, sys, json, math, hashlib
from pathlib import Path
from mathutils import Vector

FPS=12
FRAMES=72
EXPECTED=('RB_RB_F01_root','RB_RB_F02_root')
MOTION_BONES=('Bip01 L Thigh','Bip01 L Calf','Bip01 R Thigh','Bip01 R Calf',
              'Bip01 L UpperArm','Bip01 R UpperArm','Bip01 L Forearm','Bip01 R Forearm')

def fail(message):raise RuntimeError(message)

def run(inp,out):
    out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(inp))
    scene=bpy.context.scene;scene.frame_start=0;scene.frame_end=71;scene.render.fps=FPS
    scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    if scene.world is None:scene.world=bpy.data.worlds.new('OriginalMotionWorld')
    scene.world.color=(.22,.28,.22)
    actors=[]
    for idx,rootname in enumerate(EXPECTED):
        root=bpy.data.objects.get(rootname)
        if not root:fail('MISSING_NATIVE_OWNER_ROOT:'+rootname)
        armatures=[o for o in bpy.data.objects if o.type=='ARMATURE' and (o.parent==root or o.parent and o.parent.parent==root)]
        if len(armatures)!=1:fail('AMBIGUOUS_NATIVE_ARMATURE:'+rootname+':'+str(len(armatures)))
        arm=armatures[0]
        for k in MOTION_BONES:
            pb=arm.pose.bones.get(k)
            if pb is None:fail('MISSING_EXPECTED_BONE:'+rootname+':'+k)
            pb.rotation_mode='XYZ'
        actors.append((root,arm))
    # These are authored local-axis pose DOFs for an engineering demonstration, NOT inferred anatomy.
    for i,(root,arm) in enumerate(actors):
        start=-2.9 if i==0 else 2.9
        end=-.85 if i==0 else .85
        root.rotation_mode='XYZ'
        root.rotation_euler.z=math.pi/2 if i==0 else -math.pi/2
        root.keyframe_insert(data_path='rotation_euler',frame=0)
        for frame in range(FRAMES):
            t=frame/(FRAMES-1)
            root.location.x=start+(end-start)*t
            root.keyframe_insert(data_path='location',frame=frame)
            phase=2*math.pi*1.15*(frame/FPS)+i*.3
            values={
              'Bip01 L Thigh':.38*math.sin(phase),'Bip01 R Thigh':-.38*math.sin(phase),
              'Bip01 L Calf':.23+.30*max(0,math.sin(phase)),
              'Bip01 R Calf':.23+.30*max(0,-math.sin(phase)),
              'Bip01 L UpperArm':-.25*math.sin(phase),'Bip01 R UpperArm':.25*math.sin(phase),
              'Bip01 L Forearm':.10+.05*math.sin(phase),
              'Bip01 R Forearm':.10-.05*math.sin(phase)
            }
            for k,angle in values.items():
                bone=arm.pose.bones[k]
                bone.rotation_euler.x=angle
                bone.keyframe_insert(data_path='rotation_euler',frame=frame,group=k)
    # Remove original empty background objects? Preserve native staged scene and use actual recorded native skin.
    camera=scene.camera
    if camera is None:fail('NO_NATIVE_CAMERA')
    camera.data.type='ORTHO';camera.data.ortho_scale=7.7
    samples=[]
    for frame in (0,3,18,36,54,71):
        scene.frame_set(frame);bpy.context.view_layer.update()
        info=[]
        for root,arm in actors:
            mesh=[o for o in bpy.data.objects if o.type=='MESH' and (o.parent==arm or any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers))]
            if not mesh:fail('NO_REAL_NATIVE_SKIN:'+root.name)
            ob=mesh[0];ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
            try:
                # Lower bound from ACTUAL evaluated mesh coordinates, not producer synthetic stance labels.
                world=[ev.matrix_world @ v.co for v in m.vertices]
                if not world:fail('NO_EVALUATED_VERTICES')
                zmin=min(v.z for v in world)
                xmin=min(v.x for v in world);xmax=max(v.x for v in world)
                cx=sum(v.x for v in world)/len(world)
                info.append({'root':root.name,'mean_x':float(cx),'bounds_x':[float(xmin),float(xmax)],'evaluated_mesh_min_z':float(zmin),
                  'animated_local_bones':{k:float(arm.pose.bones[k].rotation_euler.x) for k in MOTION_BONES}})
            finally:ev.to_mesh_clear()
        samples.append({'frame':frame,'actors':info})
    # Actual source bone rotation liveness must appear at distinct frames, and actors must approach.
    for i in range(2):
        x0=samples[0]['actors'][i]['mean_x'];xend=samples[-1]['actors'][i]['mean_x']
        if abs(xend-x0)<1.0:fail('STATIC_ROOT_ONLY_MOTION:'+str(i))
        arm_samples=[p['actors'][i]['animated_local_bones']['Bip01 L Thigh'] for p in samples]
        if max(arm_samples)-min(arm_samples)<.3:fail('STATIC_BONE_ANIMATION:'+str(i))
    cam_data=scene.camera
    counts={}
    for view,loc in [('front',(0,-10,2.2)),('oblique',(3.0,-9.0,3.0))]:
        folder=out/view;folder.mkdir(exist_ok=True)
        cam_data.location=loc;cam_data.rotation_euler=(Vector((0,0,1.1))-cam_data.location).to_track_quat('-Z','Y').to_euler()
        for frame in range(FRAMES):
            scene.frame_set(frame)
            scene.render.filepath=str(folder/f'frame_{frame:03d}.png')
            bpy.ops.render.render(write_still=True)
        counts[view]=FRAMES
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'mit_rocketbox_walk_candidate.blend'))
    rec={'schema':'scp.mit_rocketbox_native_walk.v1','status':'NATIVE_SKINNED_WALK_SOURCE_ONLY_NOT_HUMAN_ACCEPTED',
         'source_rights':'MIT_with_notice','frame_count':FRAMES,'fps':FPS,
         'profile':'two_80_bone_actual_source_mesh_actors','views':counts,
         'bone_basis_calibrated':False,'foot_contact':'UNKNOWN','human_gait':'UNKNOWN',
         'camera_visual_acceptance':'UNKNOWN','product_accepted':False,'samples':samples}
    (out/'native_motion_receipt.json').write_text(json.dumps(rec,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':rec['status'],'source_rights':rec['source_rights'],'views':counts,'liveness':'PER_BONE_AND_EVALUATED_MESH_PASS'},sort_keys=True))

if __name__=='__main__':
    if '--' not in sys.argv:fail('ARGS_REQUIRED')
    args=sys.argv[sys.argv.index('--')+1:]
    if len(args)!=2:fail('USAGE input.blend outdir')
    run(Path(args[0]).resolve(),Path(args[1]).resolve())
