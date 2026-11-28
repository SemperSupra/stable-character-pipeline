"""Paired native sample diagnostic; no inferred stance, GRF or acceptance."""
import argparse
import json
import math
import re
from pathlib import Path

FRAMES, FPS, SUB = 360, 60, 32
SCHEMA = "scp.paired-world-samples.v1"
MARKERS = ("root", "pelvis", "torso", "knee_L", "knee_R", "ankle_L", "ankle_R")

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

def schedule(windows):
    need(type(windows) is list and 1 <= len(windows) <= 16, "DENSE_WINDOWS")
    ticks = set(range(0, FRAMES*SUB, SUB))
    previous = -1
    for window in windows:
        need(type(window) is list and len(window) == 2 and
             all(type(x) is int for x in window), "DENSE_WINDOW_TYPE")
        lo, hi = window
        need(previous < lo < hi < FRAMES, "DENSE_WINDOW_ORDER_RANGE")
        previous = hi
        ticks.update(range(lo*SUB, hi*SUB+1))
    return sorted(ticks)

def sha(x):
    return type(x) is str and re.fullmatch("[0-9a-f]{64}", x) is not None

def vec(x):
    need(type(x) is list and len(x) == 3 and
         all(type(v) in (int,float) and math.isfinite(v) and abs(v) <= 1000 for v in x),
         "WORLD_XYZ")
    return tuple(float(v) for v in x)

def sub(a,b):
    return tuple(x-y for x,y in zip(a,b))

def scale(a,s):
    return tuple(x*s for x in a)

def maximum(xs, ticks):
    i=max(range(len(xs)), key=xs.__getitem__)
    return {"value": xs[i], "tick": ticks[i]}

def read_packet(packet, ticks):
    need(type(packet) is dict and packet.get("schema") == SCHEMA and
         packet.get("source_class") == "ORIGINAL_SYNTHETIC" and
         sha(packet.get("scene_sha256")) and
         type(packet.get("fps")) is int and packet["fps"] == FPS and
         type(packet.get("subdiv")) is int and packet["subdiv"] == SUB and
         packet.get("physical_contact_accepted") is False and
         packet.get("protected_likeness_used") is False, "PACKET_ADMISSION")
    rows=packet.get("rows")
    need(type(rows) is list and len(rows)==len(ticks), "SAMPLE_DENOMINATOR")
    series={}
    layout=None
    for tick,row in zip(ticks,rows):
        need(type(row) is dict and type(row.get("tick")) is int and row["tick"]==tick,
             "SAMPLE_CLOCK")
        actors=row.get("actors")
        need(type(actors) is dict and len(actors)==2 and
             all(type(a) is str and re.fullmatch("[A-Za-z0-9_-]{1,64}",a) for a in actors),
             "ACTOR_IDS")
        values={}
        for actor,body in actors.items():
            need(type(body) is dict and set(body)=={"markers","feet"}, "BODY_SCHEMA")
            markers,feet=body["markers"],body["feet"]
            need(type(markers) is dict and set(markers)==set(MARKERS), "BODY_MARKERS")
            need(type(feet) is dict and set(feet)=={"L","R"}, "BILATERAL_FEET")
            for marker in MARKERS:
                values[(actor,"marker",marker)]=vec(markers[marker])
            for side,vertices in feet.items():
                need(type(vertices) is dict and 4<=len(vertices)<=10000 and
                     all(type(k) is str and re.fullmatch("0|[1-9][0-9]{0,8}",k) for k in vertices),
                     "FIXED_VERTEX_IDS")
                for vertex,point in vertices.items():
                    values[(actor,side,vertex)]=vec(point)
        if layout is None:
            layout=set(values)
            series={key:[] for key in sorted(layout)}
        need(set(values)==layout, "MATERIAL_OR_MARKER_ID_DRIFT")
        for key,value in values.items():
            series[key].append(value)
    return series

