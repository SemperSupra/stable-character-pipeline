#!/usr/bin/env python3
"""R63: original, source-safe object-centric inverse graphics CPU bakeoff.

Executes actual calibrated perspective ray casting and numerical inverse
fitting on two synthetic living-room scenes. Does NOT run pretrained neural
reconstruction, SAM, PyTorchGeoNodes, Mira-Scene, Oneirifact private source,
or a VLM. The latter remain distinct admission-gated candidates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import resource
import time
from dataclasses import dataclass
from pathlib import Path
import numpy as np

WIDTH=48
HEIGHT=48
FX=FY=52.0
SEED=63015
CLASSES=("sofa","chair","person")
SCHEMA="inverse-scene-bakeoff/r0"
COLORS=np.array([[178,102,92],[82,140,185],[172,171,116]],dtype=np.uint8)
VIEWS=[
  (np.array([0.,-5.8,2.5]),np.array([0.,.55,.84])),
  (np.array([4.8,-3.8,2.9]),np.array([0.,.55,.85])),
  (np.array([-4.7,-3.3,2.2]),np.array([0.,.6,.86])),
  (np.array([1.4,5.9,2.5]),np.array([0.,.5,.85])),
]
TRUTH=[
 np.array([[-.75,.15,1.07,.94,1.04],
           [1.04,-.28,.92,1.10,.96],
           [.53,1.22,1.00,.98,1.00]],dtype=float),
 np.array([[-1.00,.35,.88,1.15,.91],
           [.96,.30,1.11,.94,1.08],
           [-.20,1.42,1.09,1.03,1.07]],dtype=float)
]
# Valid perturbations fixed before trial; same source start for all arms-known methods.
INIT_OFFSETS=np.array([[.36,-.26,-.22,.19,-.16],
                       [-.29,.32,.24,-.18,.15],
                       [.25,-.30,-.18,.15,-.13]])
# Both sofa and chair truth have two armrests. Scene/object methods know
# the correct shape family; discrete-program treatment must rediscover this.
ARMS_TRUE=(2,2)
MAX_SCALED_STEP=(.32,.17,.09,.045)
TRAIN_VIEWS=(0,1)
HOLDOUT_VIEWS=(2,3)

def unit(v):
    n=np.linalg.norm(v)
    if not np.isfinite(n) or n<1e-10:raise ValueError("degenerate camera")
    return v/n

@dataclass(frozen=True)
class Camera:
    origin: np.ndarray
    direction: np.ndarray
    right: np.ndarray
    up: np.ndarray
    rays: np.ndarray
    ray_dot_fwd: np.ndarray
    extrinsic: np.ndarray
    intrinsic: np.ndarray

def camera_at(origin,look):
    f=unit(look-origin)
    right=unit(np.cross(f,np.array([0.,0.,1.])))
    up=unit(np.cross(right,f))
    # Camera convention x right, y up, z forward. Image y down.
    extrinsic=np.eye(4)
    extrinsic[:3,:3]=np.stack([right,-up,f],axis=0)
    extrinsic[:3,3]=-(extrinsic[:3,:3]@origin)
    k=np.array([[FX,0.,WIDTH/2],[0.,FY,HEIGHT/2],[0.,0.,1.]])
    yy,xx=np.meshgrid(np.arange(HEIGHT),np.arange(WIDTH),indexing="ij")
    dirs=f+((xx+.5-WIDTH/2)/FX)[...,None]*right-((yy+.5-HEIGHT/2)/FY)[...,None]*up
    dirs=dirs/np.linalg.norm(dirs,axis=2,keepdims=True)
    dot=dirs@f
    if not np.all(dot>0):raise AssertionError("invalid camera rays")
    return Camera(origin,f,right,up,dirs.reshape(-1,3),dot.reshape(-1),extrinsic,k)

CAMERAS=tuple(camera_at(*pair) for pair in VIEWS)

def box(center,size):
    return ("box",np.asarray(center,float),np.asarray(size,float))

def sphere(center,radius):
    return ("sphere",np.asarray(center,float),float(radius))

def make_parts(index,p,arms):
    x,y,sx,sy,sz=map(float,p)
    if min(sx,sy,sz)<=0:raise ValueError("negative scales")
    parts=[]
    if index==0: # sofa: seat/back/two symmetric arms and four legs
        parts += [
          box([x,y,.49*sz],[1.52*sx,.76*sy,.22*sz]),
          box([x,y+.33*sy,.81*sz],[1.57*sx,.16*sy,.72*sz]),
        ]
        if arms==2:
            for sign in (-1,1):
                parts.append(box([x+sign*.74*sx,y,.71*sz],[.17*sx,.76*sy,.46*sz]))
        for signx in (-1,1):
            for signy in (-1,1):
                parts.append(box([x+signx*.62*sx,y+signy*.27*sy,.21*sz],[.10*sx,.11*sy,.33*sz]))
    elif index==1: # chair: seat/back/optional symmetric armrests and four legs
        parts += [
          box([x,y,.51*sz],[.78*sx,.72*sy,.19*sz]),
          box([x,y+.31*sy,.85*sz],[.80*sx,.16*sy,.70*sz]),
        ]
        if arms==2:
            for sign in (-1,1):
                parts.append(box([x+sign*.36*sx,y,.73*sz],[.12*sx,.66*sy,.41*sz]))
        for signx in (-1,1):
            for signy in (-1,1):
                parts.append(box([x+signx*.31*sx,y+signy*.28*sy,.24*sz],[.08*sx,.09*sy,.40*sz]))
    elif index==2: # stylized stationary mannequin, NOT identity/rig/soft tissue
        parts += [
          box([x,y,1.18*sz],[.46*sx,.26*sy,.65*sz]),
          sphere([x,y,1.70*sz],.195*min(sx,sz)),
          box([x-.135*sx,y,.46*sz],[.175*sx,.22*sy,.87*sz]),
          box([x+.135*sx,y,.46*sz],[.175*sx,.22*sy,.87*sz]),
          box([x-.305*sx,y,1.08*sz],[.125*sx,.2*sy,.62*sz]),
          box([x+.305*sx,y,1.08*sz],[.125*sx,.2*sy,.62*sz]),
        ]
    else:
        raise ValueError("unknown object class")
    return parts

def box_hit(cam,loc,dims):
    # Ray/slab intersection in metric world coordinates; no sampling shortcuts.
    lo=loc-dims*.5
    hi=loc+dims*.5
    dirs=cam.rays
    parallel=np.abs(dirs)<1e-9
    fail=np.any(parallel & ((cam.origin<lo)|(cam.origin>hi)),axis=1)
    safe=np.where(parallel,1.,dirs)
    a=(lo-cam.origin)/safe
    b=(hi-cam.origin)/safe
    tlo=np.where(parallel,-np.inf,np.minimum(a,b))
    thi=np.where(parallel, np.inf,np.maximum(a,b))
    near=np.max(tlo,axis=1)
    far=np.min(thi,axis=1)
    t=np.where(near>1e-6,near,far)
    valid=(far>=np.maximum(near,0.)) & (t>1e-6) & (~fail)
    return np.where(valid,t,np.inf)

def sphere_hit(cam,loc,r):
    d=cam.rays
    o=cam.origin-loc
    b=d@o
    c=o@o-r*r
    disc=b*b-c
    sq=np.sqrt(np.maximum(disc,0))
    near=-b-sq
    far=-b+sq
    t=np.where(near>1e-6,near,far)
    return np.where((disc>=0)&(t>1e-6),t,np.inf)

def render(params,cam,arms=ARMS_TRUE):
    params=np.asarray(params,float).reshape(3,5)
    best=np.full(WIDTH*HEIGHT,np.inf)
    owner=np.full(WIDTH*HEIGHT,-1,dtype=np.int8)
    for i in range(3):
        for kind,cen,third in make_parts(i,params[i],arms[i] if i<2 else 0):
            d=box_hit(cam,cen,third) if kind=="box" else sphere_hit(cam,cen,third)
            hit=d<best
            best=np.where(hit,d,best)
            owner=np.where(hit,i,owner)
    depth=np.where(np.isfinite(best),best*cam.ray_dot_fwd,0).reshape(HEIGHT,WIDTH)
    label=owner.reshape(HEIGHT,WIDTH)
    return label,depth

def source_image(label):
    # A render artifact, not training data: no texture/model leakage.
    rgb=np.full((HEIGHT,WIDTH,3),235,dtype=np.uint8)
    for i in range(3):rgb[label==i]=COLORS[i]
    return rgb

def metrics(pred,real):
    label,depth=pred
    target,target_depth=real
    a=label>=0
    b=target>=0
    union=np.count_nonzero(a|b)
    global_iou=np.count_nonzero(a&b)/max(1,union)
    ious=[]
    for i in range(3):
        pa=label==i
        pb=target==i
        u=np.count_nonzero(pa|pb)
        ious.append(np.count_nonzero(pa&pb)/max(1,u))
    shared=a&b
    depth_mae=float(np.mean(np.abs(depth[shared]-target_depth[shared]))) if np.any(shared) else 4.0
    return {"global_iou":float(global_iou),"instance_iou":list(map(float,ious)),
            "mean_instance_iou":float(np.mean(ious)),
            "shared_depth_mae_m":depth_mae,
            "scene_pixel_error":float(np.mean(a!=b))}

def bounded(params):
    x=np.asarray(params,float).reshape(3,5).copy()
    x[:,0:2]=np.clip(x[:,0:2],-2.4,2.4)
    x[:,2:5]=np.clip(x[:,2:5],.55,1.6)
    return x

def objective(par,obs,mode,arms=ARMS_TRUE):
    m=[]
    for idx in TRAIN_VIEWS:
        pred=render(par,CAMERAS[idx],arms)
        m.append(metrics(pred,obs[idx]))
    global_loss=np.mean([1-x["global_iou"] for x in m])
    instance_loss=np.mean([1-x["mean_instance_iou"] for x in m])
    depth_loss=np.mean([min(2.,x["shared_depth_mae_m"]) for x in m])
    if mode=="scene":
        # No instance IDs. Same 15 parameters/renderer/evaluation budget.
        return float(global_loss+.07*depth_loss)
    return float(.78*instance_loss+.22*global_loss+.07*depth_loss)

def optimize(initial,obs,mode,arms=ARMS_TRUE):
    p=bounded(initial)
    start=time.perf_counter()
    calls=0
    best=objective(p,obs,mode,arms)
    calls+=1
    for step in MAX_SCALED_STEP:
        # Exactly 2*15 candidate probes at each resolution.
        for i in range(3):
            for j in range(5):
                for sign in (-1.,1.):
                    candidate=p.copy()
                    candidate[i,j]+=sign*step*(1.25 if j>=2 else 1.)
                    candidate=bounded(candidate)
                    loss=objective(candidate,obs,mode,arms)
                    calls+=1
                    if loss<best-1e-10:
                        p,best=candidate,loss
    return p,{"objective":best,"renderer_scene_evaluations":calls*len(TRAIN_VIEWS),
              "objective_evaluations":calls,"elapsed_seconds":round(time.perf_counter()-start,3)}

def noisy_labels(observations,seed):
    # Synthetic segmentation corruption, not neural SAM inference.
    rng=np.random.default_rng(seed)
    ans={}
    for k,(lab,dep) in observations.items():
        distorted=lab.copy()
        valid=np.where(lab.reshape(-1)>=0)[0]
        if len(valid)>0:
            take=rng.choice(valid,size=max(1,len(valid)//12),replace=False)
            flat=distorted.reshape(-1)
            flat[take]=-1
        ans[k]=(distorted,dep)
    return ans

def init_from_metric_depth(observations):
    # Object segmented visible RGB-D unprojection. No hidden object dimensions
    # inferred from unsupported unseen surfaces; deliberately coarse prior.
    out=np.array([[0.,0.,.8,.8,.9]]*3,dtype=float)
    points={i:[] for i in range(3)}
    for view_id in TRAIN_VIEWS:
        lab,depth=observations[view_id]
        cam=CAMERAS[view_id]
        ld=lab.reshape(-1)
        dd=depth.reshape(-1)
        for i in range(3):
            good=(ld==i)&(dd>0)
            if not np.any(good):continue
            xyz=cam.origin+cam.rays[good]*(dd[good]/cam.ray_dot_fwd[good])[:,None]
            points[i].append(xyz)
    for i in range(3):
        if not points[i]:continue
        xyz=np.concatenate(points[i],axis=0)
        xlo,xhi=np.percentile(xyz[:,0],[4,96])
        ylo,yhi=np.percentile(xyz[:,1],[4,96])
        zhigh=float(np.percentile(xyz[:,2],98))
        nominal=(1.65,.8,1.2) if i==0 else ((.86,.79,1.25) if i==1 else (.85,.28,1.9))
        out[i,:]=[(xlo+xhi)/2,(ylo+yhi)/2,
                   np.clip((xhi-xlo)/nominal[0],.55,1.6),
                   np.clip((yhi-ylo)/nominal[1],.55,1.6),
                   np.clip(zhigh/nominal[2],.55,1.6)]
    return bounded(out)

def evaluation(p,truth,arms=ARMS_TRUE):
    held=[metrics(render(p,CAMERAS[k],arms),render(truth,CAMERAS[k],ARMS_TRUE))
          for k in HOLDOUT_VIEWS]
    err=np.asarray(p).reshape(3,5)-truth
    # Explicit source metric geometry proxy: in meters for x,y and
    # dimensionless for shape scales. Not a mesh Chamfer/physical topology score.
    return {"heldout_global_iou":round(float(np.mean([x["global_iou"] for x in held])),5),
      "heldout_mean_instance_iou":round(float(np.mean([x["mean_instance_iou"] for x in held])),5),
      "heldout_depth_mae_m":round(float(np.mean([x["shared_depth_mae_m"] for x in held])),5),
      "param_rmse_mixed_units":round(float(np.sqrt(np.mean(err*err))),5),
      "center_rmse_m":round(float(np.sqrt(np.mean(err[:,:2]**2))),5),
      "scale_rmse_unitless":round(float(np.sqrt(np.mean(err[:,2:5]**2))),5),
      "heldout_per_view":held}

def serialize_camera(cam):
    return {"K":cam.intrinsic.tolist(),"world_to_camera":cam.extrinsic.tolist(),
            "camera_to_world":np.linalg.inv(cam.extrinsic).tolist(),
            "origin_xyz_m":cam.origin.tolist(),
            "z_depth_convention":"positive optical-axis meters"}

def case_run(case_id,truth,out):
    observed={k:render(truth,CAMERAS[k]) for k in range(4)}
    initial=bounded(truth+INIT_OFFSETS)
    cases={}
    # A and B matched identical 15 parameter source priors and optimizer budget.
    a,ra=optimize(initial,observed,"scene")
    b,rb=optimize(initial,observed,"object")
    cases["A_whole_scene_no_instances"]={"parameter_estimate":a.tolist(),"runtime":ra,"metrics":evaluation(a,truth)}
    cases["B_object_first_oracle_instances"]={"parameter_estimate":b.tolist(),"runtime":rb,"metrics":evaluation(b,truth)}
    # C deliberately starts without any furniture arms, then structured program search.
    noarms=(0,0)
    c,rc=optimize(initial,observed,"object",noarms)
    best_arms=noarms
    discrete=[]
    for arms in ((0,0),(0,2),(2,0),(2,2)):
        loss=objective(c,observed,"object",arms)
        discrete.append({"arms":arms,"loss":round(loss,6)})
        if loss<min(x["loss"] for x in discrete[:-1]) if len(discrete)>1 else True:
            best_arms=arms
    # After structure selection, allow a fair documented second continuous fit.
    c,rc2=optimize(c,observed,"object",best_arms)
    cases["C_part_program_discrete_then_fit"]={
       "parameter_estimate":c.tolist(),"armrest_program_selected":best_arms,
       "armrest_ground_truth":ARMS_TRUE,"discrete_trials":discrete,
       "runtime":{"objective_evaluations":rc["objective_evaluations"]+rc2["objective_evaluations"]+4,
                  "elapsed_seconds":round(rc["elapsed_seconds"]+rc2["elapsed_seconds"],3)},
       "metrics":evaluation(c,truth,best_arms)}
    # D uses segmented metric depth as a geometric prior, not source parameters.
    initd=init_from_metric_depth(observed)
    d,rd=optimize(initd,observed,"object")
    cases["D_RGBD_geometry_init_then_object_fit"]={
      "depth_init":initd.tolist(),"parameter_estimate":d.tolist(),
      "runtime":rd,"metrics":evaluation(d,truth)}
    # Separate segmentation quality sensitivity - only corrupted observations
    # from training views, holdout oracle remains clean.
    noisy=noisy_labels(observed,SEED+case_id)
    e,re=optimize(initial,noisy,"object")
    cases["E_noisy_segmentation_8pct_drop"]={
      "parameter_estimate":e.tolist(),"runtime":re,"metrics":evaluation(e,truth)}
    # Source images/masks for downstream independent audits.
    try:
        from PIL import Image
        for k in range(4):
            label,depth=observed[k]
            Image.fromarray(source_image(label)).save(out/f"case{case_id}_view{k}_rgb.png")
            mapped=np.where(label<0,0,(label+1)*70).astype(np.uint8)
            Image.fromarray(mapped).save(out/f"case{case_id}_view{k}_instance.png")
            # Finite metric Z, mm with 0 for background and no overflow.
            mm=np.clip(np.round(depth*1000),0,65535).astype(np.uint16)
            Image.fromarray(mm).save(out/f"case{case_id}_view{k}_depth_mm.png")
    except ModuleNotFoundError:
        pass
    return {"source_truth":truth.tolist(),"source_arm_program":ARMS_TRUE,
       "starting_parameters":initial.tolist(),
       "methods":cases,"source_views":[serialize_camera(c) for c in CAMERAS]}

def validate():
    for ci,truth in enumerate(TRUTH):
        for i in range(4):
            m=render(truth,CAMERAS[i])
            assert np.count_nonzero(m[0]>=0)>0
            assert len(np.unique(m[0]))>=3
            assert np.isfinite(m[1]).all()
            assert (m[1]>=0).all()
            assert np.allclose(CAMERAS[i].extrinsic@np.append(CAMERAS[i].origin,1.),[0,0,0,1],atol=1e-8)
            self_metric=metrics(m,m)
            assert self_metric["global_iou"]==1.
            assert self_metric["mean_instance_iou"]==1.
        assert evaluation(truth,truth)["param_rmse_mixed_units"]==0.
    try:
        camera_at(np.zeros(3),np.zeros(3))
    except ValueError:pass
    else: raise AssertionError("invalid camera admitted")
    try:
        make_parts(0,np.array([0,0,-1,1,1]),2)
    except ValueError:pass
    else:raise AssertionError("negative shape admitted")
    assert len(TRUTH)==2
    print("SCENE_SOURCE_SELF_TEST=PASS",flush=True)

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--out",default="out/inverse-scene-r0")
    args=cli.parse_args()
    root=Path(args.out)
    root.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    report={"schema":SCHEMA,"status":"FAIL","source_commit":os.getenv("GITHUB_SHA","LOCAL"),
      "image_width":WIDTH,"image_height":HEIGHT,"focal_px":FX,"seed":SEED,
      "scene_cases":len(TRUTH),"train_views":TRAIN_VIEWS,"heldout_views":HOLDOUT_VIEWS,
      "methods":["A_whole_scene_no_instances","B_object_first_oracle_instances",
                 "C_part_program_discrete_then_fit","D_RGBD_geometry_init_then_object_fit",
                 "E_noisy_segmentation_8pct_drop"],
      "method_scope":"REAL numerical inverse optimization on ORIGINAL synthetic geometric scenes; not an upstream neural/Oneirifact/splat-trained/VLM execution",
      "source_cameras_known":True,"runnable_model_weights":False,
      "negative_claims":["No trained segmenter was executed: instance labels are privileged source oracle",
          "No actual PyTorchGeoNodes, Mira, SAM3D, GenIA, TRELLIS or VLM inference",
          "No Oneirifact native feature graph/export code or third-party assets used",
          "No inferred rigged adult or semantic mesh from Gaussian radiance"],
      "cases":[]}
    try:
        validate()
        for i,truth in enumerate(TRUTH):
            receipt=case_run(i,truth,root)
            report["cases"].append(receipt)
            print("SCENE_CASE_SUMMARY="+json.dumps({"case_id":i,"methods":{
               k:{"heldout_instance_iou":v["metrics"]["heldout_mean_instance_iou"],
                  "center_rmse_m":v["metrics"]["center_rmse_m"],
                  "wall_s":v["runtime"]["elapsed_seconds"],
                  "evals":v["runtime"]["objective_evaluations"]} for k,v in receipt["methods"].items()}},
                  sort_keys=True),flush=True)
        report["status"]="PASS"
    except BaseException as e:
        report["error"]={"type":type(e).__name__,"message":str(e)}
        raise
    finally:
        report["elapsed_total_seconds"]=round(time.perf_counter()-start,3)
        report["peak_rss_kb"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report_path=root/"receipt.json"
        report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        print("INVERSE_SCENE_FINAL="+json.dumps({"status":report["status"],
          "wall_s":report["elapsed_total_seconds"],"peak_rss_kb":report["peak_rss_kb"],
          "receipt_sha256":hashlib.sha256(report_path.read_bytes()).hexdigest(),
          "cases":len(report["cases"])},sort_keys=True),flush=True)
if __name__=="__main__":
    main()
