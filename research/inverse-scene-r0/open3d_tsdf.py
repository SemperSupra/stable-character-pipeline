#!/usr/bin/env python3
"""Run real Open3D ScalableTSDFVolume meshing on R63 original calibrated RGB-D.

This is actual upstream Open3D CPU integration/mesh extraction/raycasting, not
PyTorchGeoNodes, learned 3D, Oneirifact source, or semantic object recovery.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
import open3d as o3d

sys.path.insert(0,str(Path(__file__).resolve().parent))
from bakeoff import (CAMERAS,TRUTH,TRAIN_VIEWS,HOLDOUT_VIEWS,
                     WIDTH,HEIGHT,FX,FY,render,source_image,SEED)

ROOT=Path(os.environ.get("R63_TSDF_OUT","out/r63-open3d-tsdf")).resolve()
ROOT.mkdir(parents=True,exist_ok=True)
VOXEL_M=.045
TRUNC_M=.135
SCHEMA="r63-upstream-open3d-tsdf/v1"

def source_rgbd(truth,view,noise_std=0.,drop_frac=0.,rng=None):
    label,metric_z=render(truth,CAMERAS[view])
    depth=metric_z.copy().astype(np.float32)
    if noise_std:
        if rng is None:raise ValueError("noise requires deterministic seeded rng")
        mask=depth>0
        depth[mask]=np.maximum(.01,depth[mask]+rng.normal(0,noise_std,size=mask.sum()))
    if drop_frac:
        valid=np.where(depth.reshape(-1)>0)[0]
        n=int(len(valid)*drop_frac)
        if n:
            depth.reshape(-1)[rng.choice(valid,n,replace=False)]=0.
    color=o3d.geometry.Image(np.ascontiguousarray(source_image(label)))
    d=o3d.geometry.Image(np.ascontiguousarray(depth))
    # Float meters -> depth_scale=1, no 16-bit quantization loss.
    return o3d.geometry.RGBDImage.create_from_color_and_depth(
        color,d,depth_scale=1.,depth_trunc=8.,convert_rgb_to_intensity=False)

def upstream_reconstruct(truth,integrated_views,noise_std=0.,drop_frac=0.,seed=SEED):
    began=time.perf_counter()
    rng=np.random.default_rng(seed)
    fusion=o3d.pipelines.integration.ScalableTSDFVolume(
        voxel_length=VOXEL_M,sdf_trunc=TRUNC_M,
        color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8)
    intr=o3d.camera.PinholeCameraIntrinsic(WIDTH,HEIGHT,FX,FY,WIDTH/2,HEIGHT/2)
    for view in integrated_views:
        rgbd=source_rgbd(truth,view,noise_std,drop_frac,rng)
        fusion.integrate(rgbd,intr,np.ascontiguousarray(CAMERAS[view].extrinsic,dtype=np.float64))
    mesh=fusion.extract_triangle_mesh()
    if len(mesh.vertices)==0 or len(mesh.triangles)==0:
        raise AssertionError("Open3D returned empty mesh for valid metric RGB-D")
    if not np.isfinite(np.asarray(mesh.vertices)).all():
        raise AssertionError("nonfinite mesh source")
    mesh.compute_vertex_normals()
    return mesh,time.perf_counter()-began

def cast_mesh(mesh,cam):
    tensor=o3d.t.geometry.TriangleMesh.from_legacy(mesh)
    engine=o3d.t.geometry.RaycastingScene()
    engine.add_triangles(tensor)
    rays=np.concatenate((np.broadcast_to(cam.origin,(len(cam.rays),3)),cam.rays),axis=1)
    out=engine.cast_rays(o3d.core.Tensor(np.ascontiguousarray(rays,dtype=np.float32)))
    ts=out["t_hit"].numpy().reshape(-1).astype(float)
    ok=np.isfinite(ts)&(ts>0)
    z=np.where(ok,ts*cam.ray_dot_fwd,0).reshape(HEIGHT,WIDTH)
    return ok.reshape(HEIGHT,WIDTH),z

def quality(mesh,truth,views):
    measurements=[]
    for view in views:
        gt_label,gt_z=render(truth,CAMERAS[view])
        src=gt_label>=0
        hit,depth=cast_mesh(mesh,CAMERAS[view])
        inter=np.count_nonzero(src&hit)
        union=np.count_nonzero(src|hit)
        overlap=src&hit
        depth_l1=float(np.mean(np.abs(gt_z[overlap]-depth[overlap]))) if np.any(overlap) else None
        measurements.append({
            "view":int(view),"IoU":round(float(inter/max(1,union)),6),
            "target_foreground_pixels":int(np.count_nonzero(src)),
            "reconstruction_foreground_pixels":int(np.count_nonzero(hit)),
            "shared_depth_mae_m":None if depth_l1 is None else round(depth_l1,6),
            "false_positive_pixels":int(np.count_nonzero(hit&~src)),
            "false_negative_pixels":int(np.count_nonzero(src&~hit))})
    return measurements

def run():
    start=time.perf_counter()
    rec={"schema":SCHEMA,"status":"FAIL",
        "source_commit":os.environ.get("GITHUB_SHA","LOCAL"),
        "open3d_version":o3d.__version__,
        "cpu_only":True,"source_rights":"original synthetic R63, no external assets",
        "mesh_kind":"actual Open3D RGB-D TSDF -> marching-cubes triangle mesh",
        "geometry_control":"source analytic boxes/sphere, no segmentation passed to TSDF",
        "camera_convention":"world-to-OpenCV forward Z, float optical-axis depth meters",
        "voxel_length_m":VOXEL_M,"truncation_m":TRUNC_M,
        "cases":[],"scientific_nonclaims":[
          "No neural model or latent shape optimization", "No object instances or procedural parameter recovery",
          "All-view treatment scores reconstructed training views, not an independent test",
          "No source exact watertightness or editable feature graph promised"]}
    try:
        if not o3d.__version__.startswith("0.19"):
            raise RuntimeError("pin mismatch: actual Open3D 0.19 required")
        assert len(CAMERAS)==4 and np.linalg.det(CAMERAS[0].extrinsic[:3,:3])>0.9999
        # Audit RGB-D source convention against exact ray-caster.
        first=source_rgbd(TRUTH[0],0)
        assert tuple(np.asarray(first.depth).shape)==(HEIGHT,WIDTH)
        assert np.count_nonzero(np.asarray(first.depth))>0
        for case_id,truth in enumerate(TRUTH):
            outcomes=[]
            variants=(
              ("train_two_clean",TRAIN_VIEWS,0.,0.),
              ("train_two_noisy",TRAIN_VIEWS,.025,.10),
              ("four_views_upper_bound",tuple(range(4)),0.,0.)
            )
            for name,views,noise,drop in variants:
                mesh,wall=upstream_reconstruct(truth,views,noise,drop,seed=SEED+case_id)
                path=ROOT/f"case{case_id}_{name}_open3d.ply"
                if not o3d.io.write_triangle_mesh(str(path),mesh,write_ascii=False):
                    raise AssertionError("Open3D mesh exporter failed")
                payload=path.read_bytes()
                integrated_holdout=any(k in views for k in HOLDOUT_VIEWS)
                evaluations=quality(mesh,truth,HOLDOUT_VIEWS)
                # Mean silhouette and depth are deliberately local to this geometry,
                # not weighted against procedural-param recovery metrics.
                outcome={"method":name,
                  "views_integrated":list(views),"evaluation_views":list(HOLDOUT_VIEWS),
                  "evaluation_contains_integrated_views":bool(integrated_holdout),
                  "depth_noise_sigma_m":noise,"dropout_fraction":drop,
                  "mesh_vertices":len(mesh.vertices),"mesh_triangles":len(mesh.triangles),
                  "is_watertight":bool(mesh.is_watertight()),
                  "is_edge_manifold":bool(mesh.is_edge_manifold()),
                  "time_seconds":round(wall,4),
                  "export_sha256":hashlib.sha256(payload).hexdigest(),
                  "export_size_bytes":len(payload),
                  "views":evaluations,
                  "mean_eval_silhouette_iou":round(float(np.mean([x["IoU"] for x in evaluations])),5)}
                outcomes.append(outcome)
                print("OPEN3D_TSDF_REP="+json.dumps({"case":case_id,**{k:v for k,v in outcome.items()
                        if k not in ("views","export_sha256")}},sort_keys=True),flush=True)
            rec["cases"].append({"case_id":case_id,"outcomes":outcomes})
        rec["status"]="PASS"
    except BaseException as exc:
        rec["error"]={"type":type(exc).__name__,"message":str(exc)}
        raise
    finally:
        rec["elapsed_wall_seconds"]=round(time.perf_counter()-start,4)
        rec["peak_rss_kb"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        path=ROOT/"receipt.json"
        path.write_text(json.dumps(rec,indent=2,sort_keys=True)+"\n")
        print("OPEN3D_TSDF_FINAL="+json.dumps({
          "status":rec["status"],"cases":len(rec["cases"]),
          "elapsed_s":rec["elapsed_wall_seconds"],"peak_rss_kb":rec["peak_rss_kb"],
          "receipt_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
          "open3d_version":o3d.__version__},sort_keys=True),flush=True)
if __name__=="__main__":
    run()
