#!/usr/bin/env python3
"""R074 original synthetic native Blender Armature fcurve subframes + Cycles.

An actual keyframed 2-bone weighted sleeve, not a real person, gait, IK, MMD,
MakeHuman, skin material physics or third-party source.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"skinprobe"),str(ROOT/"perspprobe"),str(ROOT/"renderlab")]
import scene as skin_scene
import synthetic_scene as base
# Explicitly import the R057 perspective source by path without shadowing
import importlib.util
spec=importlib.util.spec_from_file_location("r074_perspective",ROOT/"perspprobe"/"scene.py")
perspective=importlib.util.module_from_spec(spec)
spec.loader.exec_module(perspective)

KEYS={0:0.0,1:0.34,2:-0.29}
TIMES=(0.0,0.5,1.0,1.5,2.0)
EXPECTED={0.0:0.0,0.5:0.17,1.0:0.34,1.5:0.025,2.0:-0.29}

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    sc=base.make_scene("baseline")
    camera=sc.camera
    camera.data.type="PERSP"
    camera.data.sensor_fit="HORIZONTAL"
    camera.data.sensor_width=36.0
    camera.data.lens=65.0
    camera.data.shift_x=camera.data.shift_y=0.0
    sc.frame_set(0)
    bpy.context.view_layer.update()
    source_camera=perspective.camera_record(sc)
    obj,arm,source=skin_scene.construct_rig(sc)
    pose=arm.pose.bones["tip"]
    pose.rotation_mode="XYZ"
    for frame,angle in KEYS.items():
        pose.rotation_euler[0]=angle
        pose.keyframe_insert(data_path="rotation_euler",index=0,frame=frame)
    if arm.animation_data is None or arm.animation_data.action is None:
        raise RuntimeError("R074_ACTUAL_BLENDER_ANIMATION_ACTION_MISSING")
    curves=[fc for fc in arm.animation_data.action.fcurves
            if fc.data_path.endswith('"tip"].rotation_euler') and fc.array_index==0]
    if len(curves)!=1 or len(curves[0].keyframe_points)!=3:
        raise RuntimeError("R074_KEYED_FCURVE_NOT_CREATED")
    for point in curves[0].keyframe_points:
        point.interpolation="LINEAR"
    bpy.context.view_layer.update()
    samples={}
    for t in TIMES:
        frame=int(t)
        sc.frame_set(frame,subframe=t-frame)
        bpy.context.view_layer.update()
        observed=float(pose.rotation_euler[0])
        if abs(observed-EXPECTED[t])>1e-5:
            raise RuntimeError("R074_NATIVE_FCURVE_SUBFRAME_WRONG:"+repr((t,observed)))
        if perspective.camera_record(sc)!=source_camera:
            raise RuntimeError("R074_UNCONTROLLED_CAMERA")
        v,faces,bone_transform=skin_scene.evaluated_mesh_and_bones(obj,arm)
        if faces!=source["faces"]:
            raise RuntimeError("R074_SKIN_TOPOLOGY_DRIFT")
        rays,stable=perspective.rays_for(sc)
        rig_stable=sum(x["stable"] and x["pass_index"]==3 for x in rays)
        if rig_stable<2:raise RuntimeError("R074_RIG_NOT_VISIBLE")
        name="t%03d"%int(t*100)
        directory=out/name
        directory.mkdir(parents=True,exist_ok=True)
        files={}
        for filename,fmt in (("beauty.png","PNG"),("render_passes.exr","OPEN_EXR_MULTILAYER")):
            sc.render.image_settings.file_format=fmt
            sc.render.filepath=str(directory/filename)
            bpy.ops.render.render(write_still=True)
            f=directory/filename
            if not f.is_file() or f.stat().st_size<128:
                raise RuntimeError("R074_ACTUAL_RENDER_MISSING")
            files[filename]={"sha256":sha(f),"bytes":f.stat().st_size}
        samples[name]={
            "time_frames":t,
            "source_expected_linear_angle_x":EXPECTED[t],
            "actual_fcurve_angle_x":round(observed,9),
            "evaluated_vertices":v,
            "faces_sha256":base.canonical_hash(faces),
            "evaluated_mesh_sha256":base.canonical_hash({"vertices":v,"faces":faces}),
            "armature_pose_matrices":bone_transform,
            "stable_ray_count":stable,
            "rig_stable_ray_count":rig_stable,
            "rays":rays,
            "files":files,
        }
        print("R074_REAL_NATIVE_SUBFRAME",t,observed,rig_stable,flush=True)
    report={
        "schema":"r074.original.synthetic.native-subframes.v1",
        "status":"ACTUAL_BLENDER_FCURVE_SUBFRAMES_PENDING_EXR_LBS_AUDIT",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_PERSON_SKIN_OR_MMD_RETARGET",
        "source_scene_id":base.SCENE_ID,
        "source_original_sha256":sha(ROOT/"renderlab"/"synthetic_scene.py"),
        "source_skin_sha256":sha(ROOT/"skinprobe"/"scene.py"),
        "source_camera_sha256":sha(ROOT/"perspprobe"/"scene.py"),
        "camera":source_camera,
        "camera_sha256":base.canonical_hash(source_camera),
        "timebase":"BLENDER_SCENE_FRAMES_WITH_EXPLICIT_SUBFRAME",
        "interpolation":"ACTUAL_BLENDER_FCURVE_LINEAR",
        "keys":[[frame,angle] for frame,angle in KEYS.items()],
        "source":source,
        "samples":samples,
    }
    (out/"r074_source.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("R074_REAL_KEYED_BLENDER_SKIN_EXR_SOURCE_CAPTURED",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    args=p.parse_args(argv)
    run(args.out)

