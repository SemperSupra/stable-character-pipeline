"""Original-only Blender frame-0/1/0 repeatability critic. Never accepts contact or gait."""
import math

SEQ=(0,1,0,1,100,0,1)
SHOE_FIELDS=("heel_xy","ball_xy","heel_min_z","ball_min_z","world_shoe_side_min_z")
BONES=("foot","toe")

def need(ok,code):
    if not ok: raise ValueError(code)

def numeric(x):
    need(type(x) in (float,int) and math.isfinite(x) and abs(x)<100,"NONFINITE_OR_INVALID_FIRST_EDGE")
    return float(x)

def shoe_values(side):
    vals=[]
    need(isinstance(side,dict),"MALFORMED_SIDE")
    for key in SHOE_FIELDS:
        x=side[key]
        if key.endswith("_xy"):
            need(isinstance(x,(list,tuple)) and len(x)==2,"MALFORMED_REGION_XY")
            vals.extend(numeric(t) for t in x)
        else: vals.append(numeric(x))
    return vals

def bone_values(record):
    vals=[]
    for side in ("L","R"):
        for label in BONES:
            vec=record["bones"][side][label]
            need(isinstance(vec,(tuple,list)) and len(vec)==3,"INVALID_NATIVE_BONE")
            vals.extend(numeric(v) for v in vec)
    return vals

def diff(a,b):
    need(len(a)==len(b),"INCOMPATIBLE_FIRST_EDGE_VECTORS")
    return max((abs(x-y) for x,y in zip(a,b)),default=0.0)

def evaluate(trace,baseline):
    """Seven real replay samples compared to original full 360-frame observer."""
    need(isinstance(trace,list) and len(trace)==len(SEQ),"FIRST_EDGE_TRACE_MISSING")
    need(isinstance(baseline,dict) and set(baseline)=={"L","R"},"SOURCE_BASELINE_SIDES")
    for side in ("L","R"):
        need(isinstance(baseline[side],list) and len(baseline[side])==360,"SOURCE_BASELINE_360")
        for frame in (0,1): shoe_values(baseline[side][frame])
    flat=[]
    for i,record in enumerate(trace):
        need(type(record.get("frame")) is int and record["frame"]==SEQ[i],
             "FIRST_EDGE_FRAME_ORDER")
        need(set(record["shoe"])=={"L","R"},"FIRST_EDGE_TWO_SHOE_SIDES")
        need(isinstance(record["pose_sha256"],str) and len(record["pose_sha256"])==64 and
             isinstance(record["body_sha256"],str) and len(record["body_sha256"])==64,
             "FIRST_EDGE_POSE_OR_SKIN_DIGEST")
        flat.append([*shoe_values(record["shoe"]["L"]),
                     *shoe_values(record["shoe"]["R"])])
        bone_values(record)
    z0=[0,2,5]; z1=[1,3,6]
    repeat_shoe=max(diff(flat[z0[0]],flat[i]) for i in z0[1:])
    repeat_shoe=max(repeat_shoe,max(diff(flat[z1[0]],flat[i]) for i in z1[1:]))
    repeat_bone=max(diff(bone_values(trace[0]),bone_values(trace[i])) for i in z0[1:])
    repeat_bone=max(repeat_bone,max(diff(bone_values(trace[1]),bone_values(trace[i])) for i in z1[1:]))
    original=[]
    for frame in (0,1):
        original.append([*shoe_values(baseline["L"][frame]),*shoe_values(baseline["R"][frame])])
    replay=max(diff(flat[0],original[0]),diff(flat[1],original[1]))
    pose_consistent=(len({trace[i]["pose_sha256"] for i in z0})==1 and
                     len({trace[i]["pose_sha256"] for i in z1})==1)
    skin_consistent=(len({trace[i]["body_sha256"] for i in z0})==1 and
                     len({trace[i]["body_sha256"] for i in z1})==1)
    material={}
    native_bones={}
    for side in ("L","R"):
        material[side]={}
        native_bones[side]={}
        for label in ("heel","ball"):
            left=trace[0]["shoe"][side][label+"_xy"]
            right=trace[1]["shoe"][side][label+"_xy"]
            material[side][label+"_first_edge_xy_m"]=[round(numeric(b)-numeric(a),9) for a,b in zip(left,right)]
            material[side][label+"_first_edge_speed_mps"]=round(60*math.dist(left,right),6)
        for label in BONES:
            a=trace[0]["bones"][side][label]
            b=trace[1]["bones"][side][label]
            native_bones[side][label+"_first_edge_speed_mps"]=round(60*math.dist(a,b),6)
    stable=(repeat_shoe<=1e-6 and repeat_bone<=1e-6 and replay<=1e-6 and
            pose_consistent and skin_consistent)
    return {
        "max_repeat_shoe_coordinate_drift_m":round(repeat_shoe,9),
        "max_repeat_bone_coordinate_drift_m":round(repeat_bone,9),
        "max_vs_fullclip_first_edge_drift_m":round(replay,9),
        "pose_sha_consistent":pose_consistent,
        "body_sha_consistent":skin_consistent,
        "repeated_evaluation":"PASS_NARROW" if stable else "RED",
        "material":material,
        "native_bone_head":native_bones,
        "source_fk_comparison_accepted":False,
        "physical_contact_accepted":False,
        "mvp_accepted":False,
        "status":"HOLD",
    }
