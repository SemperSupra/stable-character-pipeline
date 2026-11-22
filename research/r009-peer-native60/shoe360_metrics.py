"""Independent source-safe 360@60Hz full-edge skinned-shoe material diagnostic.

Inputs are actual evaluated Blender CC0 fixed shoe material cohorts. Any
near-ground threshold is a candidate geometry label, NOT stance/contact force.
"""
import math


def need(ok,code):
    if not ok:
        raise ValueError(code)


def point2(p):
    need(isinstance(p,(list,tuple)) and len(p)==2 and
         all(type(v) in (int,float) and math.isfinite(v) and abs(v)<100 for v in p),
         "SHOE_PLANAR_POINT_INVALID")
    return p


def scalar(x):
    need(type(x) in (int,float) and math.isfinite(x) and abs(x)<100,
         "SHOE_WORLD_Z_INVALID")
    return float(x)


def analyze(rows):
    need(isinstance(rows,list) and len(rows)==360,"SOURCE_60HZ_NOT_360_FRAMES")
    for i,row in enumerate(rows):
        need(type(row.get("frame")) is int and row["frame"]==i,"SOURCE_FRAME_INDEX")
        need(type(row.get("t")) in (float,int) and math.isfinite(row["t"]) and
             abs(row["t"]-i/60)<1e-7,"SOURCE_SAMPLE_TIME")
        for key in ("heel_xy","ball_xy"):
            point2(row[key])
        for key in ("world_shoe_side_min_z","heel_min_z","ball_min_z"):
            scalar(row[key])
    heel_v=[];ball_v=[];candidate=[];transitions=[]
    for i in range(1,360):
        prev,cur=rows[i-1],rows[i]
        heel_v.append(60*math.dist(prev["heel_xy"],cur["heel_xy"]))
        ball_v.append(60*math.dist(prev["ball_xy"],cur["ball_xy"]))
        eligible=lambda r: -0.005<=r["world_shoe_side_min_z"]<=0.012
        candidate.append(eligible(prev) and eligible(cur))
        transitions.append(eligible(prev)!=eligible(cur))
    tail_heel=sum(math.dist(rows[i]["heel_xy"],rows[i-1]["heel_xy"]) for i in range(356,360))
    tail_ball=sum(math.dist(rows[i]["ball_xy"],rows[i-1]["ball_xy"]) for i in range(356,360))
    minimum=min(row["world_shoe_side_min_z"] for row in rows)
    return {
        "source_frames":360,
        "source_frame_edges":359,
        "source_sample_end_s":round(359/60,9),
        "min_actual_world_shoe_side_z_m":round(minimum,8),
        "max_actual_geometry_penetration_m":round(max(0.,-minimum),8),
        "max_heel_material_region_speed_mps":round(max(heel_v),6),
        "max_ball_material_region_speed_mps":round(max(ball_v),6),
        "max_heel_near_ground_candidate_speed_mps":round(max((v for v,yes in zip(heel_v,candidate) if yes),default=0.),6),
        "max_ball_near_ground_candidate_speed_mps":round(max((v for v,yes in zip(ball_v,candidate) if yes),default=0.),6),
        "candidate_near_ground_pair_count":sum(candidate),
        "candidate_ground_transition_edges":sum(transitions),
        "max_candidate_transition_edge_speed_mps":round(max((max(a,b) for a,b,yes in zip(heel_v,ball_v,transitions) if yes),default=0.),6),
        "last_four_heel_material_path_m":round(tail_heel,9),
        "last_four_ball_material_path_m":round(tail_ball,9),
        "physical_contact_accepted":False,
        "ground_reaction_force_measured":False,
        "status":"HOLD",
    }
