#!/usr/bin/env python3
"""Source-known Gaussian radiance parameter sensitivity vs exact native mesh.

15-point opacity-logit × anisotropic uniform scale-factor DOE, with explicit
training-view selection and unseen pose/view/paint interventions. No neural
model inference, reconstruction learning or equivalent-PBR claim.
"""
import hashlib
import itertools
import json
import math
import os
import struct
import sys
from pathlib import Path

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parent))
# Shared Blender render collector must write into the same R2 evidence directory.
os.environ["BAKEOFF_OUT"]=os.environ.get("BAKEOFF_R2_OUT","out/gsplat53-r2")
from rig_fixture import FIELDS, gaussian_rows, ply_bytes
from virtual_rig_r1 import ROOT, reset_world, put_mesh, take_image, compare_pair, camera_record

SCHEMA="gaussian-parameter-doe-r2/v1"
SCALES=(0.55,0.75,1.0,1.25,1.6)
OPACITY_LOGITS=(1.5,3.0,4.0)
BASELINE=(1.0,4.0)
# Train-only selection. Heldout data cannot influence the chosen treatment.
SCENES=(
 ("train",0,"base","front"),
 ("holdout_pose",90,"base","front"),
 ("holdout_view_pose",45,"base","oblique_holdout"),
 ("holdout_edit_view_pose",45,"repaint","oblique_holdout"),
)
OUT=Path(os.environ.get("BAKEOFF_R2_OUT","out/gsplat53-r2")).resolve()
OUT.mkdir(parents=True,exist_ok=True)

def sha(blob): return hashlib.sha256(blob).hexdigest()

def treatment_ply(pose,paint,scale_factor,opacity_logit):
    if not(scale_factor>0 and math.isfinite(scale_factor) and math.isfinite(opacity_logit)):
        raise ValueError("invalid scale/opacity")
    source=ply_bytes(pose,paint)
    head,sep,body=source.partition(b"end_header\n")
    if not sep: raise ValueError("missing PLY terminator")
    rows=list(struct.iter_unpack("<17f",body))
    if len(rows)!=204: raise ValueError("wrong PLY primitive count")
    out=bytearray()
    log_scale=math.log(scale_factor)
    for row in rows:
        r=list(row)
        r[9]=opacity_logit
        for i in range(10,13):
            r[i]+=log_scale
        if any(not math.isfinite(f) for f in r):
            raise ValueError("nonfinite Gaussian field")
        if abs(sum(q*q for q in r[13:17])-1)>1e-5:
            raise ValueError("quaternion corruption")
        out.extend(struct.pack("<17f",*r))
    result=head+sep+bytes(out)
    if (scale_factor,opacity_logit)==BASELINE and result!=source:
        raise AssertionError("baseline treatment changed raw source PLY")
    return result

def source_controls():
    base=treatment_ply(0,"base",*BASELINE)
    assert base==ply_bytes(0,"base")
    for factor in (0.,-1.,float("nan"),float("inf")):
        try: treatment_ply(0,"base",factor,4.)
        except ValueError: pass
        else: raise AssertionError(f"bad scale accepted {factor}")
    for logit in (float("inf"),float("nan")):
        try: treatment_ply(0,"base",1.,logit)
        except ValueError: pass
        else: raise AssertionError(f"bad logit accepted {logit}")
    assert len(set(sha(treatment_ply(0,"base",s,o))
                   for s,o in itertools.product(SCALES,OPACITY_LOGITS)))==len(SCALES)*len(OPACITY_LOGITS)
    print("R2_SOURCE_CONTROLS=PASS: baseline immutable, invalid scaling/opacities rejected, all treatments unique")

def put_splats(pose,paint,scale_factor,opacity_logit,role):
    raw=treatment_ply(pose,paint,scale_factor,opacity_logit)
    path=OUT/f"source_{role}_s{scale_factor:g}_o{opacity_logit:g}.ply"
    path.write_bytes(raw)
    existing={x.name for x in bpy.data.objects}
    bpy.ops.wm.ply_import(filepath=str(path))
    imported=[x for x in bpy.data.objects if x.name not in existing]
    if len(imported)!=1 or imported[0].type!="POINTCLOUD":
        raise AssertionError(f"wrong importer type: {[(x.name,x.type) for x in imported]}")
    pc_type=str(getattr(imported[0].data,"type","none"))
    if pc_type!="GAUSSIAN_SPLAT": raise AssertionError("not native Gaussian splat")
    return sha(raw)

