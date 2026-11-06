"""Offline diagnostic for sampled pony longhair displacement-clamp damage.

Quality screen only, not hair contact, wind realism, or anatomy acceptance.
Input: (frame, guide id, mane/forelock/tail region, raw meters) per baked key.
"""
import hashlib
import json
import math

SCHEMA = "equine.longhair.clamp_quality.v1"
REGIONS = ("mane", "forelock", "tail")

def report(samples, *, frames=(1, 7, 13, 19, 25, 31, 37, 43, 48),
           guide_count=114, cap_m=0.22):
    if type(guide_count) is not int or not 1 <= guide_count <= 10000:
        raise ValueError("invalid guide count")
    if type(frames) not in (tuple,list) or not 1 <= len(frames) <= 240 or any(
            type(f) is not int or not 1 <= f <= 240 for f in frames):
        raise ValueError("invalid frame selection")
    if tuple(sorted(set(frames))) != tuple(frames):
        raise ValueError("duplicate/unsorted frames")
    if type(cap_m) not in (float,int) or not math.isfinite(cap_m) or not .001 <= cap_m <= 1.:
        raise ValueError("invalid displacement cap")
    if type(samples) is not list or len(samples) != len(frames) * guide_count:
        raise ValueError("incomplete/excessive guide-frame samples")
    by_region = {r:[] for r in REGIONS}
    seen=set()
    canonical=[]
    for row in samples:
        if type(row) not in (tuple,list) or len(row)!=4:
            raise ValueError("invalid sample shape")
        frame,guide,region,value=row
        if type(frame) is not int or frame not in frames or type(guide) is not int or not 0 <= guide < guide_count:
            raise ValueError("out-of-range source sample")
        if region not in REGIONS or type(value) not in (int,float) or not math.isfinite(value) or value<0 or value>100:
            raise ValueError("invalid region or displacement")
        key=(frame,guide)
        if key in seen:raise ValueError("duplicate guide/frame")
        seen.add(key)
        by_region[region].append(float(value))
        canonical.append((frame,guide,region,round(float(value),9)))
    if len(seen)!=len(frames)*guide_count:raise ValueError("incomplete guide/frame matrix")
    canonical.sort()
    def metrics(values):
        if not values:return {"count":0,"verdict":"NO_SAMPLES_ABSTAIN"}
        values=sorted(values);n=len(values);count=sum(x>cap_m for x in values)
        excess=[max(0.,x-cap_m) for x in values];fraction=count/n
        return {"count":n,"saturated_count":count,"saturated_fraction":round(fraction,6),
            "p50_m":round(values[(n-1)//2],6),"p95_m":round(values[math.ceil(.95*n)-1],6),
            "p99_m":round(values[math.ceil(.99*n)-1],6),"max_raw_m":round(values[-1],6),
            "max_lost_m":round(max(excess),6),"mean_lost_m":round(sum(excess)/n,6),
            "verdict":("QUALITY_RED_CLAMP_DOMINATED" if fraction>.05 else
                       "REVIEW_SATURATION" if count else "NO_CLAMP_IN_SAMPLES_ONLY")}
    groups={r:metrics(v) for r,v in by_region.items()}
    overall=metrics([v for values in by_region.values() for v in values])
    digest=hashlib.sha256(json.dumps(canonical,separators=(",",":"),ensure_ascii=True).encode("ascii")).hexdigest()
    return {"schema":SCHEMA,"scope":"raw guide-tip deltas at baked GLB morph keyframes only",
            "sample_frames":list(frames),"guides":guide_count,"clamp_m":cap_m,
            "source_samples_sha256":digest,"overall":overall,"regions":groups,
            "biology_and_collision":"UNKNOWN","visual_acceptance":False,
            "scientific_holds":["tail_body_intersection","hair_wind_realism","fur_density"]}
