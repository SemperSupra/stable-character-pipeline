#!/usr/bin/env python3
"""R059 original synthetic real Cycles EXR surface normal semantics.
Only source original procedural bust. No real person or donor files.
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

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main(out):
    out.mkdir(parents=True,exist_ok=True)
    sc=base.make_scene("baseline")
    cam=sc.camera
    cam.data.type="PERSP"
    cam.data.sensor_fit="HORIZONTAL"
    cam.data.sensor_width=36.0
    cam.data.lens=65.0
    cam.data.shift_x=cam.data.shift_y=0.0
    bpy.context.view_layer.update()
    geom=base.geometry_digest()
    camera=perspective.camera_record(sc)
    ray_samples,stable=perspective.rays_for(sc)
    if stable<64:
        raise RuntimeError("R059_INSUFFICIENT_NATIVE_GEOMETRY_NORMALS")
    cases={}
    for arm in ("baseline","physical_material"):
        if arm=="physical_material":base.apply_material_treatment()
        if base.geometry_digest()!=geom or perspective.camera_record(sc)!=camera:
            raise RuntimeError("R059_UNCONTROLLED_GEOMETRY_OR_CAMERA")
        directory=out/arm
        directory.mkdir(parents=True,exist_ok=True)
        files={}
        for filename,fmt in (("beauty.png","PNG"),("render_passes.exr","OPEN_EXR_MULTILAYER")):
            sc.render.image_settings.file_format=fmt
            sc.render.filepath=str(directory/filename)
            bpy.ops.render.render(write_still=True)
            path=directory/filename
            if not path.is_file() or path.stat().st_size<128:
                raise RuntimeError("R059_REAL_CYCLES_RENDER_MISSING")
            files[filename]={"bytes":path.stat().st_size,"sha256":digest(path)}
        cases[arm]=files
    manifest={
        "schema":"r059.original.synthetic.shading_normals.v1",
        "status":"NATIVE_GEOMETRY_CAPTURE_PENDING_INDEPENDENT_EXR",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_HUMAN_PHYSICS_OR_ANATOMY",
        "source_script_sha256":digest(ROOT/"renderlab"/"synthetic_scene.py"),
        "perspective_script_sha256":digest(ROOT/"perspprobe"/"scene.py"),
        "scene_id":base.SCENE_ID,
        "geometry_sha256":geom,
        "camera":camera,
        "camera_sha256":base.canonical_hash(camera),
        "source_stable_samples":stable,
        "source_rays":ray_samples,
        "arms":cases,
    }
    (out/"r059_source.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print("R059_TRUE_CYCLES_NORMAL_PASS_IMAGES_CAPTURED",stable,geom,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    main(args.out)
