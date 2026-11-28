"""Bounded JSONL paired-motion audit; identical diagnostic semantics, O(vertices) state."""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"r009-paired-envelope"))
from paired_envelope import FPS, SUB, FRAMES, schedule, read_packet, need, unique, sub, scale

MAX_LINE=8*1024*1024
PEAKS=("max_induced_displacement_m","max_candidate_speed_mps","max_induced_speed_mps","max_induced_acceleration_mps2")

def line(stream,limit):
    raw=stream.readline(limit+1)
    need(len(raw)<=limit,"LINE_BUDGET")
    need(bool(raw),"SAMPLE_DENOMINATOR")
    return json.loads(raw,object_pairs_hook=unique,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))

def header(stream,limit):
    data=line(stream,limit)
    need(type(data) is dict and "rows" not in data,"STREAM_HEADER")
    return data

def points(meta,row,tick):
    return {k:v[0] for k,v in read_packet({**meta,"rows":[row]},[tick]).items()}

def put(record,key,value,tick):
    if key not in record or value>record[key]["value"]:
        record[key]={"value":value,"tick":tick}

def norm(v):
    return math.hypot(*v)

def audit_stream(ref,cand,windows,limit=MAX_LINE):
    need(type(limit) is int and 1024<=limit<=MAX_LINE,"LINE_BUDGET_CONFIG")
    ticks=schedule(windows)
    outside=sum(not any(lo*SUB<=t<=hi*SUB for lo,hi in windows) for t in ticks)
    need(bool(outside),"OUTSIDE_CONTROL_MISSING")
    rh,ch=header(ref,limit),header(cand,limit)
    layout=None
    track={}
    previous_tick=None
    previous_dt=None
    for tick in ticks:
        a,b=points(rh,line(ref,limit),tick),points(ch,line(cand,limit),tick)
        need(set(a)==set(b),"PAIRED_MATERIAL_OR_MARKER_IDS")
        if layout is None:
            layout=tuple(sorted(a))
            for key in layout:
                track[key]={"first":b[key],"last":None,"diff":None,"iv":None,
                    "stats":{"outside_window_max_displacement_m":0.0,"min_candidate_world_z_m":b[key][2]}}
        need(set(a)==set(layout),"MATERIAL_OR_MARKER_ID_DRIFT")
        dt=None if previous_tick is None else (tick-previous_tick)/(FPS*SUB)
        is_outside=not any(lo*SUB<=tick<=hi*SUB for lo,hi in windows)
        for key in layout:
            state=track[key];m=state["stats"];p=b[key];d=sub(p,a[key])
            displacement=norm(d)
            put(m,PEAKS[0],displacement,tick)
            if is_outside:m["outside_window_max_displacement_m"]=max(m["outside_window_max_displacement_m"],displacement)
            m["min_candidate_world_z_m"]=min(m["min_candidate_world_z_m"],p[2])
            if dt is not None:
                cv=scale(sub(p,state["last"]),1/dt)
                iv=scale(sub(d,state["diff"]),1/dt)
                speed=norm(cv)
                put(m,PEAKS[1],speed,tick);put(m,PEAKS[2],norm(iv),tick)
                if "first_edge_candidate_speed_mps" not in m:m["first_edge_candidate_speed_mps"]=speed
                m["last_edge_candidate_speed_mps"]=speed
                if previous_dt is not None:
                    acc=scale(sub(iv,state["iv"]),2/(previous_dt+dt))
                    put(m,PEAKS[3],norm(acc),tick)
                state["iv"]=iv
            state["last"],state["diff"]=p,d
        previous_tick,previous_dt=tick,dt
    need(not ref.read(1) and not cand.read(1),"EXTRA_SAMPLES")
    actors={}
    for actor,kind,name in layout:
        state=track[(actor,kind,name)];m=state["stats"]
        m["endpoint_candidate_displacement_m"]=math.dist(state["first"],state["last"])
        entry=actors.setdefault(actor,{"markers":{},"feet":{"L":{},"R":{}}})
        if kind=="marker":entry["markers"][name]=m
        else:entry["feet"][kind][name]=m
    for actor in actors.values():
        for side,vertices in actor["feet"].items():
            def peak(k):
                vertex=max(vertices,key=lambda v:vertices[v][k]["value"])
                return {"vertex":vertex,**vertices[vertex][k]}
            actor["feet"][side]={"vertex_count":len(vertices),**{k:peak(k) for k in PEAKS},
                "outside_window_max_displacement_m":max(v["outside_window_max_displacement_m"] for v in vertices.values()),
                "min_candidate_world_z_m":min(v["min_candidate_world_z_m"] for v in vertices.values())}
    return {"schema":"scp.paired-world-diagnostic.v1","reference_scene_sha256":rh["scene_sha256"],
        "candidate_scene_sha256":ch["scene_sha256"],"samples":len(ticks),"edges":len(ticks)-1,
        "acceleration_triplets":len(ticks)-2,"integer_frames":FRAMES,"dense_windows":windows,
        "subdiv":SUB,"last_tick":ticks[-1],"outside_samples":outside,"actors":actors,
        "status":"HOLD_DIAGNOSTIC_ONLY","physical_contact_accepted":False,"ground_reaction_force_measured":False,
        "naturalness_accepted":False,"protected_likeness_used":False,"mvp_accepted":False}

def main():
    p=argparse.ArgumentParser()
    for key in ("reference","candidate","windows","out"):p.add_argument("--"+key,required=True)
    q=p.parse_args()
    with open(q.reference,"rb") as a,open(q.candidate,"rb") as b:
        result=audit_stream(a,b,json.loads(q.windows,object_pairs_hook=unique))
    with open(q.out,"x") as f:json.dump(result,f,sort_keys=True,allow_nan=False)

if __name__=="__main__":main()
