"""Independent full-edge 60 Hz source/native gait observer; diagnostic only.

No contact/force, anatomical identity, source-clock repair or MVP acceptance.
The original source is Y-up (horizontal x,z); Blender target is Z-up (horizontal x,y).
Read-only tool for existing 360-row N03D-AC original-CC0 native witness.
"""
import argparse
import json
import math
from pathlib import Path

ACTORS = ("AsterOriginal", "JuniperOriginal")
SIDES = ("L", "R")


def _require(ok, label):
    if not ok:
        raise ValueError(label)


def _point(row, key):
    p = row.get(key)
    _require(isinstance(p, list) and len(p) == 3, "POINT_SHAPE")
    _require(all(type(v) in (int, float) and math.isfinite(v) and abs(v) < 100 for v in p), "POINT_FINITE")
    return p


def _delta(a, b, axes):
    return tuple(b[k] - a[k] for k in axes)


def _norm(vec):
    return math.sqrt(sum(v*v for v in vec))


def observe(rows, threshold_mps=5.0):
    _require(type(threshold_mps) in (int,float) and math.isfinite(threshold_mps) and
             threshold_mps > 0.0, "THRESHOLD")
    _require(isinstance(rows,list) and len(rows)==360, "EXACT_360_ROWS")
    for i,row in enumerate(rows):
        _require(isinstance(row, dict) and type(row.get("index")) is int and row["index"]==i, "INDEX")
        t=row.get("time_s")
        _require(type(t) in (int,float) and math.isfinite(t) and abs(t-i/60.0)<1e-7, "TIMEBASE")
        for k in ("source_ankle","source_toe","target_foot","target_hip"):
            _point(row,k)
    edge_speeds=[]
    edge_vectors=[]
    source_tail_m=0.0
    target_tail_m=0.0
    for i in range(1,360):
        a,b=rows[i-1],rows[i]
        src=_delta(a["source_ankle"],b["source_ankle"],(0,2))
        tgt=_delta(a["target_foot"],b["target_foot"],(0,1))
        velocity=tuple(60.0*d for d in tgt)
        edge_vectors.append(velocity)
        edge_speeds.append(_norm(velocity))
        if i>=356:
            source_tail_m+=_norm(src)
            target_tail_m+=_norm(tgt)
    accelerations=[_norm(tuple(60.0*(c[k]-p[k]) for k in range(2)))
                   for p,c in zip(edge_vectors,edge_vectors[1:])]
    large=[i+1 for i,v in enumerate(edge_speeds) if v>threshold_mps]
    return {
        "frame_count":360,
        "edge_count":359,
        "last_sample_time_s":round(359/60,9),
        "max_target_planar_speed_mps":round(max(edge_speeds),6),
        "max_target_planar_accel_mps2":round(max(accelerations),6),
        "max_speed_edge_destination_frame":1+max(range(359),key=lambda j:edge_speeds[j]),
        "large_edge_count":len(large),
        "first_large_edge_destination_frame":large[0] if large else None,
        "source_last_four_planar_path_m":round(source_tail_m,9),
        "target_last_four_planar_path_m":round(target_tail_m,9),
        "tail_motion_disagreement_observed":bool(source_tail_m>1e-6 and target_tail_m<1e-9),
        "physical_contact_accepted":False,
        "native_motion_repaired":False,
        "status":"HOLD",
    }


def assess(report):
    _require(isinstance(report,dict) and
             report.get("schema")=="scp.n03d-ac.matched-source-to-bone-60hz.v1" and
             report.get("source_class")=="ORIGINAL_FICTIONAL_CC0" and
             report.get("mvp_accepted") is False and
             report.get("source_motion_changed") is False, "PROVENANCE")
    actors=report.get("actors")
    _require(isinstance(actors,list) and len(actors)==2,"ACTORS")
    seen=set()
    results=[]
    for actor in actors:
        _require(isinstance(actor,dict) and actor.get("name") in ACTORS and
                 isinstance(actor.get("sides"),dict),"ACTOR")
        for side,rows in actor["sides"].items():
            _require(side in SIDES and (actor["name"],side) not in seen,"SIDE")
            seen.add((actor["name"],side))
            results.append({"actor":actor["name"],"side":side,**observe(rows)})
    _require(seen=={(actor,side) for actor in ACTORS for side in SIDES},"INCOMPLETE_ACTORS")
    return {"schema":"scp.r009.peer-native-full-edge-v1",
            "source":"original-fictional-cc0",
            "status":"HOLD","mvp_accepted":False,
            "results":results}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    report=json.loads(Path(args.source).read_text())
    result=assess(report)
    Path(args.out).write_text(json.dumps(result,sort_keys=True,allow_nan=False)+"\n")
    print("R009_NATIVE_FULL_EDGE_DIAGNOSTIC_ONLY",json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
