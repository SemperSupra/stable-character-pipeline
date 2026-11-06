#!/usr/bin/env python3
"""R009 geometry QA: distribution of nearest-body-vertex distances.

This is NOT true triangle intersection, gap closure, penetration, physics,
contact, apparel fit, anatomical validation or a release criterion.
"""
import math

SCHEMA="scp.r009.garment_body_vertex_proximity_proxy.v1"

def summarize(distances):
    values=sorted(float(d) for d in distances)
    if not values:
        raise ValueError("PROXIMITY_INPUT_EMPTY")
    if not all(math.isfinite(x) and x>=0 for x in values):
        raise ValueError("PROXIMITY_INPUT_NONFINITE_OR_NEGATIVE")
    def percentile(frac):
        pos=(len(values)-1)*frac
        low=int(pos);high=min(low+1,len(values)-1)
        return values[low]*(1-(pos-low))+values[high]*(pos-low)
    return {"sample_count":len(values),"min_m":values[0],
            "p10_m":percentile(.1),"p50_m":percentile(.5),
            "p90_m":percentile(.9),"max_m":values[-1],
            "near_2cm_ratio":sum(x<=.02 for x in values)/len(values),
            "far_10cm_ratio":sum(x>.10 for x in values)/len(values),
            "metric":"NEAREST_BODY_VERTEX_DISTANCE_NOT_SURFACE_COLLISION",
            "penetration_qualified":False,
            "fit_accepted":False}
