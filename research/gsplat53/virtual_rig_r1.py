#!/usr/bin/env python3
"""Native mesh authority vs source-derived Gaussian surface render R1.

Actual Blender 5.3/Cycles CPU renders of exactly the same deterministic
two-link rigid animation, camera and repaint edit in two representations.
Original synthetic object, not a human, learned reconstruction or equal
quality/photorealism comparison.
"""
import hashlib
import itertools
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

from rig_fixture import (LENGTH, WIDTH, HEIGHT, PAINTS, POSES,
                         colors, center, ground_truth, ply_bytes, vertices)

ROOT=Path(os.environ.get("BAKEOFF_OUT","out/gsplat53-r1")).resolve()
ROOT.mkdir(parents=True,exist_ok=True)
RES=96
VIEWS={
 "front":((0.0,-4.0,0.65),(0.0,0.0,-0.08)),
 "oblique_holdout":((1.85,-3.0,1.2),(0.0,0.0,-0.08)),
}
REPS=("mesh","splat")
SCHEMA="native-authority-vs-splat-r1/v1"

def sha_bytes(blob): return hashlib.sha256(blob).hexdigest()

def reset_world(view):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    s=bpy.context.scene
    s.unit_settings.system="METRIC"
    s.unit_settings.scale_length=1.
    s.render.engine="CYCLES"
    s.cycles.device="CPU"
    s.cycles.samples=6
    s.cycles.seed=3
    s.render.resolution_x=s.render.resolution_y=RES
    s.render.resolution_percentage=100
    s.render.image_settings.file_format="PNG"
    s.render.image_settings.color_mode="RGBA"
    s.render.film_transparent=True
    s.render.image_settings.color_depth="8"
    s.render.image_settings.compression=15
    camdata=bpy.data.cameras.new("source-calibrated-orthographic")
    cam=bpy.data.objects.new("source-calibrated-orthographic",camdata)
    s.collection.objects.link(cam)
    loc,target=VIEWS[view]
    cam.location=loc
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
    camdata.type="ORTHO"
    camdata.ortho_scale=1.75
    s.camera=cam
    light_data=bpy.data.lights.new("source-fixed-area",type="AREA")
    light=bpy.data.objects.new("source-fixed-area",light_data)
    s.collection.objects.link(light)
    light.location=(0.0,-2.0,2.0)
    light.rotation_euler=(Vector((0,0,0))-light.location).to_track_quat("-Z","Y").to_euler()
    light_data.energy=700
    light_data.shape="DISK"
    light_data.size=4.0
    bpy.context.view_layer.update()
    return s,cam

def mesh_material(name,rgb):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    mat.diffuse_color=(*rgb,1.)
    bsdf=mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value=(*rgb,1.)
    bsdf.inputs["Roughness"].default_value=0.70
    bsdf.inputs["Metallic"].default_value=0.
    return mat

def put_mesh(pose,paint):
    for segment in ("upper","lower"):
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj=bpy.context.object
        obj.name="source-native-"+segment
        obj.location=center(segment,pose)
        obj.scale=(LENGTH,WIDTH,HEIGHT)
        obj.rotation_euler=(0.,math.radians(pose if segment=="lower" else 0),0.)
        obj.data.materials.append(mesh_material(segment,colors(paint)[segment]))
        bpy.context.view_layer.update()
        expected=sorted(tuple(round(x,5) for x in row) for row in vertices(segment,pose))
        actual=sorted(tuple(round(x,5) for x in obj.matrix_world@v.co) for v in obj.data.vertices)
        if actual!=expected:
            raise AssertionError(f"Blender mesh deviates from rig-native source ground truth for {segment}: {actual} vs {expected}")
    return "MESH"

