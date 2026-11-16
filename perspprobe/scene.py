#!/usr/bin/env python3
"""R057 real Cycles perspective-camera Z/object-ID evidence, original synthetic.
No private character, source asset, downloaded model, generated identity or owner.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderlab"))
import synthetic_scene as base

RES=base.RESOLUTION
LENSES=(35.0,65.0)

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def camera_record(scene):
    cam=scene.camera
    if cam.data.type!="PERSP":
        raise RuntimeError("R057_CAMERA_NOT_PERSPECTIVE")
    return {
        "type":"PERSP",
        "lens_mm":float(cam.data.lens),
        "sensor_width_mm":float(cam.data.sensor_width),
        "sensor_fit":str(cam.data.sensor_fit),
        "shift_x":float(cam.data.shift_x),
        "shift_y":float(cam.data.shift_y),
        "clip_start":float(cam.data.clip_start),
        "clip_end":float(cam.data.clip_end),
        "world_matrix":[round(float(v),9) for row in cam.matrix_world for v in row],
        "resolution":[int(scene.render.resolution_x),int(scene.render.resolution_y)],
        "pixel_aspect":[float(scene.render.pixel_aspect_x),float(scene.render.pixel_aspect_y)]
    }

def ray_at_pixel(scene,px,py):
    cam=scene.camera
    # Blender's actual calibrated frame at this resolution/lens/sensor/shift
    # rather than an independently guessed 36mm/sensor model.
    corners=cam.data.view_frame(scene=scene)
    min_x=min(float(v.x) for v in corners)
    max_x=max(float(v.x) for v in corners)
    min_y=min(float(v.y) for v in corners)
    max_y=max(float(v.y) for v in corners)
    zs=[float(v.z) for v in corners]
    if max(zs)-min(zs)>1e-8 or zs[0]>=0:
        raise RuntimeError("R057_UNEXPECTED_NATIVE_FRAME")
    x=min_x+(px+.5)/RES*(max_x-min_x)
    y=max_y-(py+.5)/RES*(max_y-min_y)
    local_direction=Vector((x,y,zs[0])).normalized()
    cam.update_tag(refresh={'OBJECT'})
    world_direction=(cam.matrix_world.to_quaternion() @ local_direction).normalized()
    return cam.matrix_world.translation.copy(),world_direction

def intersect(scene,dg,px,py):
    origin,direction=ray_at_pixel(scene,px,py)
    hit,point,normal,face,obj,_=scene.ray_cast(dg,origin,direction,distance=80.0)
    if not hit or obj is None:return None
    distance=float((point-origin).dot(direction))
    # Perspective Cycles ViewLayer Z is linear camera-space axial distance
    # (-camera-local Z), not Euclidean camera-to-hit ray length.
    # Retain BOTH independent measurements to prevent mode confusion.
    local_hit=scene.camera.matrix_world.inverted() @ point
    axis_depth=-float(local_hit.z)
    if distance<=0 or distance>=80 or axis_depth<=0 or axis_depth>distance+1e-4:
        raise RuntimeError("R057_BAD_CAMERA_RAY_OR_AXIS_DISTANCE")
    return {
        "pass_index":int(obj.pass_index),
        "ray_distance":round(distance,9),
        "camera_axis_depth":round(axis_depth,9),
        "geometric_normal":[round(float(z),9) for z in normal.normalized()],
        "object_name":obj.name
    }

def rays_for(scene):
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    records=[]
    for py in range(8,RES,16):
        for px in range(8,RES,16):
            center=intersect(scene,dg,px,py)
            if center is None:continue
            near=[intersect(scene,dg,px+dx,py+dy)
                  for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))]
            stable=all(q is not None and
                       q["pass_index"]==center["pass_index"] and
                       q["object_name"]==center["object_name"] and
                       abs(q["camera_axis_depth"]-center["camera_axis_depth"])<1.0
                       for q in near)
            records.append({"x":px,"y":py,"stable":stable,**center})
    num=sum(bool(r["stable"]) for r in records)
    if num<64:
        raise RuntimeError("R057_TOO_FEW_NATIVE_STABLE_RAYS:"+str(num))
    return records,num

def render_pair(out):
    out.mkdir(parents=True,exist_ok=True)
    scene=base.make_scene("baseline")
    cam=scene.camera
    cam.data.type="PERSP"
    cam.data.sensor_fit="HORIZONTAL"
    cam.data.sensor_width=36.0
    cam.data.shift_x=0.0
    cam.data.shift_y=0.0
    bpy.context.view_layer.update()

    original_geometry=base.geometry_digest()
    original_script_sha=sha(ROOT/"renderlab"/"synthetic_scene.py")
    per_lens={}
    for lens in LENSES:
        cam.data.lens=lens
        bpy.context.view_layer.update()
        camera=camera_record(scene)
        ray_sample,n=rays_for(scene)
        lens_id="lens_%02d"%int(lens)
        per_lens[lens_id]={
            "camera":camera,
            "camera_sha256":base.canonical_hash(camera),
            "source_geometry_sha256":original_geometry,
            "ray_sample_count":len(ray_sample),
            "stable_count":n,
            "rays":ray_sample,
            "arms":{}
        }

    for arm in ("baseline","physical_material"):
        if arm=="physical_material":
            base.apply_material_treatment()
            if base.geometry_digest()!=original_geometry:
                raise RuntimeError("R057_MATERIAL_CHANGED_GEOMETRY")
        for lens in LENSES:
            lens_id="lens_%02d"%int(lens)
            cam.data.lens=lens
            bpy.context.view_layer.update()
            if base.geometry_digest()!=original_geometry:
                raise RuntimeError("R057_LENS_CHANGED_GEOMETRY")
            camera=camera_record(scene)
            if base.canonical_hash(camera)!=per_lens[lens_id]["camera_sha256"]:
                raise RuntimeError("R057_UNCONTROLLED_CAMERA_DRIFT")
            target=out/lens_id/arm
            target.mkdir(parents=True,exist_ok=True)
            files={}
            for name,fmt in (("beauty.png","PNG"),("render_passes.exr","OPEN_EXR_MULTILAYER")):
                scene.render.image_settings.file_format=fmt
                scene.render.filepath=str(target/name)
                bpy.ops.render.render(write_still=True)
                file=target/name
                if not file.is_file() or file.stat().st_size<128:
                    raise RuntimeError("R057_MISSING_RENDER_"+name)
                files[name]={"sha256":sha(file),"bytes":file.stat().st_size}
            per_lens[lens_id]["arms"][arm]=files
            print("R057_PERSPECTIVE_ACTUAL_CYCLES_RENDER",lens_id,arm,
                  per_lens[lens_id]["camera_sha256"],flush=True)

    report={
        "schema":"r057.perspective.native.v1",
        "status":"PERSPECTIVE_SOURCE_RAY_CAPTURED_PENDING_EXR_CRITIC",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_PHOTOREALISM_OR_PRIVATE_HUMAN_EVIDENCE",
        "source_scene_id":base.SCENE_ID,
        "source_script_sha256":original_script_sha,
        "exr_z_interpretation":"PERSPECTIVE_CAMERA_AXIS_MINUS_LOCAL_Z",
        "native_ray_metric":"EUCLIDEAN_CAMERA_TO_HIT_RAY_LENGTH",
        "geometry_sha256":original_geometry,
        "resolution":RES,
        "lenses":per_lens
    }
    (out/"r057_source_manifest.json").write_text(
        json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("R057_PERSPECTIVE_REAL_SOURCE_CAPTURED",len(per_lens),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    args=p.parse_args(argv)
    render_pair(args.out)
