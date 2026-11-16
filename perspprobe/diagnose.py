#!/usr/bin/env python3
"""Failure-only R057 counterfactual diagnostic; NEVER an acceptance oracle.

All inputs are original synthetic test renders. Print observed pixel/source
mismatch classes. Do not auto-select a replacement projection or fit offsets.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np

import audit


def summarize(root):
    manifest=audit.ortho.strict_json(root/"r057_source_manifest.json")
    cases=audit.validate_manifest(manifest)
    result={"schema":"r057.perspective.first-red.v1",
            "status":"DIAGNOSTIC_ONLY_NO_ACCEPTANCE",
            "rights":"ORIGINAL_SYNTHETIC",
            "cases":{}}
    for label,case in sorted(cases.items()):
        rays=[r for r in case["rays"] if r["stable"]]
        if not rays:continue
        lens=case["camera"]["lens_mm"]
        by_arm={}
        for arm in ("baseline","physical_material"):
            pix,summary=audit.pixel_decode.decode(root/label/arm/"render_passes.exr")
            d=pix["depth"]["Z"]
            ob=pix["object"]["X"]
            candidates=[]
            # Predeclared diagnostic *only* tests: inverse-Y pixel convention,
            # one-pixel center offset, and camera-axis vs ray-length Z.
            transformations=[
              ("native",lambda x,y:(x,y)),
              ("vertical_flip",lambda x,y:(x,255-y)),
              ("horizontal_flip",lambda x,y:(255-x,y)),
              ("both_flip",lambda x,y:(255-x,255-y)),
              ("x_plus_one",lambda x,y:(min(255,x+1),y)),
              ("y_plus_one",lambda x,y:(x,min(255,y+1))),
              ("y_minus_one",lambda x,y:(x,max(0,y-1))),
            ]
            for name,transform in transformations:
                for depth_mode in ("ray_distance","camera_axis"):
                    total=0;correct=0;index_bad=0;depth_bad=0
                    finite_deltas=[];signed=[];samples=[]
                    for r in rays:
                        x,y=transform(r["x"],r["y"])
                        z=float(d[y,x])
                        idx=float(ob[y,x])
                        expected=(r["camera_axis_depth"] if depth_mode=="camera_axis"
                                  else r["ray_distance"])
                        delta=z-expected
                        idx_bad=not math.isfinite(idx) or abs(idx-r["pass_index"])>0.01
                        z_bad=not math.isfinite(delta) or abs(delta)>0.05
                        index_bad+=int(idx_bad)
                        depth_bad+=int(z_bad)
                        if not idx_bad and not z_bad:correct+=1
                        if math.isfinite(delta):
                            finite_deltas.append(abs(delta))
                            signed.append(delta)
                        if len(samples)<5:
                            samples.append({"source_pixel":[r["x"],r["y"]],
                                            "sample_pixel":[x,y],"source_object":r["pass_index"],
                                            "actual_index":idx if math.isfinite(idx) else None,
                                            "source_depth":expected,
                                            "actual_exr_depth":z if math.isfinite(z) else None,
                                            "signed_error":delta if math.isfinite(delta) else None})
                        total+=1
                    candidates.append({
                        "mapping":name,
                        "hypothesis":depth_mode,
                        "sample_count":total,
                        "joint_matches":correct,
                        "source_object_index_mismatches":index_bad,
                        "depth_beyond_original_0p05":depth_bad,
                        "median_abs_depth_delta":float(np.median(finite_deltas)) if finite_deltas else None,
                        "median_signed_depth_delta":float(np.median(signed)) if signed else None,
                        "p95_abs_depth_delta":float(np.quantile(finite_deltas,.95)) if finite_deltas else None,
                        "first_samples":samples
                    })
            by_arm[arm]=sorted(candidates,key=lambda z:(-z["joint_matches"],z["median_abs_depth_delta"] if z["median_abs_depth_delta"] is not None else float('inf')))[:7]
        result["cases"][label]=by_arm
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=summarize(args.root)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    for case,arms in result["cases"].items():
        for arm,rows in arms.items():
            print("R057_PERSPECTIVE_DIAGNOSTIC_ONLY",case,arm,
                  [(r["mapping"],r["hypothesis"],r["joint_matches"],r["sample_count"],
                    r["median_abs_depth_delta"]) for r in rows[:4]],flush=True)
