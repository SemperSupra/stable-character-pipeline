"""R014 MPFB native Workbench visual evidence; not photorealism qualification."""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument('--output',required=True,type=Path)
p.add_argument('--receipt',required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
a.output.mkdir(parents=True,exist_ok=True)
assert 'R014_female_body' in bpy.data.objects
assert 'R014_male_body' in bpy.data.objects
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=8
scene.render.threads_mode='FIXED'
scene.render.threads=4
scene.render.resolution_x=640
scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.film_transparent=False
world=bpy.data.worlds.new('R014NeutralWorld')
world.use_nodes=True
world.node_tree.nodes.get('Background').inputs['Color'].default_value=(0.7,0.73,0.78,1.0)
world.node_tree.nodes.get('Background').inputs['Strength'].default_value=0.8
scene.world=world
lamp_data=bpy.data.lights.new('R014AreaKey','AREA')
lamp=bpy.data.objects.new('R014AreaKey',lamp_data)
bpy.context.collection.objects.link(lamp)
lamp.location=(2.0,-3.0,4.0)
lamp_data.energy=600
lamp_data.shape='DISK'
lamp_data.size=5.0
camera_data=bpy.data.cameras.new('R014_QA_camera')
cam=bpy.data.objects.new('R014_QA_camera',camera_data)
bpy.context.collection.objects.link(cam)
scene.camera=cam
camera_data.type='ORTHO'
def point_at(place,target,scale):
    cam.location=place
    direction=Vector(target)-cam.location
    cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    camera_data.ortho_scale=scale
def still(name,place,target,scale):
    point_at(place,target,scale)
    scene.render.filepath=str(a.output/(name+'.png'))
    bpy.ops.render.render(write_still=True)

still('pair_front',(0,-6,1.7),(0,0,1.05),2.65)
still('pair_back',(0,6,1.7),(0,0,1.05),2.65)
still('pair_side',(6,0,1.7),(0,0,1.05),2.65)
still('female_face',(-0.8,-2.7,1.65),(-0.8,0,1.65),0.68)
still('male_face',(0.8,-2.7,1.65),(0.8,0,1.65),0.68)
# The hands are laterally offset in the A-pose; avoid the misleading torso crop.
still('female_hands',(-0.28,-2.1,0.99),(-0.28,0,0.99),0.48)
still('male_hands',(1.32,-2.1,0.99),(1.32,0,0.99),0.48)
# A moving-camera test: actor bodies are NOT walking or talking.
scene.render.resolution_x=480
scene.render.resolution_y=480
scene.frame_start=1
scene.frame_end=24
for frame in range(1,25):
    angle=math.radians(-35+70*(frame-1)/23)
    place=(5.5*math.sin(angle),-5.5*math.cos(angle),1.7)
    point_at(place,(0,0,1.0),2.7)
    cam.keyframe_insert(data_path='location',frame=frame)
    cam.keyframe_insert(data_path='rotation_euler',frame=frame)
scene.render.filepath=str(a.output/'turntable_camera_only.mp4')
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4'
scene.render.ffmpeg.codec='H264'
bpy.ops.render.render(animation=True)
report={'status':'PASS_VISUAL_RECEIPTS_GENERATED_NOT_REVIEWED',
        'blender':bpy.app.version_string,
        'static_views':['pair_front','pair_back','pair_side','female_face','male_face','female_hands','male_hands'],
        'motion':'24 frame native Blender H.264 camera orbit ONLY; not humanoid motion',
        'limits':['Neutral CPU Cycles only','No photoreal skin/hair/eyes',
                  'No actual gait or soft-tissue mechanics','No face close-up realism acceptance']}
a.receipt.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print('R014_RENDER_RECEIPT',json.dumps(report,sort_keys=True))
