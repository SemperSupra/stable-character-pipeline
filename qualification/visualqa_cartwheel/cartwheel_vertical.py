#!/usr/bin/env python3
"""Read-only analytic reachability envelopes for original cartwheel 3D joints.

Find whether one common vertical translation of *both* hips could put both
hip-to-ankle endpoint pairs within anatomical segment-length reach, per frame.
This is NOT an inverse-kinematics correction, pelvis dynamics, full-body balance,
or real cartwheel acceptance. Original contact-foot skate is untouched.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

CASE="female_cartwheel_barefoot"
FAMILY="exercise_pose"
L1,L2=.52,.51
SUM=L1+L2
MIN=abs(L1-L2)
MAX_SHIFT=1.5
EPS=1e-4

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_source(root:Path):
    folder=Path(root)/FAMILY
    manifest=json.loads((folder/"manifest.json").read_text())
    if (manifest.get("schema")!="scp.expanded-original-3d-motion-corpus.v1"
        or manifest.get("rights")!="CC0-1.0 for original generated files"
        or manifest.get("batch")!=FAMILY or manifest.get("frames")!=40
        or manifest.get("fps")!=20):
        raise ValueError("ORIGINAL_SOURCE_MANIFEST_MISMATCH")
    cs=[x for x in manifest.get("cases",[]) if x.get("case")==CASE]
    if len(cs)!=1:
        raise ValueError("CARTWHEEL_CASE_MISSING_OR_DUPLICATE")
    c=cs[0]
    for obj,suffix in ((c["model"],".glb"),(c["ground_truth"],"_ground_truth.json"),(c["videos"][0],"_side.mp4")):
        fn=CASE+suffix
        if obj.get("file")!=fn or sha(folder/fn)!=obj.get("sha256"):
            raise ValueError("CARTWHEEL_ORIGINAL_ASSET_SHA_MISMATCH")
    frames=json.loads((folder/(CASE+"_ground_truth.json")).read_text())["frames"]
    if len(frames)!=40:
        raise ValueError("CARTWHEEL_CLOCK_INCOMPLETE")
    for i,f in enumerate(frames):
        if f.get("frame")!=i:
            raise ValueError("WRONG_FRAME")
        for side in ("left","right"):
            for suffix in ("hip","ankle"):
                a=f["joints"][side+"_"+suffix]
                if len(a)!=3 or any(type(q) not in (float,int) or not math.isfinite(q) for q in a):
                    raise ValueError("INVALID_3D_ENDPOINT")
            if type(f["contact"][side]) is not bool:
                raise ValueError("INVALID_ORIGINAL_CONTACT")
    return frames,c

def shared_vertical_interval(frame,upper:float=SUM-EPS):
    """Exact intersection of two upper-reach 3D closed intervals in delta_z."""
    if upper<=MIN:
        raise ValueError("INVALID_REACH_BOUNDS")
    lo,hi=-MAX_SHIFT,MAX_SHIFT
    byside={}
    for side in ("left","right"):
        h=frame["joints"][side+"_hip"]
        a=frame["joints"][side+"_ankle"]
        transverse=math.hypot(h[0]-a[0],h[1]-a[1])
        if transverse>=upper:
            byside[side]={"horizontal_m":transverse,"interval":None}
            return None,byside
        allowance=math.sqrt(upper*upper-transverse*transverse)
        a_lo=a[2]-h[2]-allowance
        a_hi=a[2]-h[2]+allowance
        byside[side]={"horizontal_m":transverse,"interval":[a_lo,a_hi]}
        lo=max(lo,a_lo);hi=min(hi,a_hi)
    if lo>hi:
        return None,byside
    return [lo,hi],byside

def least_absolute_shift(interval):
    if interval is None:
        return None
    lo,hi=interval
    if lo<=0<=hi:return 0.
    if lo>0:return lo
    return hi

def analyze(root:Path):
    frames,case=load_source(root)
    rows=[]
    unreachable_before=0
    impossible_common=0
    max_needed=0.
    feasible=0
    for i,frame in enumerate(frames):
        old={}
        for side in ("left","right"):
            a=frame["joints"][side+"_hip"];b=frame["joints"][side+"_ankle"]
            d=math.dist(a,b)
            old[side]=d
            unreachable_before+=int(d>SUM+1e-9 or d<MIN-1e-9)
        interval,parts=shared_vertical_interval(frame)
        delta=least_absolute_shift(interval)
        after={}
        if delta is None:
            impossible_common+=1
        else:
            feasible+=1
            max_needed=max(max_needed,abs(delta))
            for side in ("left","right"):
                h=list(frame["joints"][side+"_hip"]);h[2]+=delta
                a=frame["joints"][side+"_ankle"]
                d=math.dist(h,a)
                if d>SUM+1e-6 or d<MIN-1e-6:
                    raise ValueError("ANALYTIC_SHARED_PELVIS_SHIFT_NOT_REACHABLE")
                after[side]=d
        rows.append({"frame":i,"hip_to_ankle_original_m":old,
                     "common_pelvis_vertical_shift_interval_m":interval,
                     "minimum_abs_common_pelvis_shift_m":delta,
                     "hip_to_ankle_after_hypothetical_shift_m":after,
                     "per_leg_transverse_and_shift_intervals":parts,
                     "source_contact":frame["contact"]})
    if unreachable_before!=36:
        raise ValueError("ORIGINAL_CARTWHEEL_36_UNREACHABLE_CONTROL_CHANGED:"+str(unreachable_before))
    return {"schema":"scp.visualqa.cartwheel-common-pelvis-reachability.v1",
            "case":CASE,"source_labels_sha256":case["ground_truth"]["sha256"],
            "original_cartwheel_unreachable_leg_observations":unreachable_before,
            "frames_with_common_vertical_solution":feasible,
            "frames_without_common_vertical_solution":impossible_common,
            "maximum_abs_hypothetical_pelvis_shift_m":max_needed,
            "frames":rows,
            "disposition":"READ_ONLY_HYPOTHESIS_NOT_MOTION_REPAIR",
            "limitations":["Only endpoint reachability; does not update knees, torso, feet or GLB/H264",
                           "Translating hips alone is not a synchronized physically valid articulated pelvis",
                           "No hip/ankle trajectory, landing forces, contact skate, knee pole or real biomechanics acceptance",
                           "Original 36 unreachable and negative controls remain source-immutable"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    d=analyze(Path(a.root))
    out=Path(a.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(d,sort_keys=True,indent=2)+"\n")
    print("CARTWHEEL_COMMON_VERTICAL_PELVIS_ENVELOPE",
          d["original_cartwheel_unreachable_leg_observations"],
          d["frames_with_common_vertical_solution"],
          d["frames_without_common_vertical_solution"],
          d["maximum_abs_hypothetical_pelvis_shift_m"])

if __name__=="__main__":
    main()
