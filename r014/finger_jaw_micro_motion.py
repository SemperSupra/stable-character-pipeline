"""Actual source-rig MPFB hand curl and jaw/gaze motion, research proof only.

No new FACS controls. Explicit source silhouette, rig bone and animated mesh
checks; footage is a visual test, not anatomically validated expressivity.
"""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

p=argparse.ArgumentParser()
p.add_argument("--sex",choices=("female","male"),required=True)
p.add_argument("--motion-source",type=Path,required=True)
p.add_argument("--source-receipt",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.motion_source.resolve()
a.out.mkdir(parents=True,exist_ok=True)
source=json.loads(a.source_receipt.read_text())
assert source["actor"]==a.sex and source["source_gender_macro"]=={"female":0.0,"male":1.0}[a.sex]
rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
assert len(rig.data.bones)==163 and len(body.data.vertices)==19158

scene=bpy.context.scene
scene.render.engine="CYCLES"
scene.cycles.device="CPU";scene.cycles.samples=6
scene.render.threads_mode="FIXED";scene.render.threads=4
scene.render.resolution_x=512;scene.render.resolution_y=512
scene.render.resolution_percentage=100
scene.render.image_settings.color_mode="RGB"
scene.frame_start=1;scene.frame_end=36;scene.render.fps=24

# New camera is dynamic but both storyboard shots start at actual rig bones.
cam_data=bpy.data.cameras.new("R014ControlledCloseup")
cam=bpy.data.objects.new("R014ControlledCloseup",cam_data)
bpy.context.collection.objects.link(cam)
cam_data.type="ORTHO";scene.camera=cam
light_data=bpy.data.lights.new("R014ControlledSoftbox","AREA")
lamp=bpy.data.objects.new("R014ControlledSoftbox",light_data)
bpy.context.collection.objects.link(lamp)
light_data.energy=220;light_data.size=1.6

FINGER_NAMES=["finger"+str(i)+"-"+str(segment)+".L"
              for i in range(1,6) for segment in range(1,4)]
FACE_NAMES=["jaw","eye.L","eye.R"]
assert all(n in rig.pose.bones for n in FINGER_NAMES+FACE_NAMES)
def reset_pose():
    rig.animation_data_clear()
    for bone in rig.pose.bones:
        bone.rotation_mode="XYZ"
        bone.rotation_euler=(0,0,0)
        bone.location=(0,0,0)
        bone.scale=(1,1,1)
    scene.frame_set(1)
    bpy.context.view_layer.update()

def target_vertices(names):
    refs=[body.vertex_groups.get(n) for n in names]
    gids={g.index for g in refs if g is not None}
    ids=[v.index for v in body.data.vertices
         if any(g.group in gids and g.weight>.02 for g in v.groups)]
    return ids

def world_points(indices):
    dg=bpy.context.evaluated_depsgraph_get()
    ev=body.evaluated_get(dg)
    mesh=ev.to_mesh()
    try:return {i:ev.matrix_world@mesh.vertices[i].co for i in indices}
    finally:ev.to_mesh_clear()

results=[]
for shot in ("hand","jaw_gaze"):
    reset_pose()
    driven=FINGER_NAMES if shot=="hand" else FACE_NAMES
    origin_bone="finger2-1.L" if shot=="hand" else "jaw"
    bone=rig.pose.bones[origin_bone]
    target=rig.matrix_world@bone.head
    # Front oblique finger closeup or face closeup, not whole-body camera.
    cam.location=target+Vector((.08,-.7,.09 if shot=="hand" else .17))
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    cam_data.ortho_scale=.44 if shot=="hand" else .68
    lamp.location=target+Vector((.3,-.6,.65))
    bpy.context.view_layer.update()
    projected=world_to_camera_view(scene,cam,target)
    assert .2<projected.x<.8 and .2<projected.y<.8 and projected.z>0
    # Unanimated starting pose is neutral, then deliberate mid-cycle motion.
    frames=range(1,37)
    for f in frames:
        amplitude=math.sin(math.pi*(f-1)/35)
        if shot=="hand":
            for name in driven:
                pb=rig.pose.bones[name]
                # Conservative local-axis curl (0..0.33rad), only one hand.
                pb.rotation_euler.x=(.33 if "-1." in name else .20)*amplitude
                pb.keyframe_insert(data_path="rotation_euler",frame=f)
        else:
            rig.pose.bones["jaw"].rotation_euler.x=.13*amplitude
            rig.pose.bones["eye.L"].rotation_euler.z=.06*amplitude
            rig.pose.bones["eye.R"].rotation_euler.z=.06*amplitude
            for name in driven:
                rig.pose.bones[name].keyframe_insert(data_path="rotation_euler",frame=f)
    indices=target_vertices(driven)
    # A bone-action log alone is insufficient; prove that skinned mesh actually moved.
    assert len(indices)>10,("no skin geometry driven by target bones",shot,len(indices))
    scene.frame_set(1);bpy.context.view_layer.update()
    first=world_points(indices)
    scene.frame_set(18);bpy.context.view_layer.update()
    changed=world_points(indices)
    deltas=sorted((first[i]-changed[i]).length for i in indices)
    max_delta=deltas[-1]
    p95=deltas[min(len(deltas)-1,int(.95*len(deltas)))]
    assert .0003<max_delta<.15,("closeup target not visibly deforming or excessive",shot,max_delta)
    scene.frame_set(1);bpy.context.view_layer.update()
    filename="R014_"+a.sex+"_"+shot+"_native_micro_motion_1p5s.mp4"
    scene.render.filepath=str(a.out/filename)
    scene.render.image_settings.file_format="FFMPEG"
    scene.render.ffmpeg.format="MPEG4"
    scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.ffmpeg_preset="GOOD"
    scene.render.ffmpeg.constant_rate_factor="HIGH"
    bpy.ops.render.render(animation=True)
    assert (a.out/filename).stat().st_size>9000
    scene.render.filepath=""
    bpy.ops.file.pack_all()
    native=a.out/("R014_"+a.sex+"_"+shot+"_native_micro_research.blend")
    bpy.ops.wm.save_as_mainfile(filepath=str(native))
    assert native.stat().st_size>10_000_000
    result={"shot":shot,"motion_source":source["movie"],"sex":a.sex,
            "source_gender_macro":source["source_gender_macro"],
            "driven_bones":driven,"affected_body_vertices":len(indices),
            "max_skin_vertex_displacement_m":max_delta,
            "p95_skin_vertex_displacement_m":p95,
            "frames":36,"fps":24,"resolution":[512,512],
            "video":filename,"editable_blend":native.name,
            "source_mpfb_body_vertices":len(body.data.vertices),
            "quality":"RESEARCH_MOTION_ONLY_NOT_VQA_ACCEPTED"}
    results.append(result)
    print("R014_MICRO_MOTION",json.dumps(result,sort_keys=True),flush=True)
(a.out/"micro_motion_receipt.json").write_text(json.dumps({
 "status":"PASS_BONE_DRIVEN_REAL_SKIN_MOTION_ONLY",
 "actor":a.sex,"recorded":results,
 "holds":["Facial rig lacks independent lip/brow/cheek FACS controls",
          "Eye/jaw movement is not natural speech synchronization",
          "Finger curl is not grasp contact or physically correct tendon action",
          "Not high-resolution sculpt or 4K quality",
          "No independent human visual pass, no full genital anatomy qualification"]
},indent=2,sort_keys=True)+"\n")
