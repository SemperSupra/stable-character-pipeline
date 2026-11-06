"""Source-bound classification of measured skinned longhair vs body contacts.

This is a diagnostic about animated triangle surfaces, not hair-body physical
truth, enclosed-volume containment, cloth forces or equine safety. A clean
surface crossing test never constitutes scientific acceptance.
"""
import hashlib
import json
import math

SCHEMA="equine.hair_body.contact_screen.v1"
FRAMES=48
REGION_CARDS={"mane":440,"forelock":230,"tail":380}
OBSTACLES={
    "mane":("sculpt_sloping_neck","continuous_shetland_barrel_rump_shoulder"),
    "forelock":("sculpt_equine_brow_bridge_muzzle","sculpt_sloping_neck"),
    "tail":("continuous_shetland_barrel_rump_shoulder","continuous_hind_L_limb",
            "continuous_hind_R_limb","hind_L_hoof","hind_R_hoof"),
}

def classify(records,*,frames=tuple(range(1,49))):
    if type(records) is not list or type(frames) not in (tuple,list):
        raise ValueError("invalid contact observations")
    if len(frames)<2 or len(frames)>240 or any(type(f) is not int for f in frames):
        raise ValueError("invalid frame horizon")
    if tuple(frames)!=tuple(sorted(set(frames))):
        raise ValueError("out-of-order/duplicate frame horizon")
    expected={(frame,region,obstacle) for frame in frames
              for region,obstacles in OBSTACLES.items() for obstacle in obstacles}
    if len(records)!=len(expected):raise ValueError("incomplete/excessive body observations")
    out={r:{"obstacle_contacts":{},"max_colliding_cards_in_frame":0,
            "possible_collision_frame_count":0,"min_tip_surface_distance_m":None}
         for r in REGION_CARDS}
    normalized=[];seen=set();flags={r:set() for r in REGION_CARDS}
    for row in records:
        if type(row) is not dict:raise ValueError("non-object contact witness")
        if set(row)!={"frame","region","obstacle","face_pairs","card_count",
                      "tip_samples","tips_within_5mm","min_tip_distance_m"}:
            raise ValueError("missing/extra contact field")
        frame=row["frame"];region=row["region"];obstacle=row["obstacle"]
        key=(frame,region,obstacle)
        if key not in expected or key in seen:raise ValueError("wrong/duplicate source witness")
        seen.add(key)
        n=REGION_CARDS[region]
        pairs=row["face_pairs"];cards=row["card_count"];tips=row["tip_samples"];near=row["tips_within_5mm"]
        if any(type(x) is not int for x in (pairs,cards,tips,near)):
            raise ValueError("noninteger contact evidence")
        if not (pairs>=cards>=0 and tips==n and 0<=near<=tips):
            raise ValueError("impossible measured geometry counts")
        d=row["min_tip_distance_m"]
        if type(d) not in (float,int) or not math.isfinite(d) or d<0 or d>100:
            raise ValueError("invalid measured distance")
        if near and d>=.005:
            raise ValueError("near witness contradicts minimum")
        if not near and d<.005:
            raise ValueError("near count contradicts minimum")
        entry=out[region];ob=entry["obstacle_contacts"].setdefault(obstacle,{
              "triangle_pair_observations":0,"hair_card_frame_observations":0,
              "tip_near_observations":0,"first_candidate_frame":None})
        ob["triangle_pair_observations"]+=pairs
        ob["hair_card_frame_observations"]+=cards
        ob["tip_near_observations"]+=near
        if cards:
            flags[region].add(frame)
            entry["max_colliding_cards_in_frame"]=max(entry["max_colliding_cards_in_frame"],cards)
            if ob["first_candidate_frame"] is None:ob["first_candidate_frame"]=frame
        if entry["min_tip_surface_distance_m"] is None or d<entry["min_tip_surface_distance_m"]:
            entry["min_tip_surface_distance_m"]=d
        normalized.append([frame,region,obstacle,pairs,cards,tips,near,round(float(d),8)])
    if seen!=expected:raise ValueError("missing measured regions/frames")
    total=0
    for region in REGION_CARDS:
        r=out[region]
        r["possible_collision_frame_count"]=len(flags[region])
        r["min_tip_surface_distance_m"]=round(r["min_tip_surface_distance_m"],7)
        r["verdict"]="POSSIBLE_TRIANGLE_CONTACT_REVIEW" if flags[region] else "NO_CROSSINGS_DETECTED_ONLY"
        total+=len(flags[region])
    sha=hashlib.sha256(json.dumps(sorted(normalized),separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
    return {"schema":SCHEMA,"source_sample_sha256":sha,
        "frames":len(frames),"tested_obstacle_surfaces":{r:list(x) for r,x in OBSTACLES.items()},
        "regions":out,"possible_region_frames":total,
        "candidate_collision":"POSSIBLE_CROSSING" if total else "NO_TRIANGLE_CROSSING_OBSERVED",
        "scientific_hold":"KEEP", "not_tested":["skin_inside_closed_volume",
            "short_fur_shell","hair_hair_intersection","contact_pressure",
            "animal_anatomy","mane_fiber_render_quality"],
        "release_or_CPE_admission":False,"visual_acceptance":False}
