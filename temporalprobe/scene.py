#!/usr/bin/env python3
"""R060 original synthetic animated pose-time Cycles EXR depth and object witness.

Three fixed, source-predeclared per-frame head transforms in one actual Blender
scene. Not a bone/skin rig, learned motion, tracking or physical human animation.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"renderlab"))
sys.path.insert(0,str(ROOT/"perspprobe"))
import synthetic_scene as base
import scene as perspective

OFFSETS={0:0.0,1:0.36,2:-0.28}
HEAD_OBJECTS=(
    "head","nose","mouth","left-sclera","left-iris","left-pupil",
    "left-brow","left-ear","right-sclera","right-iris","right-pupil",
    "right-brow","right-ear"
)
def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):h.update(c)
    return h.hexdigest()

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    sc=base.make_scene("baseline")
    cam=sc.camera
    cam.data.type="PERSP"
    cam.data.sensor_fit="HORIZONTAL"
    cam.data.sensor_width=36.0
    cam.data.lens=65.0
    cam.data.shift_x=cam.data.shift_y=0.0
    bpy.context.view_layer.update()
    camera=perspective.camera_record(sc)
    source_objects={name:bpy.data.objects.get(name) for name in HEAD_OBJECTS}
    if any(v is None or v.type!="MESH" for v in source_objects.values()):
        raise RuntimeError("R060_UNRECOGNIZED_HEAD_OBJECT_SET")
    # Explicit original positions, never cumulative movement or re-created mesh.
    original={name:obj.location.copy() for name,obj in source_objects.items()}
    frames={}
    for frame,delta in sorted(OFFSETS.items()):
        sc.frame_set(frame)
        for name,obj in source_objects.items():
            obj.location=original[name].copy()
            obj.location.x+=delta
        bpy.context.view_layer.update()
        if perspective.camera_record(sc)!=camera:
            raise RuntimeError("R060_CAMERA_CHANGED_WHEN_HEAD_MOVED")
        rays,n=perspective.rays_for(sc)
        geom=base.geometry_digest()
        target=out/("frame_%02d"%frame)
        target.mkdir(parents=True,exist_ok=True)
        files={}
        for name,fmt in (("beauty.png","PNG"),("render_passes.exr","OPEN_EXR_MULTILAYER")):
            sc.render.image_settings.file_format=fmt
            sc.render.filepath=str(target/name)
            bpy.ops.render.render(write_still=True)
            path=target/name
            if not path.is_file() or path.stat().st_size<128:
                raise RuntimeError("R060_REAL_FRAME_RENDER_MISSING_"+name)
            files[name]={"sha256":sha(path),"bytes":path.stat().st_size}
        frames[str(frame)]={
            "frame_index":frame,
            "head_x_delta_source_units":delta,
            "pose_sha256":base.canonical_hash({
                name:[round(float(v),9) for row in source_objects[name].matrix_world for v in row]
                for name in sorted(source_objects)
            }),
            "geometry_sha256":geom,
            "camera_sha256":base.canonical_hash(camera),
            "stable_ray_count":n,
            "rays":rays,
            "files":files
        }
        print("R060_ACTUAL_CYCLES_FRAME",frame,n,geom,flush=True)
    if len({r["geometry_sha256"] for r in frames.values()})!=3:
        raise RuntimeError("R060_NO_ACTUAL_FRAME_GEOMETRY_CHANGE")
    manifest={
        "schema":"r060.synthetic.pose_time.v1",
        "status":"ORIGINAL_SOURCE_POSE_CAPTURE_ONLY",
        "qualification":"NOT_RIGGED_SKIN_OR_HUMAN_MOTION",
        "rights":"ORIGINAL_SYNTHETIC",
        "scene_id":base.SCENE_ID,
        "source_script_sha256":sha(ROOT/"renderlab"/"synthetic_scene.py"),
        "perspective_script_sha256":sha(ROOT/"perspprobe"/"scene.py"),
        "exr_z_convention":"CAMERA_AXIS_DEPTH_MINUS_LOCAL_Z",
        "motion_type":"CONTROLLED_MULTI_OBJECT_RIGID_HEAD_TRANSLATION_NOT_SKIN",
        "camera":camera,
        "camera_sha256":base.canonical_hash(camera),
        "head_mesh_names":sorted(HEAD_OBJECTS),
        "frames":frames,
    }
    (out/"r060_source.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("R060_REAL_THREE_FRAME_MESH_ORIGINAL_SYNTHETIC_CAPTURED",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    run(args.out)
