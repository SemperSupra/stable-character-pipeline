"""Original 100STYLE BVH window-start falsifier; standalone stdlib/sha-pinned.

Tests temporal boundary sensitivity at source frames 119..122 and 180, not
the Blender retargeter's startFrame convention or protected/physical contact.
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"r088-motion-real"))
from bvh_preflight import parse_bvh,git_blob_sha,fk,SOURCES,SOURCE_COMMIT

SIDES=("LeftAnkle","RightAnkle","LeftToe","RightToe")
STARTS=(119,120,121,122,180)

def need(ok,code):
    if not ok:raise ValueError(code)

def edge_metrics(a,b,dt=1/60):
    need(len(a)==3 and len(b)==3 and
         all(type(v) in (int,float) and math.isfinite(v) for v in list(a)+list(b)) and
         type(dt) in (float,int) and math.isfinite(dt) and dt>0,
         "SOURCE_BVH_WINDOW_EDGE_INVALID")
    delta=[(b[i]-a[i])*0.01 for i in range(3)] # BVH cm->m.
    return {"delta_xyz_m":[round(x,9) for x in delta],
            "speed_3d_mps":round(math.hypot(*delta)*1.0/dt,6),
            "speed_horizontal_xz_mps":round(math.hypot(delta[0],delta[2])/dt,6)}

def window_summary(coords,start):
    need(type(start) is int and start>=1 and start+60<len(coords),
         "SOURCE_BVH_WINDOW_START_RANGE")
    pairs=[edge_metrics(coords[i-1],coords[i]) for i in range(start,start+61)]
    before=pairs[0]["speed_3d_mps"]
    at=pairs[1]["speed_3d_mps"]
    next_=pairs[2]["speed_3d_mps"]
    rest=[v["speed_3d_mps"] for v in pairs[1:]]
    return {"source_window_start":start,
            "preceding_edge":str(start-1)+"->"+str(start),
            "first_edge":str(start)+"->"+str(start+1),
            "first_edge_speed_3d_mps":at,
            "preceding_edge_speed_3d_mps":before,
            "next_edge_speed_3d_mps":next_,
            "first_edge_delta_xyz_m":pairs[1]["delta_xyz_m"],
            "first_60_edges_p50_3d_speed_mps":round(statistics.median(rest),6),
            "first_60_edges_max_3d_speed_mps":round(max(rest),6),
            "source_first_edge_over_p50_ratio":
                round(at/statistics.median(rest),6) if statistics.median(rest)>1e-9 else None,
            "start_does_not_prove_target_retarget_clock":True}

def analyze_source(blob):
    need(isinstance(blob,bytes) and git_blob_sha(blob)==SOURCES["Neutral_FW.bvh"],
         "SOURCE_100STYLE_BLOB_AUTHORIZATION_FAILED")
    bvh=parse_bvh(blob)
    need(bvh["count"]==2400 and abs(bvh["frame_time"]-1/60)<1e-5 and
         all(j in bvh["names"] for j in SIDES),
         "SOURCE_100STYLE_60HZ_OR_JOINTS")
    # Minimum common window covering 118..241 for all factors. Never fake data.
    samples={k:[] for k in SIDES}
    for f in range(242):
        pos=fk(bvh,f)
        for name in SIDES:samples[name].append(pos[name])
    cases={str(s):{name:window_summary(samples[name],s) for name in SIDES}
           for s in STARTS}
    return {"schema":"scp.r009.peer-original-source-window-sensitivity-v1",
            "source_class":"ORIGINAL_PUBLIC_100STYLE_CC_BY_4",
            "source_git_commit":SOURCE_COMMIT,
            "source_blob_sha1":SOURCES["Neutral_FW.bvh"],
            "source_full_frame_count":2400,
            "source_clock_hz":60,
            "original_world_axes":"Y-up, X/Z horizontal",
            "unit_conversion":"BVH centimetres*0.01 = metres",
            "source_file_not_redistributed":True,
            "source_window_offsets_studied":list(STARTS),
            "windows":cases,
            "native_retarget_equivalence_accepted":False,
            "true_contact_accepted":False,
            "protected_likeness_used":False,
            "mvp_accepted":False,"status":"HOLD"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--motion",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    need(Path(a.motion).name=="Neutral_FW.bvh","SOURCE_100STYLE_PATH_NAME")
    result=analyze_source(Path(a.motion).read_bytes())
    Path(a.out).write_text(json.dumps(result,sort_keys=True,allow_nan=False)+"\n")
    print("R009_SOURCE_WINDOW_DOE_HOLD",json.dumps(result,sort_keys=True),flush=True)
