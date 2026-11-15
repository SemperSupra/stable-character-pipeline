#!/usr/bin/env python3
"""R63 OpenCV real CPU color-cluster segmentation -> geometric inverse fit.

Uses actual cv2.kmeans (not SAM or learned semantic segmentation), color
exemplars as explicit weak supervision, and independent source-truth metrics.
Models how a mask consumer breaks under material/illumination confounding.
"""
from __future__ import annotations
import hashlib
import itertools
import json
import os
import resource
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parent))
from bakeoff import (CAMERAS,COLORS,HEIGHT,WIDTH,TRUTH,INIT_OFFSETS,TRAIN_VIEWS,
                     SEED,render,source_image,metrics,optimize,evaluation,bounded)

ROOT=Path(os.environ.get("R63_MASK_OUT","out/r63-opencv-masks")).resolve()
ROOT.mkdir(parents=True,exist_ok=True)
SCHEMA="r63-cv2-weak-colors-to-inverse-fit/v1"
BACKGROUND=np.array([235,235,235],dtype=float)
PROTOTYPES=np.vstack([COLORS.astype(float),BACKGROUND[None,:]])

def modified_rgb(label,condition,seed):
    rgb=source_image(label)
    if condition=="distinct":
        return rgb
    if condition=="shared_furniture_material":
        # Both furniture objects are the SAME material color: no RGB-based
        # pixel classifier can assign semantic identity without extra cues.
        rgb[label==1]=rgb[label==0][0] if np.any(label==0) else COLORS[0]
        return rgb
    if condition=="illumination_noise":
        rng=np.random.default_rng(seed)
        gradient=np.linspace(.68,1.24,WIDTH)[None,:,None]
        noisy=rgb.astype(float)*gradient+rng.normal(0,9,size=rgb.shape)
        return np.clip(noisy,0,255).astype(np.uint8)
    raise ValueError("unknown nuisance")

def cluster_mask(rgb,seed):
    # Genuine OpenCV color K-means. Class labels are NOT supervised by true
    # instance maps. Assignment to the four known semantic color prototypes
    # is an explicit weak-supervision advantage over zero-shot SAM.
    cv2.setRNGSeed(int(seed))
    data=np.ascontiguousarray(rgb.reshape(-1,3).astype(np.float32))
    criteria=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,40,.2)
    compactness,raw_centers,centers=cv2.kmeans(data,4,None,criteria,3,cv2.KMEANS_PP_CENTERS)
    # OpenCV returns (compactness, labels, centers), not vice versa.
    # Keep every permutation independent of true object labels.
    labels_flat=np.asarray(raw_centers).reshape(-1)
    costs=np.linalg.norm(centers[:,None,:]-PROTOTYPES[None,:,:],axis=2)
    perm=min(itertools.permutations(range(4)),
             key=lambda p:sum(costs[j,p[j]] for j in range(4)))
    out=np.array(perm,dtype=np.int8)[labels_flat]
    out=np.where(out==3,-1,out).reshape(HEIGHT,WIDTH)
    assigned_distances=[float(costs[j,perm[j]]) for j in range(4)]
    return out,{"opencv_compactness":round(float(compactness),3),
       "centers_RGB":np.round(centers,2).tolist(),"color_assignments":list(perm),
       "prototype_distances":list(map(lambda q:round(q,3),assigned_distances)),
       "max_exemplar_mismatch":round(max(assigned_distances),3),
       "weak_supervision":"known RGB color exemplars, no neural segmentation or image-text detection"}

def label_metrics(pred,gt):
    outputs=[]
    for i in range(3):
        src=gt==i
        p=pred==i
        inter=np.count_nonzero(src&p)
        union=np.count_nonzero(src|p)
        outputs.append(round(float(inter/max(1,union)),6))
    valid=gt>=0
    return {"mean_instance_iou":round(float(np.mean(outputs)),6),
      "per_instance_iou":outputs,
      "valid_source_pixels":int(np.count_nonzero(valid)),
      "misclassified_all_pixels":int(np.count_nonzero(pred!=gt))}