def compare_treatment(ref,alternative):
    metric=compare_pair(ref,alternative)
    if not all(math.isfinite(x) for k,x in metric.items() if k!="interpretation"):
        raise AssertionError("nonfinite image comparison")
    return {"iou":metric["binary_alpha_iou"],
            "rgb_l1":metric["mean_abs_rgb"],
            "alpha_l1":metric["mean_abs_alpha"]}


def read_rgba(path):
    image=bpy.data.images.load(str(path),check_existing=False)
    try:
        w,h=image.size
        if (w,h)!=(96,96):raise AssertionError("unexpected audit image dimensions")
        px=image.pixels[:]
        rgb=[(px[i],px[i+1],px[i+2]) for i in range(0,len(px),4)]
        alpha=[px[i+3] for i in range(0,len(px),4)]
        return w,h,rgb,alpha
    finally:
        bpy.data.images.remove(image)

def visual_tradeoff_audit(role,treatment,selected):
    """Independent interior quality check: silhouette IoU can hide pinholes."""
    if treatment=="baseline":name=f"gs_{role}_s1_o4.png"
    elif treatment=="selected":
        name=f"gs_{role}_s{selected[0]:g}_o{selected[1]:g}.png"
    elif treatment=="mesh":name=f"mesh_{role}.png"
    else:raise ValueError(treatment)
    w,h,rgb,alpha=read_rgba(OUT/name)
    _,_,_,reference_alpha=read_rgba(OUT/f"mesh_{role}.png")
    target=[v>.15 for v in reference_alpha]
    interior=set()
    for y in range(2,h-2):
        for x in range(2,w-2):
            if all(target[(y+dy)*w+x+dx] for dy in range(-2,3) for dx in range(-2,3)):
                interior.add(y*w+x)
    if not interior:raise AssertionError("reference silhouette has no 5x5-eroded interior")
    a=[alpha[idx] for idx in interior]
    total_variation=0.
    num_edges=0
    for idx in interior:
        for adj in (idx+1,idx+w):
            if adj in interior:
                total_variation+=sum(abs(rgb[idx][j]-rgb[adj][j]) for j in range(3))/3.
                num_edges+=1
    if num_edges==0:raise AssertionError("no adjacent interior pixels")
    fp=sum(1 for i,b in enumerate(target) if not b and alpha[i]>.15)
    fn=sum(1 for i,b in enumerate(target) if b and alpha[i]<=.15)
    result={"role":role,"treatment":treatment,"interior_pixels":len(interior),
            "mean_interior_alpha":round(sum(a)/len(a),6),
            "fraction_interior_alpha_below_0_9":round(sum(v<.9 for v in a)/len(a),6),
            "mean_interior_rgb_neighbor_abs_gradient":round(total_variation/num_edges,6),
            "source_silhouette_false_positive_pixels":fp,
            "source_silhouette_false_negative_pixels":fn}
    if not all(math.isfinite(v) for v in result.values() if isinstance(v,(float,int))):
        raise AssertionError("nonfinite image QA data")
    return result

