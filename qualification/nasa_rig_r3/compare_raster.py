#!/usr/bin/env python3
"""Observed 2-reader raster overlap for the SAME GLB; not an anatomical oracle.

Compare independent R5 glTF-software-raster (authored glTF source XY) with
R6 native Blender-deformed XZ Pillow-raster of the exact SHA-pinned GLB.
Both readers and both visualizers share a model, so numerical pixel overlap
is only interoperability evidence; zero right to infer physical 3D truth.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from PIL import Image


def mask(path):
    im=Image.open(path).convert("RGB")
    if im.size != (640,360):
        raise ValueError("renderer image dimension mismatch")
    px=im.load()
    # Distinguish cyan skinned geometry in both readers from background/labels.
    # Ignore header/footer annotations and count colored polygons only.
    return {(x,y) for y in range(39,325) for x in range(640)
            if (lambda c: c[0]<150 and c[1]>120 and c[2]>140)(px[x,y])}

def bbox(p):
    return [min(x for x,y in p),min(y for x,y in p),
            max(x for x,y in p),max(y for x,y in p)]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def evaluate(reference,blender,out):
    rows=[]
    for n in range(10):
        a=reference / ("rig_frame_%03d.png" % n)
        b=blender / ("rig_frame_%03d.png" % n)
        if not a.is_file() or not b.is_file():
            raise ValueError("missing one of ten source-chronological raster frames")
        ma,mb=mask(a),mask(b)
        if len(ma)<10 or len(mb)<10:
            raise ValueError("an image has no visible source-bound mesh")
        intersection=len(ma & mb)
        union=len(ma | mb)
        iou=intersection/union
        if not math.isfinite(iou) or iou<=.05:
            raise ValueError("grossly inconsistent independent camera-plane raster")
        rows.append({
          "source_second":13+n,
          "image_index":n,
          "source_reader_png_sha256":digest(a),
          "blender_native_reader_png_sha256":digest(b),
          "glb_reader_colored_pixels":len(ma),
          "blender_colored_pixels":len(mb),
          "intersection_over_union":iou,
          "glb_reader_bounds_px":bbox(ma),
          "blender_bounds_px":bbox(mb),
        })
    vals=[row["intersection_over_union"] for row in rows]
    result={
      "schema":"nasa-r6-cross-reader-raster/1",
      "status":"OBSERVED_TWO_READER_SOURCE_LINKED_RASTER_OVERLAP_NOT_3D_GROUND_TRUTH",
      "source":"same SHA-pinned R5 GLB, 10 source frames (13-22 sec); independent glTF CPU math vs native bpy-evaluated skin",
      "frame_count":len(rows),
      "min_overlap":min(vals),
      "mean_overlap":sum(vals)/len(vals),
      "max_overlap":max(vals),
      "actual_anatomical_3d_accuracy":"NOT_TESTED",
      "actual_model_inference":False,
      "source_identity_inference":False,
      "camera_plane_axis_mapping":"glTF XY, Blender native XZ",
      "method":"cyan source-mesh pixels IoU after excluding text; both draw procedural triangles; not an independent truth oracle",
      "samples":rows,
    }
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("R6_CROSS_READER_RASTER",json.dumps({k:v for k,v in result.items() if k!="samples"},sort_keys=True))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--reference",required=True,type=Path)
    p.add_argument("--blender",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    evaluate(a.reference,a.blender,a.out)
