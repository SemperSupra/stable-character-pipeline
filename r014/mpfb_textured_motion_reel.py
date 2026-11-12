"""R014 native rigged/textured synthetic adult motion preview — research only.

Uses exact prior public GHA MADEskin scene, no regenerated humans or identity.
Three-second cycle demonstrates arm/leg pose and root orientation changes.
Not a realistic gait, collision/contact, tissue, facial acting or anatomy gate.
"""
import argparse,json,math,sys
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
import bpy

p=argparse.ArgumentParser()
p.add_argument("--sex",choices=["female","male"],required=True)
p.add_argument("--source",required=True,type=Path)
p.add_argument("--generation",required=True,type=Path)
p.add_argument("--out",required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
a.out.mkdir(parents=True,exist_ok=True)
assert Path(bpy.data.filepath).resolve()==a.source.resolve(), "unexpected source .blend"
gen=json.loads(a.generation.read_text())
assert gen["asset_archive_sha256"]=="b542127a8e25547c7c29c19f2d1d2adb9a664c80396ecd694095dbc8028a0107"
assert gen["eye_material_mode"]=="MAKESKIN"
assert {(c["sex"],c["source_gender_macro"]) for c in gen["characters"]}=={("female",0.),("male",1.)}
assert gen["blender"]=="4.5.16 LTS"

rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
opposite="male" if a.sex=="female" else "female"
other=bpy.data.objects["R014_"+opposite+"_textured_rig"]
assert rig.type=="ARMATURE" and len(rig.data.bones)==163
assert body.type=="MESH" and len(body.data.vertices)==19158
assert len([m for m in body.modifiers if m.type=="ARMATURE"])==1

def child_of(obj,parent):
    node=obj
    while node is not None:
        if node==parent:return True
        node=node.parent
    return False

# Hide opposing actor and attached hair/teeth/body meshes without changing
# source geometry. Everything else is sourced from the official public CC0 pack.
for obj in bpy.data.objects:
    if child_of(obj,other) or (obj.type=="MESH" and obj.name.startswith("R014_"+opposite)):
        obj.hide_render=True
        obj.hide_set(True)
assert not body.hide_render

# Rig conventions verified in prior MPFB native deform test; bone Y rotation
# is a deliberately illustrative articulation command, not human gait synthesis.
required=["upperarm01.L","upperarm01.R","upperleg01.L","upperleg01.R"]
missing=[n for n in required if n not in rig.pose.bones]
assert not missing,("missing source motion bones",missing)
optional=["lowerleg01.L","lowerleg01.R","lowerarm01.L","lowerarm01.R"]
animated=required+[n for n in optional if n in rig.pose.bones]
for n in animated:
    rig.pose.bones[n].rotation_mode="XYZ"
rig.rotation_mode="XYZ"
initial=rig.location.copy()
initial_euler=rig.rotation_euler.copy()
fps=24;end=72
scene=bpy.context.scene
scene.frame_start=1;scene.frame_end=end;scene.render.fps=fps
for frame in range(1,end+1):
    phase=2*math.pi*(frame-1)/24
    sine=math.sin(phase)
    rig.pose.bones["upperarm01.L"].rotation_euler[1]=.21*sine
    rig.pose.bones["upperarm01.R"].rotation_euler[1]=-.21*sine
    rig.pose.bones["upperleg01.L"].rotation_euler[1]=-.16*sine
    rig.pose.bones["upperleg01.R"].rotation_euler[1]=.16*sine
    for suffix,offset in ((".L",0.),(".R",math.pi)):
        name="lowerleg01"+suffix
        if name in rig.pose.bones:
            rig.pose.bones[name].rotation_euler[1]=.10*max(0,math.sin(phase+offset))
        name="lowerarm01"+suffix
        if name in rig.pose.bones:
            rig.pose.bones[name].rotation_euler[1]=.04*math.sin(phase+offset)
    for n in animated:
        rig.pose.bones[n].keyframe_insert(data_path="rotation_euler",frame=frame)
    rig.rotation_euler=initial_euler.copy()
    rig.rotation_euler.z+=.20*math.sin(2*math.pi*(frame-1)/(end-1))
    rig.location=initial.copy()
    rig.location.z+=.008*(1-math.cos(2*phase))
    rig.rotation_euler.z+=.08
    rig.keyframe_insert(data_path="rotation_euler",frame=frame)
    rig.keyframe_insert(data_path="location",frame=frame)
scene.frame_set(1)

# View: individual actor centered, head-to-toe silhouette, slight oblique
# angle so arm swing and gait-like weight shift remain perceptible.
center_x=float(initial.x)
cam_data=bpy.data.cameras.new("R014_Motion_Review_"+a.sex)
cam=bpy.data.objects.new("R014_Motion_Review_"+a.sex,cam_data)
bpy.context.collection.objects.link(cam)
cam_data.type="ORTHO";cam_data.ortho_scale=3.15
cam.location=(center_x+0.45,-5.1,1.5)
target=Vector((center_x,0,1.03))
cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
scene.camera=cam

light_data=bpy.data.lights.new("R014_Motion_Fill","AREA")
light=bpy.data.objects.new("R014_Motion_Fill",light_data)
bpy.context.collection.objects.link(light)
light.location=(center_x-1.4,-1.7,2.7)
light_data.size=3;light_data.energy=320
# Lower cycles samples for free-tier CPU research; true packed shader assets.
scene.render.engine="CYCLES"
scene.cycles.device="CPU";scene.cycles.samples=6
scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=448
scene.render.resolution_y=576
scene.render.resolution_percentage=100
scene.render.film_transparent=False
scene.render.image_settings.color_mode="RGB"
# Frame coverage needs real evaluated body geometry, not static object bounds.
# Check multiple key poses fail-closed if head/body is clipped.
coverage=[]
for frame in (1,12,24,36,48,60,72):
    scene.frame_set(frame)
    dg=bpy.context.evaluated_depsgraph_get()
    evaluated=body.evaluated_get(dg)
    mesh=evaluated.to_mesh()
    try:
        verts=[evaluated.matrix_world@v.co for v in mesh.vertices]
        sample=verts[::max(1,len(verts)//1500)]
    finally:evaluated.to_mesh_clear()
    projected=[world_to_camera_view(scene,cam,v) for v in sample]
    xs=[v.x for v in projected];ys=[v.y for v in projected];zs=[v.z for v in projected]
    bounds={"frame":frame,"min_x":min(xs),"max_x":max(xs),"min_y":min(ys),"max_y":max(ys),
            "near_depth":min(zs)}
    coverage.append(bounds)
    if bounds["min_x"]<-.02 or bounds["max_x"]>1.02 or bounds["min_y"]<-.02 or bounds["max_y"]>1.02 or bounds["near_depth"]<=0:
        raise ValueError("Body outside captured camera frame: "+str(bounds))
scene.frame_set(1)

# Save playable video and native Blender source; no camera-based quality pass.
filename="R014_MPFB_"+a.sex+"_textured_technical_motion_3s.mp4"
scene.render.filepath=str(a.out/filename)
scene.render.image_settings.file_format="FFMPEG"
scene.render.ffmpeg.format="MPEG4";scene.render.ffmpeg.codec="H264"
scene.render.ffmpeg.constant_rate_factor="HIGH"
scene.render.ffmpeg.ffmpeg_preset="GOOD"
bpy.ops.render.render(animation=True)
assert (a.out/filename).stat().st_size>15000,"missing/too-small video file"
scene.render.filepath=""
bpy.ops.file.pack_all()
native=a.out/("R014_MPFB_"+a.sex+"_textured_motion_research.blend")
bpy.ops.wm.save_as_mainfile(filepath=str(native))
assert native.stat().st_size>10_000_000
receipt={
  "status":"PASS_NATIVE_TEXTURED_MOTION_EVIDENCE_CREATED_ONLY",
  "actor":a.sex,"source_gender_macro":0.0 if a.sex=="female" else 1.0,
  "source_asset":"MPFB corrected synthetic adult lookdev with MAKESKIN eyes",
  "source_run":43207664661,"source_artifact":"r014-mpfb-eye-MAKESKIN-lookdev",
  "frame_count":end,"fps":fps,"seconds":end/fps,
  "resolution":[scene.render.resolution_x,scene.render.resolution_y],
  "source_rig_bones":len(rig.data.bones),"animated_bones":animated,
  "camera_projected_body_samples":coverage,"movie":filename,"native_scene":native.name,
  "motion_type":"ILLUSTRATIVE cyclic limb articulation and body yaw, NOT gait model",
  "quality_state":"HOLD_UNREVIEWED",
  "limitations":["Not realistic gait or foot-ground contact","No skeletal locomotion / body translation",
                 "No audited external reproductive anatomy","No soft tissue physics or FACS/lipsync",
                 "Not photoreal 4K, no independently validated rendered anatomy",
                 "Original source appearance, sex and hair are not individual identity"]
}
(a.out/"motion_receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print("R014_MPFB_MOTION",json.dumps({k:v for k,v in receipt.items() if k!="camera_projected_body_samples"},sort_keys=True))
