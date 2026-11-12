#!/usr/bin/env python3
"""Read-only temporal reachability for original cartwheel, NOT a motion repair.

Given source-SHA-bound framewise feasible vertical pelvis shift intervals from
#426, compute the exact smallest per-frame Lipschitz speed necessary for any
continuous sample-to-sample root translation. Verify via forward interval
reachability and construct a *hypothetical* witness without modifying a joint,
source label, mesh, video, threshold, or production evaluator.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = "scp.visualqa.cartwheel-temporal-lipschitz-envelope.v1"
INPUT_SCHEMA = "scp.visualqa.cartwheel-common-pelvis-reachability.v1"
CASE = "female_cartwheel_barefoot"
SOURCE_SHA = "d0f69142801e3c66aabcf79e1787e349f5bdb54bc8e966040f7e5e50dc5f5548"
FPS = 20
FRAME_COUNT = 40

def validate_intervals(intervals: list):
    if len(intervals) != FRAME_COUNT:
        raise ValueError("FRAME_COUNT_MISMATCH")
    for a in intervals:
        if not isinstance(a, list) or len(a) != 2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in a):
            raise ValueError("UNTRUSTWORTHY_3D_FEASIBILITY_INTERVAL")
        if a[0] > a[1] or a[0] < -1.5-1e-9 or a[1] > 1.5+1e-9:
            raise ValueError("INVALID_ROOT_SHIFT_INTERVAL")

def exact_pairwise_min_speed(intervals: list[list[float]], fps: int = FPS):
    """Sharp 1D Lipschitz selection bound, maximum disjoint interval gap / dt."""
    if fps <= 0:
        raise ValueError("INVALID_SAMPLE_RATE")
    bound=0.
    witness=None
    for i,a in enumerate(intervals):
        for j in range(i+1,len(intervals)):
            b=intervals[j]
            gap=max(0., b[0]-a[1], a[0]-b[1])
            required=gap*fps/(j-i)
            if required>bound:
                bound=required
                witness={"from_frame":i,"to_frame":j,"gap_m":gap,
                         "time_s":(j-i)/fps,"required_speed_m_s":required}
    return bound,witness

def forward_intervals(intervals: list[list[float]], speed_m_s:float, fps:int=FPS):
    if speed_m_s<0 or not math.isfinite(speed_m_s) or fps<=0:
        raise ValueError("INVALID_SPEED_CAP")
    reach=[intervals[0][:]]
    delta=speed_m_s/fps
    for low,high in intervals[1:]:
        lo=max(low,reach[-1][0]-delta)
        hi=min(high,reach[-1][1]+delta)
        if lo>hi+1e-10:
            return None
        if lo>hi:lo=hi
        reach.append([lo,hi])
    return reach

def reconstruct(intervals:list[list[float]],speed_m_s:float):
    reach=forward_intervals(intervals,speed_m_s)
    if reach is None:
        raise ValueError("NO_SPEED_BOUNDED_ROOT_SHIFT")
    out=[0.]*len(reach)
    last=reach[-1]
    out[-1]=min(max(0.,last[0]),last[1])
    d=speed_m_s/FPS
    for i in range(len(reach)-2,-1,-1):
        low=max(reach[i][0],out[i+1]-d)
        high=min(reach[i][1],out[i+1]+d)
        if low>high+1e-10:
            raise ValueError("BACKWARD_WITNESS_NOT_FEASIBLE")
        if low>high:low=high
        out[i]=min(max(0.,low),high)
    for i,(v,interval) in enumerate(zip(out,intervals)):
        if v<interval[0]-1e-8 or v>interval[1]+1e-8:
            raise ValueError("ROOT_SHIFT_OUTSIDE_FRAME_INTERVAL")
        if i and abs(v-out[i-1])*FPS > speed_m_s+1e-7:
            raise ValueError("ROOT_SHIFT_TOO_FAST")
    return out

def evaluate(original_receipt:dict,receipt_sha:str):
    if (original_receipt.get("schema")!=INPUT_SCHEMA
        or original_receipt.get("case")!=CASE
        or original_receipt.get("source_labels_sha256")!=SOURCE_SHA
        or original_receipt.get("original_cartwheel_unreachable_leg_observations")!=36
        or original_receipt.get("frames_with_common_vertical_solution")!=FRAME_COUNT
        or original_receipt.get("frames_without_common_vertical_solution")!=0
        or original_receipt.get("disposition")!="READ_ONLY_HYPOTHESIS_NOT_MOTION_REPAIR"):
        raise ValueError("SOURCE_AUTHORITY_OR_NEGATIVE_CONTROL_CHANGED")
    rows=original_receipt.get("frames")
    if not isinstance(rows,list) or len(rows)!=FRAME_COUNT or any(row.get("frame")!=i for i,row in enumerate(rows)):
        raise ValueError("FRAME_CLOCK_OR_ORDER_CHANGED")
    intervals=[row.get("common_pelvis_vertical_shift_interval_m") for row in rows]
    validate_intervals(intervals)
    lo,hi=max(x[0] for x in intervals),min(x[1] for x in intervals)
    static_possible=(lo<=hi)
    limit,critical=exact_pairwise_min_speed(intervals)
    forward=forward_intervals(intervals,limit+1e-8)
    if forward is None:
        raise AssertionError("PAIRWISE_BOUND_DISAGREES_WITH_FORWARD_REACHABILITY")
    if limit>1e-6 and forward_intervals(intervals,limit-1e-6) is not None:
        raise AssertionError("UNEXPECTED_FEASIBILITY_BELOW_SHARP_SPEED_BOUND")
    witness=reconstruct(intervals,limit+1e-8)
    speeds=[abs(witness[i]-witness[i-1])*FPS for i in range(1,FRAME_COUNT)]
    return {"schema":SCHEMA,
            "original_source_labels_sha256":SOURCE_SHA,
            "source_parent_receipt_sha256":receipt_sha,
            "original_unreachable_observations":36,
            "frames_checked":FRAME_COUNT,"fps":FPS,
            "one_constant_vertical_shift_feasible":static_possible,
            "common_static_shift_interval_m":[lo,hi] if static_possible else None,
            "exact_minimum_sampled_root_shift_speed_m_s":limit,
            "limiting_frame_pair":critical,
            "hypothetical_root_delta_z_by_frame_m":witness,
            "witness_max_sampled_speed_m_s":max(speeds),
            "witness_max_abs_pelvis_shift_m":max(abs(x) for x in witness),
            "disposition":"READ_ONLY_TEMPORAL_REACHABILITY_NOT_MOTION_REPAIR",
            "limitations":[
              "Only 3D hip-to-ankle two-link upper reach with per-frame common pelvis vertical translation",
              "A Lipschitz bound on sampled shifts does not establish velocity continuity, acceleration limits, dynamic feasibility, whole-body orientation, or knee IK",
              "Does not change source GLB/H264, source labels or judge thresholds; all 36 unreachable original observations remain original failures",
              "No foot contact, collision, mass-center, ground-reaction-force, video realism, anatomy or stable identity acceptance"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--parent-receipt",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    raw=Path(a.parent_receipt).read_bytes()
    if not raw or len(raw)>5_000_000: raise ValueError("PARENT_RECEIPT_TOO_LARGE_OR_EMPTY")
    result=evaluate(json.loads(raw),hashlib.sha256(raw).hexdigest())
    out=Path(a.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("CARTWHEEL_TEMPORAL_LIPSCHITZ_BOUND",
          result["one_constant_vertical_shift_feasible"],
          round(result["exact_minimum_sampled_root_shift_speed_m_s"],8),
          round(result["witness_max_abs_pelvis_shift_m"],8))

if __name__=="__main__":
    main()
