#!/usr/bin/env python3
"""R073 genuine Cycles EXR object-index tracking of original source-known parts.

Free public original synthetic geometry only, no protected character identity.
Rigid source head proxy motion is NOT actual skeleton/skin/optical flow/gait.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"renderlab"))
sys.path.insert(0,str(ROOT/"perspprobe"))
import synthetic_scene as base
import scene as perspective

HEAD_NAMES=(
    "head","nose","mouth","left-sclera","left-iris","left-pupil",
    "left-brow","left-ear","right-sclera","right-iris","right-pupil",
    "right-brow","right-ear"
)
OFFSETS={0:0.0,1:0.36,2:-0.28}
HEAD_INDEX=3

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def projected_center(scene,mesh):
    point=mesh.matrix_world.translation
    norm=world_to_camera_view(scene,scene.camera,point)
    if float(norm.z)<=0:
        raise RuntimeError("R073_HEAD_CENTER_BEHIND_CAMERA")
    return [round(float(norm.x*base.RESOLUTION),9),
            round(float((1.0-norm.y)*base.RESOLUTION),9)]

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    scene=base.make_scene("baseline")
    camera=scene.camera
    camera.data.type="PERSP"
    camera.data.sensor_fit="HORIZONTAL"
    camera.data.sensor_width=36.0
    camera.data.lens=65.0
    camera.data.shift_x=camera.data.shift_y=0.0
    bpy.context.view_layer.update()
    fixed_camera=perspective.camera_record(scene)
    objects={name:bpy.data.objects.get(name) for name in HEAD_NAMES}
    if any(obj is None or obj.type!="MESH" or obj.pass_index!=1 for obj in objects.values()):
        raise RuntimeError("R073_UNRECOGNIZED_ORIGINAL_HEAD_SOURCE")
    original={name:ob.location.copy() for name,ob in objects.items()}
    # Object IDs are DIFFERENT from the torso and ground, making a real decoded
    # full-resolution visual segmentation witness possible.
    for obj in objects.values():
        obj.pass_index=HEAD_INDEX
    bpy.context.view_layer.update()
    frames={}
    for idx,delta in sorted(OFFSETS.items()):
        scene.frame_set(idx)
        for name,obj in objects.items():
            obj.location=original[name].copy()
            obj.location.x+=delta
        bpy.context.view_layer.update()
        if perspective.camera_record(scene)!=fixed_camera:
            raise RuntimeError("R073_CAMERA_MOVED_DURING_OBJECT_ID_TRACKING")
        rays,num=perspective.rays_for(scene)
        source_3=sum(r["stable"] and r["pass_index"]==HEAD_INDEX for r in rays)
        if source_3<8:
            raise RuntimeError("R073_INSUFFICIENT_SOURCE_HEAD_RAYS")
        target=out/("frame_%02d"%idx)
        target.mkdir(parents=True,exist_ok=True)
        files={}
        for filename,fmt in (("beauty.png","PNG"),("render_passes.exr","OPEN_EXR_MULTILAYER")):
            scene.render.image_settings.file_format=fmt
            scene.render.filepath=str(target/filename)
            bpy.ops.render.render(write_still=True)
            path=target/filename
            if not path.exists() or path.stat().st_size<128:
                raise RuntimeError("R073_MISSING_REAL_CYCLES_IMAGE")
            files[filename]={"sha256":sha(path),"bytes":path.stat().st_size}
        frames[str(idx)]={
            "frame_index":idx,"source_head_x_delta":delta,
            "source_geometry_sha256":base.geometry_digest(),
            "camera_sha256":base.canonical_hash(fixed_camera),
            "head_center_projection_px":projected_center(scene,objects["head"]),
            "head_mesh_pass_index":HEAD_INDEX,
            "source_stable_rays":num,
            "source_stable_head_rays":source_3,
            "source_rays":rays,
            "files":files
        }
        print("R073_REAL_SEMANTIC_HEAD_RENDER",idx,
              "stable_head",source_3,
              "head_projected",frames[str(idx)]["head_center_projection_px"],
              flush=True)
    if len({f["source_geometry_sha256"] for f in frames.values()})!=3:
        raise RuntimeError("R073_SOURCE_GEOMETRY_NOT_TRANSLATED")
    manifest={
      "schema":"r073.original.synthetic.exr.object-track.v1",
      "status":"SOURCE_TRACKING_CAPTURE_PENDING_INDEPENDENT_IMAGE",
      "rights":"ORIGINAL_SYNTHETIC",
      "qualification":"NOT_REAL_IDENTITY_OPTICAL_FLOW_OR_MAKEHUMAN",
      "scene_id":base.SCENE_ID,
      "original_source_script_sha256":sha(ROOT/"renderlab"/"synthetic_scene.py"),
      "perspective_script_sha256":sha(ROOT/"perspprobe"/"scene.py"),
      "camera":fixed_camera,
      "camera_sha256":base.canonical_hash(fixed_camera),
      "source_semantic_object_names":list(sorted(HEAD_NAMES)),
      "source_semantic_object_index":HEAD_INDEX,
      "source_motion_type":"RIGID_HEAD_TRANSLATION_WITH_SEMANTIC_EXR_ID",
      "frames":frames
    }
    (out/"r073_source.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("R073_THREE_REAL_MOVING_SEGMENTATION_SOURCE_CAPTURED",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    run(args.out)