def put_splats(pose,paint):
    blob=ply_bytes(pose,paint)
    path=ROOT/f"source_splats_pose{pose}_{paint}.ply"
    path.write_bytes(blob)
    start=set(x.name for x in bpy.data.objects)
    bpy.ops.wm.ply_import(filepath=str(path))
    new=[x for x in bpy.data.objects if x.name not in start]
    if len(new)!=1 or new[0].type!="POINTCLOUD":
        raise AssertionError(f"not a single imported splat pointcloud {[(x.name,x.type) for x in new]}")
    typ=str(getattr(new[0].data,"type","UNAVAILABLE"))
    if typ!="GAUSSIAN_SPLAT":
        raise AssertionError("Blender importer is not Gaussian splat: "+typ)
    return typ

def take_image(scene,label):
    path=ROOT/(label+".png")
    scene.render.filepath=str(path)
    started=time.monotonic()
    bpy.ops.render.render(write_still=True)
    render_ms=round(1000*(time.monotonic()-started),2)
    if not path.is_file(): raise AssertionError("render missing: "+label)
    image=bpy.data.images.load(str(path),check_existing=False)
    try:
        w,h=image.size
        px=image.pixels[:]
        if (w,h)!=(RES,RES): raise AssertionError("unexpected image shape")
        mask=[]
        weighted=[]
        for y in range(h):
            for x in range(w):
                a=px[(y*w+x)*4+3]
                if a>.15:
                    mask.append((x,y))
                    weighted.append((x,y,a))
        if not mask: raise AssertionError("render is transparent: "+label)
        total=sum(e[2] for e in weighted)
        cx=sum(e[0]*e[2] for e in weighted)/total
        cy=sum(e[1]*e[2] for e in weighted)/total
        if not all(math.isfinite(x) for x in (cx,cy,total)):
            raise AssertionError("nonfinite decoded image")
        # The full images are retained only for in-job comparisons, never as JSON.
        colors=tuple(round(px[i],5) for i in range(0,len(px),4))
        rgb=tuple(float(px[4*i+j]) for i in range(w*h) for j in range(3))
        alpha=tuple(float(px[4*i+3]) for i in range(w*h))
        record={"file":path.name,"sha256":sha_bytes(path.read_bytes()),
                "render_ms":render_ms,"alpha_count":len(mask),
                "centroid_xy_px":[round(cx,4),round(cy,4)],
                "rgba_dimensions":[w,h,4]}
        return record,{"mask":set(mask),"rgb":rgb,"alpha":alpha}
    finally:
        bpy.data.images.remove(image)

def camera_record(cam):
    bpy.context.view_layer.update()
    return {"projection":"orthographic","ortho_scale_m":float(cam.data.ortho_scale),
            "resolution":[RES,RES],
            "camera_to_world_4x4": [[float(x) for x in row] for row in cam.matrix_world],
            "world_to_camera_4x4": [[float(x) for x in row] for row in cam.matrix_world.inverted()]}

def image_delta(a,b):
    if len(a)!=len(b): raise AssertionError("render size mismatch")
    return sum(abs(x-y) for x,y in zip(a,b))/len(a)

def compare_pair(mesh,gs):
    am,bm=mesh["mask"],gs["mask"]
    union=len(am|bm)
    inter=len(am&bm)
    if union==0: raise AssertionError("both representations blank")
    iou=inter/union
    if iou<.05: raise AssertionError(f"splat and source mesh do not overlap: {iou}")
    rgb_l1=image_delta(mesh["rgb"],gs["rgb"])
    alpha_l1=image_delta(mesh["alpha"],gs["alpha"])
    return {"binary_alpha_iou":round(iou,5),"mean_abs_rgb":round(rgb_l1,6),
            "mean_abs_alpha":round(alpha_l1,6),
            "interpretation":"SOURCE-DERIVED UNFITTED SPLATS; exploratory, not quality or training parity"}

