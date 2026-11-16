#!/usr/bin/env python3
"""R045: source-known Blender mesh ray hits vs INDEPENDENT Cycles depth/ID pixels.
Only original R037 stylized geometry, not real human or photorealism claim.
This program does not edit upstream R044 or acquire any external assets.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"lightingprobe"))
sys.path.insert(0,str(ROOT/"renderlab"))
import stress
import synthetic_scene

STRIDE=16
SIDE=256

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cast_pixel(scene, camera, dg, px, py):
    """Pixel center in ortho camera plane. Blender camera local -Z is forward."""
    width=camera.data.ortho_scale
    height=camera.data.ortho_scale
    x=((px+0.5)/SIDE-0.5)*width
    y=(0.5-(py+0.5)/SIDE)*height
    origin=camera.matrix_world @ Vector((x,y,0.0))
    direction=(camera.matrix_world.to_quaternion() @ Vector((0,0,-1))).normalized()
    hit,point,normal,face,obj,_=scene.ray_cast(dg,origin,direction,distance=80.0)
    if not hit or obj is None:return None
    linear=float((point-origin).dot(direction))
    if not 0 < linear < 80.0:raise RuntimeError("nonsensical ray hit")
    return {
        "pass_index":int(obj.pass_index),
        "depth_from_camera_plane":round(linear,8),
        "geometric_normal": [round(float(v),8) for v in normal.normalized()],
        "object_name":obj.name
    }

def capture(out):
    out.mkdir(parents=True,exist_ok=True)
    # R044 renders all 4 intervention arms from ONE scene, without a rebuild.
    stress.run(out)
    scene=bpy.context.scene
    cam=scene.camera
    if cam is None or cam.data.type!="ORTHO":raise RuntimeError("expected orthographic test fixture")
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    geometry=synthetic_scene.geometry_digest()
    cam_hash=synthetic_scene.canonical_hash({
        "matrix":[round(float(v),7) for row in cam.matrix_world for v in row],
        "projection":"ORTHO","scale":cam.data.ortho_scale,
        "resolution":synthetic_scene.RESOLUTION
    })
    records=[]
    for py in range(STRIDE//2,SIDE,STRIDE):
        for px in range(STRIDE//2,SIDE,STRIDE):
            center=cast_pixel(scene,cam,dg,px,py)
            if center is None:continue
            neighbors=[cast_pixel(scene,cam,dg,px+dx,py+dy)
                       for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))]
            stable=all(q is not None and q["pass_index"]==center["pass_index"]
                       and abs(q["depth_from_camera_plane"]-center["depth_from_camera_plane"])<0.03
                       for q in neighbors)
            records.append({"x":px,"y":py,"stable":bool(stable),**center})
    count=sum(r["stable"] for r in records)
    if count<64:raise RuntimeError("insufficient source-stable ray samples")
    report={
        "schema":"r045.ortho.raycast.v1",
        "status":"ORIGINAL_SCENE_RAYCAST_CAPTURE_ONLY",
        "qualification":"NOT_INDEPENDENT_RENDER_PASS_VALIDATION_YET",
        "rights":"ORIGINAL_SYNTHETIC",
        "scene_id":synthetic_scene.SCENE_ID,
        "source_geometry_sha256":geometry,
        "source_camera_sha256":cam_hash,
        "synthetic_scene_script_sha256":digest(ROOT/"renderlab"/"synthetic_scene.py"),
        "lighting_manifest_sha256":digest(out/"lighting_manifest.json"),
        "camera_type":"ORTHO",
        "depth_hypothesis":"camera-plane-forward-ray-parameter-meters-in-uncalibrated-scene-units",
        "pixel_convention":"top-left pixel centers, 256x256",
        "sample_stride":STRIDE,
        "stable_samples":count,
        "rays":records
    }
    (out/"raycast_oracle.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("R045_NATIVE_MESH_RAYCAST_CAPTURED",len(records),count,geometry,cam_hash)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    a=p.parse_args(argv)
    capture(a.out)
