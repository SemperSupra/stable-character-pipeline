#!/usr/bin/env python3
"""Independent read-only aggregate of genuine image-pixel measurements."""
import json
import math
import sys
from pathlib import Path

VIEWS=("side","oblique")
FRAMES=(12,24)
CANDIDATES=("m060","zero","p060")
def aggregate(folder: Path):
    source=json.loads((folder/"source_receipt.json").read_text())
    if source.get("schema")!="scp.native_neckfit_source.v1" or source.get("source_reference")!="SYNTHETIC_SELF_RENDER_NOT_REAL_PHOTO":
        raise ValueError("unadmitted source receipt")
    if source.get("source_rig_bones")!=26 or source.get("candidate_deltas_radians")!=[-.6,0.,.6]:
        raise ValueError("source topology or sweep mutated")
    rows=[]
    for camera in VIEWS:
      for frame in FRAMES:
        refs=set()
        for candidate in CANDIDATES:
          p=folder/f"measurement_{camera}_f{frame}_{candidate}.json"
          d=json.loads(p.read_text())
          expected=f"pony_fit_{camera}_f{frame}_{candidate}"
          if d.get("schema")!="scp.render_mask_metrics.v1" or d.get("experiment_id")!=expected:
             raise ValueError("measurement ID/schema mismatch")
          if d.get("camera_id")!=camera or d.get("frame_index")!=frame or d.get("subject_class")!="public_original_synthetic_equine":
             raise ValueError("camera/frame/source mismatch")
          if d.get("split")!="heldout" or d.get("source_attestation")!="UNAUTHENTICATED_SPLIT_AND_CAMERA_METADATA":
             raise ValueError("unqualified or false attestation")
          if d.get("verdict")!="MEASURED_ONLY_NOT_ANATOMICAL_ACCEPTANCE":
             raise ValueError("unexpected disposition")
          if d.get("width")!=256 or d.get("height")!=256 or d.get("reference_foreground_pixels",0)<1000:
             raise ValueError("invalid source image dimensions/foreground")
          for key in ["reference_sha256","baseline_image_sha256","candidate_image_sha256","baseline_sha256","candidate_sha256"]:
             h=d.get(key)
             if not isinstance(h,str) or len(h)!=64 or any(c not in "0123456789abcdef" for c in h):
                raise ValueError("unverified hash field")
          for key in ["baseline","candidate"]:
             m=d.get(key,{})
             inter=m.get("intersection_pixels",-1); union=m.get("union_pixels",-1)
             iou=m.get("iou",-1.)
             if inter<0 or union<=0 or inter>union or not math.isfinite(iou) or abs(iou-inter/union)>1e-12:
                raise ValueError("invalid numerical IoU witness")
          refs.add(d["reference_sha256"])
          rows.append({"camera":camera,"frame":frame,"candidate":candidate,
                       "reference_sha256":d["reference_sha256"],
                       "baseline_iou":d["baseline"]["iou"],
                       "candidate_iou":d["candidate"]["iou"]})
        if len(refs)!=1:raise ValueError("candidate references disagree for fixed view/frame")
    if len(rows)!=len(VIEWS)*len(FRAMES)*len(CANDIDATES):
        raise ValueError("missing camera/frames")
    means={x:sum(row["candidate_iou"] for row in rows if row["candidate"]==x)/4 for x in CANDIDATES}
    baseline=sum(row["baseline_iou"] for row in rows if row["candidate"]=="zero")/4
    if means["zero"]<.999999 or means["zero"]<=means["m060"]+1e-4 or means["zero"]<=means["p060"]+1e-4:
        raise ValueError("known synthetic reference candidate failed blinded sweep")
    if means["zero"]-baseline<.005:
        raise ValueError("no measured correction over baseline")
    return {"schema":"scp.native_multiview_neckfit.v1",
            "subject":"public_original_synthetic_equine",
            "model_source_sha256":source["source_blend_sha256"],
            "camera_count":2,"frames":[12,24],
            "candidate_angles_radians":{"m060":-.6,"zero":0.,"p060":.6},
            "mean_iou_by_candidate":means,"baseline_mean_iou":baseline,
            "best_candidate":"zero","measured_gain":means["zero"]-baseline,
            "per_view_frame":rows,
            "physical_anatomy":"UNKNOWN",
            "external_photo_fit":"NOT_RUN",
            "reasoning_model_inference":"NOT_RUN",
            "reference_kind":"SYNTHETIC_SELF_RENDER",
            "disposition":"ENGINEERING_MULTI_VIEW_FIT_PASS_SCIENCE_UNKNOWN"}
if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: verify_fit.py folder")
    try:result=aggregate(Path(sys.argv[1]))
    except (ValueError,KeyError,TypeError,OSError) as exc:
      raise SystemExit("REJECT_MISSING_OR_INVALID_MEASUREMENT: "+str(exc))
    print(json.dumps(result,indent=2,sort_keys=True))