def main():
    if bpy.app.version[:2]!=(5,3): raise RuntimeError("requires Blender 5.3")
    source_controls()
    rec={"schema":SCHEMA,"status":"FAIL","head_sha":os.getenv("PR_HEAD",os.getenv("GITHUB_SHA","LOCAL")),
         "build_sha":os.getenv("GITHUB_SHA","LOCAL"),"blender":bpy.app.version_string,
         "metric":"binary alpha silhouette IoU, alpha threshold=0.15; source mesh is immutable ground truth",
         "parameters":{"scales":SCALES,"opacity_logits":OPACITY_LOGITS,"baseline":BASELINE,
                       "number_treatments":len(SCALES)*len(OPACITY_LOGITS)},
         "selection_rule":"maximize only training-front-pose0 IoU, break ties by lower training alpha L1",
         "scenes":[{"role":r,"pose":p,"paint":col,"view":view} for r,p,col,view in SCENES],
         "trials":[],"camera_receipts":{}}
    try:
        source_mesh_images={}
        all_results={}
        for role,pose,paint,view in SCENES:
            s,cam=reset_world(view)
            put_mesh(pose,paint)
            native,native_pixels=take_image(s,f"mesh_{role}")
            source_mesh_images[role]=native_pixels
            rec["camera_receipts"][role]=camera_record(cam)
            rec["trials"].append({"role":role,"representation":"canonical_mesh",**native})
            for sf,logit in itertools.product(SCALES,OPACITY_LOGITS):
                scene,_=reset_world(view)
                digest=put_splats(pose,paint,sf,logit,role)
                label=f"gs_{role}_s{sf:g}_o{logit:g}"
                rendered,px=take_image(scene,label)
                m=compare_treatment(native_pixels,px)
                rec["trials"].append({"role":role,"representation":"source_derived_gaussian",
                    "scale_factor":sf,"opacity_logit":logit,"source_ply_sha256":digest,
                    **m,**rendered})
                all_results[(role,sf,logit)]=m
            if role=="train":
                train=[(all_results[("train",sf,logit)]["iou"],
                        -all_results[("train",sf,logit)]["alpha_l1"],sf,logit)
                       for sf,logit in itertools.product(SCALES,OPACITY_LOGITS)]
                train.sort(reverse=True)
                _,_,chosen_scale,chosen_logit=train[0]
                chosen=(chosen_scale,chosen_logit)
                rec["selection"]={"selected_scale_factor":chosen_scale,
                                   "selected_opacity_logit":chosen_logit,
                                   "selected_on":"train only","baseline":BASELINE,
                                   "train_metrics_selected":all_results[("train",*chosen)],
                                   "train_metrics_baseline":all_results[("train",*BASELINE)]}
                if rec["selection"]["train_metrics_selected"]["iou"] + 1e-6 < rec["selection"]["train_metrics_baseline"]["iou"]:
                    raise AssertionError("train-selected candidate has lower IoU than frozen baseline")
        rec["holdout_comparisons"]=[]
        for role,*_ in SCENES[1:]:
            x=all_results[(role,*chosen)]
            b=all_results[(role,*BASELINE)]
            rec["holdout_comparisons"].append({"role":role,"selected":x,"baseline":b,
                "delta_iou":round(x["iou"]-b["iou"],5),
                "delta_alpha_l1":round(x["alpha_l1"]-b["alpha_l1"],6)})
        rec["independent_visual_quality"]=[
            visual_tradeoff_audit(role,treatment,chosen)
            for role,_,_,_ in SCENES
            for treatment in ("mesh","baseline","selected")
        ]
        rec["summary"]={
            "actual_renders":len(rec["trials"]),"target_mesh_renders":len(SCENES),
            "gaussian_renders":len(rec["trials"])-len(SCENES),
            "unique_param_treatments":len(train),
            "train_iou_gain":round(rec["selection"]["train_metrics_selected"]["iou"]-
                                   rec["selection"]["train_metrics_baseline"]["iou"],5),
            "holdout_iou_delta_min":min(x["delta_iou"] for x in rec["holdout_comparisons"]),
            "holdout_iou_delta_mean":round(sum(x["delta_iou"] for x in rec["holdout_comparisons"])/3,5),
            "no_canonical_change":True,
            "scientific_nonclaim":"No model fitting, perspective GS reconstruction, PBR equivalence, human rigs or generalization across scenes"
        }
        if len(rec["trials"])!=64: raise AssertionError("missing treatment/camera combinations")
        if len(rec["holdout_comparisons"])!=3:raise AssertionError("missing heldouts")
        rec["status"]="PASS"
    except BaseException as e:
        rec["error"]={"type":type(e).__name__,"message":str(e)}
        raise
    finally:
        (OUT/"receipt.json").write_text(json.dumps(rec,sort_keys=True,indent=2)+"\n")
        small={k:v for k,v in rec.items() if k not in ("trials","camera_receipts")}
        print("R2_GAUSSIAN_DOE_SUMMARY="+json.dumps(small,sort_keys=True),flush=True)
    return 0

if __name__=="__main__":
    sys.exit(main())