def validate():
    # Honest, deterministic result; not perfect segmentation asserted.
    perfect=np.zeros((HEIGHT,WIDTH),dtype=np.int8)
    perfect[5:10,4:9]=1
    perfect[15:20,4:9]=2
    perfect[25:30,4:9]=0
    rgb=source_image(perfect)
    result,meta=cluster_mask(rgb,SEED)
    assert result.shape==(HEIGHT,WIDTH)
    assert set(np.unique(result)).issubset({-1,0,1,2})
    assert len(meta["centers_RGB"])==4
    assert np.isfinite(meta["opencv_compactness"])
    for unsupported in ("",None,"malformed"):
        try:modified_rgb(perfect,unsupported,SEED)
        except ValueError:pass
        else:raise AssertionError("unknown nuisance admitted")
    print("CV2_SEGMENTATION_CONTROLS=PASS",flush=True)

def run():
    t0=time.perf_counter()
    rec={"schema":SCHEMA,"status":"FAIL","source_commit":os.environ.get("GITHUB_SHA","LOCAL"),
         "cv2_version":cv2.__version__,"opencv_rng_seed":SEED,
         "image_resolution":[WIDTH,HEIGHT],
         "segmentation_algorithm":"upstream OpenCV kmeans (K=4) + known RGB exemplars weak semantic label matching",
         "explicit_negative":"not pretrained SAM3/3D, semantic VLM, independent object mask network",
         "conditions":["distinct","shared_furniture_material","illumination_noise"],
         "cases":[]}
    try:
        validate()
        for case_id,truth in enumerate(TRUTH):
            source={k:render(truth,CAMERAS[k]) for k in range(4)}
            init=bounded(truth+INIT_OFFSETS)
            oracle_model,oracle_cost=optimize(init,source,"object")
            oracle_score=evaluation(oracle_model,truth)
            variants=[]
            for condition in rec["conditions"]:
                observations={}
                segmentation={}
                starts=time.perf_counter()
                for view in TRAIN_VIEWS:
                    gt,depth=source[view]
                    img=modified_rgb(gt,condition,SEED+case_id*100+view)
                    inferred,meta=cluster_mask(img,SEED+case_id*100+view)
                    observations[view]=(inferred,depth)
                    segmentation[str(view)]={"metrics":label_metrics(inferred,gt),**meta}
                    Image.fromarray(img).save(ROOT/f"case{case_id}_{condition}_view{view}_rgb.png")
                    # Labels map: 0 background, 70 sofa,140 chair,210 mannequin.
                    mask=np.where(inferred<0,0,(inferred+1)*70).astype(np.uint8)
                    Image.fromarray(mask).save(ROOT/f"case{case_id}_{condition}_view{view}_inferred_instances.png")
                fit,fit_cost=optimize(init,observations,"object")
                score=evaluation(fit,truth)
                variants.append({"condition":condition,"train_segmentation":segmentation,
                      "fit":{"runtime":fit_cost,"geometry_metrics":score},
                      "total_segmentation_and_fit_seconds":round(time.perf_counter()-starts,4),
                      "source_truth_and_heldout": "heldout geometry/object masks never passed to kmeans/fit"})
                print("CV2_MASK_METHOD="+json.dumps({"scene":case_id,"condition":condition,
                     "mask_mean_iou":round(float(np.mean([x["metrics"]["mean_instance_iou"]
                                  for x in segmentation.values()])),5),
                     "heldout_instance_iou":score["heldout_mean_instance_iou"],
                     "center_rmse_m":score["center_rmse_m"],
                     "time_s":round(time.perf_counter()-starts,4)},sort_keys=True),flush=True)
            rec["cases"].append({"source_case":case_id,
                 "oracle_mask_fit_comparator":{"heldout_geometry":oracle_score,"runtime":oracle_cost},
                 "methods":variants})
        rec["status"]="PASS"
    except BaseException as e:
        rec["error"]={"type":type(e).__name__,"message":str(e)}
        raise
    finally:
        rec["elapsed_wall_seconds"]=round(time.perf_counter()-t0,4)
        rec["peak_rss_kb"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        dest=ROOT/"receipt.json"
        dest.write_text(json.dumps(rec,sort_keys=True,indent=2)+"\n")
        print("CV2_MASK_FINAL="+json.dumps({"status":rec["status"],
           "source_cases":len(rec["cases"]),"wall_s":rec["elapsed_wall_seconds"],
           "peak_rss_kb":rec["peak_rss_kb"],"receipt_sha256":hashlib.sha256(dest.read_bytes()).hexdigest()},sort_keys=True),flush=True)
if __name__=="__main__":
    run()
