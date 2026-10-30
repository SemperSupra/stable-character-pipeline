"""W13 independent stdlib Python numeric oracle for original-only 3D two-bone geometry.
Not an import of or call into Go implementation, Blender, Ozz or Three.js.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

def sqr_distance(a,b):
    return sum((float(x)-float(y))**2 for x,y in zip(a,b))

def normalized(vec):
    length=math.sqrt(sum(x*x for x in vec))
    if length<=1e-8 or not math.isfinite(length):
        raise ValueError("SINGULAR_POLE_OR_TARGET")
    return [x/length for x in vec]

def displacement(a,b):
    return [float(y)-float(x) for x,y in zip(a,b)]

def scalar(a,b):
    return sum(x*y for x,y in zip(a,b))

def compute(case):
    start=case["start"];destination=case["target"];pole=case["pole"]
    upper=float(case["upper"]);lower=float(case["lower"]);margin=float(case["soften_margin"])
    if len(start)!=3 or len(destination)!=3 or len(pole)!=3:
        raise ValueError("BAD_VECTOR_DIMENSION")
    numbers=[*start,*destination,*pole,upper,lower,margin]
    if not all(type(n) in (int,float) and math.isfinite(n) for n in numbers):
        raise ValueError("NONFINITE_SOURCE")
    if min(upper,lower,margin)<=0 or margin>=min(upper,lower)/4:
        raise ValueError("INVALID_LIMB_OR_MARGIN")
    target_vector=displacement(start,destination)
    target_distance=math.sqrt(scalar(target_vector,target_vector))
    if target_distance<1e-10:
        raise ValueError("ZERO_TARGET_DIRECTION")
    if target_distance<=abs(upper-lower)+1e-8:
        raise ValueError("INNER_REACH_UNAVAILABLE")
    axis=[v/target_distance for v in target_vector]
    pole_offset=displacement(start,pole)
    pole_component=scalar(axis,pole_offset)
    sideways=[pole_offset[i]-axis[i]*pole_component for i in range(3)]
    side=normalized(sideways)
    max_reach=upper+lower-margin
    if max_reach<=abs(upper-lower)+1e-8:
        raise ValueError("INVALID_REACH_ENVELOPE")
    actual_range=min(target_distance,max_reach)
    end=[start[i]+actual_range*axis[i] for i in range(3)]
    knee_axis=(upper*upper-lower*lower+actual_range*actual_range)/(2*actual_range)
    vertical=max(0.0,upper*upper-knee_axis*knee_axis)**.5
    knee=[start[i]+axis[i]*knee_axis+side[i]*vertical for i in range(3)]
    residual_upper=abs(math.sqrt(sqr_distance(start,knee))-upper)
    residual_lower=abs(math.sqrt(sqr_distance(knee,end))-lower)
    pole_side=scalar(displacement(start,knee),side)
    if residual_upper>1e-8 or residual_lower>1e-8 or pole_side<=0:
        raise ValueError("INVALID_GEOMETRY_RESULT")
    reached=target_distance<=max_reach
    return {"id":case["id"],"status":"REACHED" if reached else "SOFTENED_UNREACHABLE",
            "reached":reached,"start":start,"knee":knee,"end":end,
            "target":destination,"effective_target":end,
            "upper_residual":residual_upper,"lower_residual":residual_lower,
            "target_gap":math.sqrt(sqr_distance(destination,end)),
            "pole_side":pole_side}

def process(source):
    doc=json.loads(source)
    if (doc.get("schema")!="scp.ik3d.fixtures.v1" or
        doc.get("source_rights")!="ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY" or
        doc.get("coordinate_basis")!="RIGHT_HANDED_XYZ_Y_UP_UNCALIBRATED" or
        doc.get("units")!="SOURCE_SCENE_UNCALIBRATED" or
        doc.get("algorithm")!="ANALYTIC_3D_TWO_SEGMENT_POLE_SELECTED_NO_JOINT_LIMITS"):
        raise ValueError("UNADMITTED_ORIGINAL_3D_SOURCE")
    cases=doc["cases"]
    if len(cases)!=5 or len(set(c["id"] for c in cases))!=5:
        raise ValueError("INVALID_CASE_SET")
    return {"schema":"scp.ik3d.receipt.v1","source_rights":doc["source_rights"],
            "coordinate_basis":doc["coordinate_basis"],
            "source_sha256":hashlib.sha256(source).hexdigest(),
            "algorithm":doc["algorithm"],"solver":"PYTHON_INDEPENDENT_NUMERIC_3D",
            "cases":[compute(c) for c in cases]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source",required=True)
    ap.add_argument("--out",required=True)
    p=ap.parse_args()
    raw=Path(p.source).read_bytes()
    packet=process(raw)
    Path(p.out).write_text(json.dumps(packet,indent=2,sort_keys=True)+"\n")
    print("W13_PYTHON_INDEPENDENT_3D_IK_PASS",len(packet["cases"]),packet["source_sha256"])
if __name__=="__main__":main()
