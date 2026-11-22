"""Full-360 original CC0 shoe geometry diagnostic separating first-edge onset.

Read-only; not a stance detector, force, friction, body morphology or protected MVP.
The first-edge outlier is retained as evidence, never silently discarded.
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"r009-peer-native60"))
from shoe360_metrics import analyze

def need(ok,code):
    if not ok:raise ValueError(code)

def q95(xs):
    need(len(xs)>0,"EMPTY_POSTSTARTUP_VELOCITY")
    s=sorted(xs)
    return s[math.ceil(.95*len(s))-1]

def summarize(rows):
    need(type(rows) is list and len(rows)==360,
         "EXPECTED_AUTHENTIC_360_SOURCE_CLOCK_ROWS")
    base=analyze(rows)  # prior independent source-safe strict full 360 clock.
    velocities={}
    result={}
    for region in ("heel","ball"):
        key=region+"_xy"
        all_edges=[60*math.dist(rows[i-1][key],rows[i][key])
                   for i in range(1,360)]
        need(len(all_edges)==359 and all(math.isfinite(x) for x in all_edges),
             "NONFINITE_OR_ABSENT_SHOE_EDGES")
        remaining=all_edges[1:]
        post_frame=2+max(range(len(remaining)),key=lambda j:remaining[j])
        # There is no fullclip index0->-1 edge; keep the startup spike explicit.
        result[region]={
            "first_edge_0_to_1_speed_mps":round(all_edges[0],6),
            "post_startup_1_to_359_speed_max_mps":round(max(remaining),6),
            "post_startup_peak_destination_frame":post_frame,
            "post_startup_1_to_359_speed_p50_mps":round(statistics.median(remaining),6),
            "post_startup_1_to_359_speed_p95_mps":round(q95(remaining),6),
            "all_359_edges_including_first_peak_mps":round(max(all_edges),6),
            "all_359_edges_including_first_peak_destination_frame":
                1+max(range(len(all_edges)),key=lambda j:all_edges[j]),
        }
        velocities[region]=all_edges
    z=[float(r["world_shoe_side_min_z"]) for r in rows]
    need(all(math.isfinite(v) for v in z),"INVALID_ACTUAL_WORLD_MESH_Z")
    ground=[i for i,v in enumerate(z) if v < 0.0]
    deep5=[i for i,v in enumerate(z) if v < -.005]
    deep25=[i for i,v in enumerate(z) if v < -.025]
    eligible=[(-.005<=v<=.012) for v in z]
    near_pair=[i for i in range(2,360) if eligible[i] and eligible[i-1]]
    for region in ("heel","ball"):
        speeds=[velocities[region][i-1] for i in near_pair]
        result[region]["post_startup_near_plane_candidate_pairs"]=len(speeds)
        result[region]["post_startup_near_plane_candidate_max_mps"]=round(max(speeds),6) if speeds else None
        result[region]["post_startup_near_plane_candidate_peak_frame"]=max(
            near_pair,key=lambda i:velocities[region][i-1]) if speeds else None
    return {
        "fullclip_replayed_same_original_metrics":base,
        "all_360_frame_shoe_side_floor_z_min_m":round(min(z),9),
        "whole_clip_penetration_mm":round(1000*max(0.,-min(z)),6),
        "all_360_frames_below_floor":len(ground),
        "all_360_frames_penetration_gt_5mm":len(deep5),
        "all_360_frames_penetration_gt_25mm":len(deep25),
        "deepest_penetration_destination_frame":min(range(360),key=lambda i:z[i]),
        "speed_by_region":result,
        "first_edge_outlier_retained":True,
        "source_ground_geometry_only_not_stance":True,
        "true_planted_contact_proven":False,
        "ground_reaction_force_measured":False,
        "mvp_accepted":False,
        "status":"HOLD",
    }

def build(record):
    need(isinstance(record,dict) and
         record.get("schema")=="scp.r009.peer-original-native360-shoe-fullclip-v1" and
         record.get("source_class")=="ORIGINAL_FICTIONAL_MPFBCORE_CC0" and
         record.get("source_60hz_frame_count")==360 and
         record.get("physical_contact_accepted") is False and
         record.get("protected_likeness_used") is False,
         "NONAUTHENTIC_OR_PROTECTED_SHOE_SOURCE")
    actors=record.get("actors")
    need(isinstance(actors,list) and len(actors)==2 and
         {p["name"] for p in actors}=={"AsterOriginal","JuniperOriginal"},
         "ORIGINAL_TWO_ACTORS_REQUIRED")
    out={}
    for actor in actors:
        out[actor["name"]]={}
        need(set(actor["sides"])=={"L","R"},"ACTUAL_BILATERAL_SHOE_MISSING")
        for side in ("L","R"):
            entry=actor["sides"][side]
            calculated=analyze(entry["rows"])
            need(calculated==entry["metrics"],"ORIGINAL_FULLCLIP_METRIC_DRIFT")
            out[actor["name"]][side]=summarize(entry["rows"])
    return {
        "schema":"scp.r009.peer-original-native360-shoe-poststartup-v1",
        "native_blend_sha256":record.get("exact_native_blend_sha256"),
        "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
        "source_60hz_frames":360,"source_60hz_frame_edges":359,
        "actual_shoe_geometry_only":True,
        "source_first_edge_not_discarded":True,
        "true_planted_contact_proven":False,
        "ground_reaction_force_measured":False,
        "protected_likeness_used":False,
        "mvp_accepted":False,
        "actors":out,"status":"HOLD"}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--fullclip",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    data=json.loads(Path(a.fullclip).read_text())
    out=build(data)
    Path(a.out).write_text(json.dumps(out,sort_keys=True,allow_nan=False)+"\n")
    print("R009_ORIGINAL_SHOE_POSTSTARTUP_CONTACT_HOLD",
          json.dumps({"actors":{
              k:{side:{"penetration_mm":v["whole_clip_penetration_mm"],
                   "all_360_frames_below_floor":v["all_360_frames_below_floor"],
                   "heel":v["speed_by_region"]["heel"],
                   "ball":v["speed_by_region"]["ball"]}
                 for side,v in sides.items()}
              for k,sides in out["actors"].items()},"status":"HOLD"},sort_keys=True))
