"""W06 original two-character public park walk. Source-neutral, explicit 2D motion.

No identifiable likeness, private vendor models, outside textures or paid inference.
World-space planted ankle position is a source-owned invariant, not a heuristic
measured from raster pixels. Source body proportions are stylized, not metric.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA="scp.walk_motion.v1"
CLASS="ORIGINAL_SELF_AUTHORED_PUBLIC_PROCEDURAL_CHARACTERS_NOT_REAL_PERSONS"
FPS=12
N=72
DURATION=6.0
MOVING_UNTIL=5.4
PERIOD=.9
STANCE=.62
THIGH=.61
SHIN=.57
GROUND_ANKLE_Y=.11
ACTORS=(
    {"id":"cobalt-automaton","name":"Cobalt Automaton","kind":"self-authored-robot-avatar","start_x":-2.7,"facing":1,"base_color":"#297a99","accent_color":"#f4b35e"},
    {"id":"marigold-explorer","name":"Marigold Explorer","kind":"self-authored-fantasy-avatar","start_x":2.7,"facing":-1,"base_color":"#d78b44","accent_color":"#7d5aac"}
)

def smoothstep(v):
    return v*v*(3-2*v)

def root_at(start,direction,speed,t):
    return start+direction*speed*max(0,min(t,MOVING_UNTIL))

def foot_at(actor,side,t,speed):
    direction=actor["facing"]
    x0=actor["start_x"]
    if t>=MOVING_UNTIL:
        return foot_at(actor,side,MOVING_UNTIL-1e-9,speed)[:2]+(True,)
    offset=0.0 if side=="left" else .5
    u=t/PERIOD+offset
    cycle=math.floor(u)
    phase=u-cycle
    tplant=(cycle-offset)*PERIOD
    planted=root_at(x0,direction,speed,tplant)+direction*.18
    if phase<STANCE:
        return planted,GROUND_ANKLE_Y,True
    p=(phase-STANCE)/(1-STANCE)
    target=root_at(x0,direction,speed,tplant+PERIOD)+direction*.18
    return planted+(target-planted)*smoothstep(p),GROUND_ANKLE_Y+.18*math.sin(math.pi*p),False

def ik_knee(hip,ankle,direction):
    dx=ankle[0]-hip[0];dy=ankle[1]-hip[1]
    d=math.hypot(dx,dy)
    if d>=THIGH+SHIN-1e-7 or d<=abs(THIGH-SHIN)+1e-7:
        raise ValueError("IK_REACH_OR_ZERO_LENGTH")
    a=(THIGH*THIGH-SHIN*SHIN+d*d)/(2*d)
    h2=THIGH*THIGH-a*a
    if h2<-1e-10:
        raise ValueError("IK_NEGATIVE_RADICAND")
    height=math.sqrt(max(0,h2))
    ux=dx/d;uy=dy/d
    # Forward bend in source character's direction; no hidden facing guesses.
    return [hip[0]+a*ux+direction*height*(-uy),
            hip[1]+a*uy+direction*height*ux]

def pt(x,y):
    return [round(x,9),round(y,9)]

def make_pose(actor,t,speed):
    d=actor["facing"];root=root_at(actor["start_x"],d,speed,t)
    moving=t<MOVING_UNTIL
    bob=(.017*math.sin(4*math.pi*t/PERIOD)**2 if moving else 0)
    hip_y=1.13+bob
    positions={}
    contact={}
    for side,side_index in (("left",-1),("right",1)):
        hx=root+side_index*.073*d
        hip=(hx,hip_y)
        ax,ay,grounded=foot_at(actor,side,t,speed)
        ankle=(ax,ay)
        knee=ik_knee(hip,ankle,d)
        positions["hip_"+side]=pt(*hip)
        positions["knee_"+side]=pt(*knee)
        positions["ankle_"+side]=pt(*ankle)
        contact[side]=grounded
    positions["pelvis"]=pt(root,hip_y)
    positions["torso"]=pt(root,1.49+bob)
    positions["neck"]=pt(root,1.79+bob)
    positions["head"]=pt(root,2.065+bob)
    for side,side_index in (("left",-1),("right",1)):
        shoulder=pt(root+side_index*.19*d,1.72+bob)
        phase=2*math.pi*(t/PERIOD+(0 if side=="left" else .5))
        swing=math.sin(phase)*(.17 if moving else 0)
        elbow=pt(shoulder[0]-d*swing*.68,1.41+bob)
        wrist=pt(shoulder[0]-d*swing,1.16+bob)
        positions["shoulder_"+side]=shoulder
        positions["elbow_"+side]=elbow
        positions["wrist_"+side]=wrist
    return {
        "root_x":round(root,9),"facing":d,"walking":moving,
        "joints":positions,"contact":contact,
        "left_step_phase":round((t/PERIOD)%1,9),
        "source_semantics":"camera_plane_2d_original_joint_ik_and_world_stance_ankle",
    }

def generate(profile="relaxed"):
    if profile not in ("relaxed","brisk"):
        raise ValueError("INVALID_ADMITTED_PUBLIC_GAIT_PROFILE")
    speed=.35 if profile=="relaxed" else .37
    frames=[]
    for i in range(N):
        t=i/FPS
        frames.append({
            "index":i,"timestamp_ms":int(round(t*1000)),
            "time_s":round(t,9),
            "actors":{a["id"]:make_pose(a,t,speed) for a in ACTORS},
        })
    model={
        "schema":SCHEMA,"classification":CLASS,
        "source_rights":"ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY",
        "profile":profile,"fps":FPS,"frames_count":N,
        "duration_seconds":DURATION,"moving_until_seconds":MOVING_UNTIL,
        "geometry_space":"STYLIZED_CAMERA_XY_UNCALIBRATED",
        "ankle_ground_y":GROUND_ANKLE_Y,
        "gait_period_seconds":PERIOD,"stance_fraction":STANCE,
        "segment_lengths":{"thigh":THIGH,"shin":SHIN},
        "actors":[dict(a) for a in ACTORS],"frames":frames,
        "transfer_intent":"SOURCE_NEUTRAL_JOINT_CONTACT_AND_ROOT_MOTION_ONLY_REQUIRE_PRIVATE_REMAP",
        "real_person_identity":"NOT_EVALUATED","real_body_kinematics":"NOT_EVALUATED",
    }
    validate(model)
    return model

def validate(m):
    if (m.get("schema")!=SCHEMA or m.get("classification")!=CLASS or
        m.get("source_rights")!="ORIGINAL_PROGRAMMATIC_PROCEDURAL_ONLY" or
        m.get("geometry_space")!="STYLIZED_CAMERA_XY_UNCALIBRATED" or
        m.get("fps")!=FPS or m.get("frames_count")!=N or
        m.get("duration_seconds")!=DURATION or
        m.get("transfer_intent")!="SOURCE_NEUTRAL_JOINT_CONTACT_AND_ROOT_MOTION_ONLY_REQUIRE_PRIVATE_REMAP" or
        m.get("real_person_identity")!="NOT_EVALUATED"):
        raise ValueError("INVALID_SOURCE_RIGHTS_SCHEMA_OR_CLOCK")
    fs=m.get("frames")
    if not isinstance(fs,list) or len(fs)!=N:
        raise ValueError("INVALID_FRAME_COUNT")
    ids=[a["id"] for a in m["actors"]]
    if ids!=[a["id"] for a in ACTORS]:raise ValueError("INVALID_OR_UNADMITTED_ACTORS")
    slip=0.;limb_residual=0.;minimum_root_gap=math.inf;movement={}
    for i,f in enumerate(fs):
        if f["index"]!=i or f["timestamp_ms"]!=int(round(1000*i/FPS)) or abs(f["time_s"]-i/FPS)>1e-8:
            raise ValueError("NONMONOTONIC_OR_OFFSET_CLOCK")
        if set(f["actors"])!=set(ids):raise ValueError("MISSING_OR_EXTRA_CHARACTER")
        minimum_root_gap=min(minimum_root_gap,abs(f["actors"][ids[1]]["root_x"]-f["actors"][ids[0]]["root_x"]))
        for actor in m["actors"]:
            a=f["actors"][actor["id"]]
            j=a["joints"]
            required={"pelvis","torso","neck","head"}
            for side in ("left","right"):
                required|={"hip_"+side,"knee_"+side,"ankle_"+side,
                           "shoulder_"+side,"elbow_"+side,"wrist_"+side}
            if set(j)!=required:raise ValueError("MISSING_SOURCE_JOINT")
            for p in j.values():
                if (not isinstance(p,list) or len(p)!=2 or
                    any(type(x) not in (float,int) or not math.isfinite(x) for x in p)):
                    raise ValueError("NONFINITE_SOURCE_JOINT")
            if a["facing"]!=actor["facing"]:raise ValueError("FORGED_FACING")
            for side in ("left","right"):
                hip=j["hip_"+side];knee=j["knee_"+side];ankle=j["ankle_"+side]
                for start,end,length in ((hip,knee,THIGH),(knee,ankle,SHIN)):
                    deviation=abs(math.dist(start,end)-length)
                    limb_residual=max(limb_residual,deviation)
                    if deviation>2e-7:raise ValueError("LIMB_LENGTH_CHANGED")
                if ankle[1]<GROUND_ANKLE_Y-1e-7:raise ValueError("FOOT_INTERSECTS_GROUND")
                if a["contact"][side] and abs(ankle[1]-GROUND_ANKLE_Y)>1e-7:
                    raise ValueError("PLANTED_FOOT_ABOVE_GROUND")
                if i and a["contact"][side] and fs[i-1]["actors"][actor["id"]]["contact"][side]:
                    previous=fs[i-1]["actors"][actor["id"]]["joints"]["ankle_"+side]
                    delta=math.dist(ankle,previous)
                    slip=max(slip,delta)
                    if delta>1e-7:raise ValueError("PLANTED_FOOT_SLIP")
            movement[actor["id"]]=a["root_x"]
    if minimum_root_gap<1.50:raise ValueError("ACTOR_COLLISION_OR_UNSAFE_GAP")
    for a in m["actors"]:
        end=movement[a["id"]]
        if a["facing"]*(end-a["start_x"])<1.7:
            raise ValueError("CHARACTER_NOT_APPROACHING")
    return {"source_only_qualified":True,"contact_slip_max_scene_units":round(slip,10),
            "segment_length_max_residual_scene_units":round(limb_residual,10),
            "minimum_root_separation_scene_units":round(minimum_root_gap,7),
            "frame_count":N,"characters":len(ACTORS),
            "classification":"ORIGINAL_2D_IK_STANCE_FOOT_LOCK_NOT_REAL_HUMAN"}

def main():
    parser=argparse.ArgumentParser(description="Original rights-clean two-character walking gait")
    parser.add_argument("--profile",choices=["relaxed","brisk"],default="relaxed")
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    m=generate(a.profile)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(m,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    out.write_bytes(raw)
    verdict=validate(m)
    print("WALK_W06_SOURCE_GAIT_PASS",json.dumps({
        **verdict,"profile":a.profile,
        "source_motion_sha256":hashlib.sha256(raw).hexdigest(),
        "source_motion_path":str(out)
    },sort_keys=True))

if __name__=="__main__":main()