def main():
    if bpy.app.version[:2]!=(5,3):
        raise AssertionError("not Blender 5.3: "+bpy.app.version_string)
    receipt={"schema":SCHEMA,"status":"FAIL","source_commit":os.environ.get("PR_HEAD",os.environ.get("GITHUB_SHA","LOCAL")),
             "build_sha":os.environ.get("GITHUB_SHA","LOCAL"),
             "blender":bpy.app.version_string,"platform":platform.platform(),
             "render_engine":"Cycles CPU","units":"meters","frames_per_second":24,
             "poses_deg":list(POSES),"paint_actions":list(PAINTS),
             "camera_views":list(VIEWS),
             "science_scope":"same known source-native rig geometry vs unfitted splat surface sampling; no pretrained model or latent reconstruction",
             "trials":[],"comparisons":[],"ground_truth":[]}
    obs={}
    try:
        for pose,paint,view in itertools.product(POSES,PAINTS,VIEWS):
            gt=ground_truth(pose,paint)
            gt["view"]=view
            gt["frame_index"]=POSES.index(pose)
            gt["frame_pts_seconds"]=POSES.index(pose)/24.
            for rep in REPS:
                s,cam=reset_world(view)
                kind=put_mesh(pose,paint) if rep=="mesh" else put_splats(pose,paint)
                ident=f"{rep}_pose{pose}_{paint}_{view}"
                r,img=take_image(s,ident)
                r.update({"representation":rep,"native_type":kind,
                          "pose_deg":pose,"paint":paint,"view":view,
                          "frame_index":POSES.index(pose),"frame_pts_seconds":POSES.index(pose)/24.,
                          "source_ply_sha256":gt["ply_sha256"] if rep=="splat" else None})
                receipt["trials"].append(r)
                obs[(rep,pose,paint,view)]=img
                if rep=="mesh":
                    gt["camera"]=camera_record(cam)
            receipt["ground_truth"].append(gt)
            ref=obs[("mesh",pose,paint,view)]
            challenger=obs[("splat",pose,paint,view)]
            receipt["comparisons"].append({"pose_deg":pose,"paint":paint,"view":view,
                                           **compare_pair(ref,challenger)})
        # Enforce actual material intervention and animation in both representations.
        receipt["intervention_checks"]=[]
        for rep,view in itertools.product(REPS,VIEWS):
            base=obs[(rep,45,"base",view)]
            repaint=obs[(rep,45,"repaint",view)]
            color_delta=image_delta(base["rgb"],repaint["rgb"])
            if not color_delta>.003:
                raise AssertionError(f"{rep}/{view}: native repaint did not visibly change RGB ({color_delta})")
            a=obs[(rep,0,"base",view)]["mask"]
            b=obs[(rep,90,"base",view)]["mask"]
            union=len(a|b)
            jaccard=len(a&b)/union if union else 1
            if jaccard>.95:
                raise AssertionError(f"{rep}/{view}: changing pose was not visible (IoU={jaccard})")
            receipt["intervention_checks"].append({"representation":rep,"view":view,
                "repaint_mean_abs_rgb":round(color_delta,6),
                "pose0_pose90_mask_iou":round(jaccard,6)})
        assert len(receipt["trials"])==24
        assert len(receipt["comparisons"])==12
        assert len(receipt["ground_truth"])==12
        receipt["summary"]={"renders":24,"matched_source_pairs":12,"source_pose_states":3,
          "source_paint_states":2,"heldout_camera_views":1,
          "alpha_iou_min":min(x["binary_alpha_iou"] for x in receipt["comparisons"]),
          "alpha_iou_mean":round(sum(x["binary_alpha_iou"] for x in receipt["comparisons"])/12,5),
          "alpha_iou_max":max(x["binary_alpha_iou"] for x in receipt["comparisons"]),
          "observed_quality_claim":"NONE: unfitted Gaussian shell vs exact native mesh is not fair optimized-splat ranking",
          "native_source_truth_preserved":True}
        receipt["status"]="PASS"
    except BaseException as exc:
        receipt["error"]={"type":type(exc).__name__,"message":str(exc)}
        raise
    finally:
        path=ROOT/"receipt.json"
        path.write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
        summary={k:v for k,v in receipt.items() if k not in ("ground_truth","trials","comparisons")}
        print("VIRTUAL_RIG_R1_SUMMARY="+json.dumps(summary,sort_keys=True),flush=True)
    return 0

if __name__=="__main__":
    sys.exit(main())
