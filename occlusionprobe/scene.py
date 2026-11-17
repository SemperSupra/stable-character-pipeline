#!/usr/bin/env python3
"""R075 original synthetic actual Cycles occlusion falsifiers for EXR object-ID.

No actual human, consented source, inferred real identity, pose tracking or
optical-flow claim. A known head ID can disappear under a foreground object.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"renderlab"),str(ROOT/"perspprobe")]
import synthetic_scene as base
import importlib.util
spec=importlib.util.spec_from_file_location("r075_perspective",ROOT/"perspprobe"/"scene.py")
perspective=importlib.util.module_from_spec(spec)
spec.loader.exec_module(perspective)

HEAD_NAMES=(
    "head","nose","mouth","left-sclera","left-iris","left-pupil",
    "left-brow","left-ear","right-sclera","right-iris","right-pupil",
    "right-brow","right-ear")
CASES=("clear","partial","severe")
HEAD_INDEX=3
OCCLUDER_INDEX=4
GEOM_PARAMS={
    "clear":{"width":0.08,"height":0.08,"offset_x":100.0,"offset_y":0.0},
    "partial":{"width":0.56,"height":0.78,"offset_x":0.18,"offset_y":0.11},
    "severe":{"width":2.4,"height":2.3,"offset_x":0.0,"offset_y":0.0},
}

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    scene=base.make_scene("baseline")
    cam=scene.camera
    cam.data.type="PERSP"
    cam.data.sensor_fit="HORIZONTAL"
    cam.data.sensor_width=36.0
    cam.data.lens=65.0
    cam.data.shift_x=cam.data.shift_y=0.0
    bpy.context.view_layer.update()
    camera=perspective.camera_record(scene)
    originals={name:bpy.data.objects.get(name) for name in HEAD_NAMES}
    if any(obj is None or obj.type!="MESH" or obj.pass_index!=1 for obj in originals.values()):
        raise RuntimeError("R075_ORIGINAL_SOURCE_HEAD_MISSING")
    for obj in originals.values():
        obj.pass_index=HEAD_INDEX
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    occ=bpy.context.object
    occ.name="r075-original-foreground-occluder"
    occ.pass_index=OCCLUDER_INDEX
    occ.data.materials.append(base.material("r075-source-occluder",(0.06,0.055,0.21),"baseline"))
    occ.rotation_euler=cam.rotation_euler.copy()
    center=cam.matrix_world.inverted() @ originals["head"].matrix_world.translation
    # Place a camera-facing solid in 3-D at 65% of target depth. Its scale/offset
    # is fixed BEFORE rendering, never fitted to the decoded image.
    place=Vector((center.x*0.65,center.y*0.65,center.z*0.65))
    frames={}
    for idx,case in enumerate(CASES):
        scene.frame_set(idx)
        p=GEOM_PARAMS[case]
        occ.scale=(p["width"],p["height"],0.08)
        local=place+Vector((p["offset_x"],p["offset_y"],0.0))
        occ.location=cam.matrix_world @ local
        bpy.context.view_layer.update()
        if perspective.camera_record(scene)!=camera:
            raise RuntimeError("R075_UNCONTROLLED_CAMERA")
        rays,stable=perspective.rays_for(scene)
        n_head=sum(r["stable"] and r["pass_index"]==HEAD_INDEX for r in rays)
        n_occ=sum(r["stable"] and r["pass_index"]==OCCLUDER_INDEX for r in rays)
        if stable<64:
            raise RuntimeError("R075_NOT_ENOUGH_TOTAL_SOURCE_RAYS")
        if case=="clear" and n_head<8:
            raise RuntimeError("R075_NO_UNOCCLUDED_SOURCE_HEAD")
        if case!="clear" and n_occ<2:
            raise RuntimeError("R075_OCCLUDER_NOT_IN_NATIVE_SOURCE_VIEW")
        directory=out/case
        directory.mkdir(parents=True,exist_ok=True)
        files={}
        for filename,fmt in (("beauty.png","PNG"),("render_passes.exr","OPEN_EXR_MULTILAYER")):
            scene.render.image_settings.file_format=fmt
            scene.render.filepath=str(directory/filename)
            bpy.ops.render.render(write_still=True)
            path=directory/filename
            if not path.is_file() or path.stat().st_size<=128:
                raise RuntimeError("R075_ACTUAL_CYCLES_IMAGE_MISSING")
            files[filename]={"sha256":sha(path),"bytes":path.stat().st_size}
        frames[case]={
            "frame_index":idx,
            "case":case,
            "source_occluder_geometry":p,
            "source_occluder_id":OCCLUDER_INDEX,
            "source_head_id":HEAD_INDEX,
            "camera_sha256":base.canonical_hash(camera),
            "source_geometry_sha256":base.geometry_digest(),
            "stable_rays":stable,
            "head_source_rays":n_head,
            "occluder_source_rays":n_occ,
            "rays":rays,
            "files":files,
        }
        print("R075_REAL_OCCLUDER_FRAME",case,stable,n_head,n_occ,flush=True)
    if len({x["source_geometry_sha256"] for x in frames.values()})!=3:
        raise RuntimeError("R075_SOURCE_OCCLUDER_UNCHANGED")
    report={
        "schema":"r075.original.synthetic.real-occlusion.v1",
        "status":"ACTUAL_SOURCE_OCCLUSION_PENDING_INDEPENDENT_EXR",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_REAL_PERSON_IDENTITY_OR_OCCLUSION_TRACKING",
        "source_scene_id":base.SCENE_ID,
        "source_script_sha256":sha(ROOT/"renderlab"/"synthetic_scene.py"),
        "perspective_script_sha256":sha(ROOT/"perspprobe"/"scene.py"),
        "camera":camera,
        "camera_sha256":base.canonical_hash(camera),
        "source_semantic_head_names":sorted(HEAD_NAMES),
        "source_semantic_head_id":HEAD_INDEX,
        "source_occluder_id":OCCLUDER_INDEX,
        "source_motion_type":"KNOWN_STATIONARY_HEAD_MOVING_FOREGROUND_OCCLUDER",
        "cases":frames,
    }
    (out/"r075_source.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("R075_REAL_CYCLES_OCCLUSION_SOURCE_CAPTURED",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    run(args.out)