def metrics(ref,cand,ticks,outside):
    diff=[sub(c,r) for r,c in zip(ref,cand)]
    dt=[(b-a)/(FPS*SUB) for a,b in zip(ticks,ticks[1:])]
    cv=[scale(sub(b,a),1/d) for a,b,d in zip(cand,cand[1:],dt)]
    iv=[scale(sub(b,a),1/d) for a,b,d in zip(diff,diff[1:],dt)]
    acceleration=[scale(sub(b,a),2/(d+e)) for a,b,d,e in zip(iv,iv[1:],dt,dt[1:])]
    return {
        "max_induced_displacement_m":maximum([math.hypot(*v) for v in diff],ticks),
        "max_candidate_speed_mps":maximum([math.hypot(*v) for v in cv],ticks[1:]),
        "max_induced_speed_mps":maximum([math.hypot(*v) for v in iv],ticks[1:]),
        "max_induced_acceleration_mps2":maximum([math.hypot(*v) for v in acceleration],ticks[2:]),
        "outside_window_max_displacement_m":max(math.hypot(*diff[i]) for i in outside),
        "first_edge_candidate_speed_mps":math.hypot(*cv[0]),
        "last_edge_candidate_speed_mps":math.hypot(*cv[-1]),
        "endpoint_candidate_displacement_m":math.dist(cand[0],cand[-1]),
        "min_candidate_world_z_m":min(p[2] for p in cand),
    }

def audit(reference,candidate,windows):
    ticks=schedule(windows)
    a,b=read_packet(reference,ticks),read_packet(candidate,ticks)
    need(set(a)==set(b),"PAIRED_MATERIAL_OR_MARKER_IDS")
    outside=[i for i,t in enumerate(ticks) if not any(lo*SUB<=t<=hi*SUB for lo,hi in windows)]
    need(bool(outside),"OUTSIDE_CONTROL_MISSING")
    actors={}
    for key in a:
        actor,kind,name=key
        entry=actors.setdefault(actor,{"markers":{},"feet":{"L":{},"R":{}}})
        result=metrics(a[key],b[key],ticks,outside)
        if kind=="marker":
            entry["markers"][name]=result
        else:
            entry["feet"][kind][name]=result
    for actor in actors.values():
        for side,vertices in actor["feet"].items():
            def peak(k):
                vertex=max(vertices,key=lambda v:vertices[v][k]["value"])
                return {"vertex":vertex,**vertices[vertex][k]}
            actor["feet"][side]={
                "vertex_count":len(vertices),
                "max_induced_displacement_m":peak("max_induced_displacement_m"),
                "max_candidate_speed_mps":peak("max_candidate_speed_mps"),
                "max_induced_speed_mps":peak("max_induced_speed_mps"),
                "max_induced_acceleration_mps2":peak("max_induced_acceleration_mps2"),
                "outside_window_max_displacement_m":max(v["outside_window_max_displacement_m"] for v in vertices.values()),
                "min_candidate_world_z_m":min(v["min_candidate_world_z_m"] for v in vertices.values()),
            }
    return {
        "schema":"scp.paired-world-diagnostic.v1",
        "reference_scene_sha256":reference["scene_sha256"],
        "candidate_scene_sha256":candidate["scene_sha256"],
        "samples":len(ticks), "edges":len(ticks)-1, "acceleration_triplets":len(ticks)-2,
        "integer_frames":FRAMES, "dense_windows":windows, "subdiv":SUB,
        "last_tick":ticks[-1], "outside_samples":len(outside),
        "actors":actors,
        "status":"HOLD_DIAGNOSTIC_ONLY",
        "physical_contact_accepted":False,"ground_reaction_force_measured":False,
        "naturalness_accepted":False,"protected_likeness_used":False,"mvp_accepted":False,
    }

def unique(pairs):
    out={}
    for k,v in pairs:
        need(k not in out,"DUPLICATE_JSON_KEY")
        out[k]=v
    return out

def load(path):
    return json.loads(Path(path).read_text(),object_pairs_hook=unique,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for key in ("reference","candidate","windows","out"):
        p.add_argument("--"+key,required=True)
    q=p.parse_args()
    result=audit(load(q.reference),load(q.candidate),json.loads(q.windows))
    with open(q.out,"x") as f:
        json.dump(result,f,sort_keys=True,allow_nan=False)
    print("PAIRED_WORLD_ENVELOPE",json.dumps(result,sort_keys=True,allow_nan=False))
