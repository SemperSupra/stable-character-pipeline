#!/usr/bin/env python3
"""Original-source phase-aware IK to 35-joint skinned glTF research candidate.

Adapted mathematical form from public source-owner gait PR #290, head
aeeccaf6b00a55483e8b9e503d8aa7fb4a3c7532. Local stdlib reimplementation
for the owner-original 35-joint rig; no protected or third-party motion data.
Every source mesh/material/skin remains unchanged; human gait remains UNKNOWN.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from rig35_v2 import glb_pack, add_accessor
from verify_original_glb import decode

FPS=12
FRAMES=72
PERIOD=1.6
STANCE=.60
SPEED=2.56/6
FWD=.16
HIP_Y=.89
ANKLE_Y=.115
THIGH=math.hypot(.4,.01414213562373095)
SHANK=math.hypot(.375,.01)
BOUNDS={"hip":(-.40,.70),"knee":(-1.30,0),"ankle":(-.40,.72)}

def smooth(x):
    x=max(0,min(1,x))
    return x*x*(3-2*x)

def hermite(a,b,m0,m1,u):
    return (2*u**3-3*u**2+1)*a + (u**3-2*u**2+u)*m0 + (-2*u**3+3*u**2)*b + (u**3-u**2)*m1

def leg(phase,dy):
    p=phase%1.
    if p<STANCE:
        f=FWD-SPEED*PERIOD*p
        h=.04*smooth((p-.45)/.15)
        ay=ANKLE_Y+h
        pitch=.055*(1-smooth(p/.12))-.20*smooth((p-.46)/.14)
        stage="stance"
    else:
        u=(p-STANCE)/(1-STANCE)
        f=hermite(FWD-SPEED*PERIOD*STANCE,FWD,
                  -SPEED*PERIOD*(1-STANCE),-SPEED*PERIOD*(1-STANCE),u)
        ay=ANKLE_Y+.04*(1-u)**2 + .100*max(0,math.sin(math.pi*(u+.90*u*(1-u))))**1.15
        pitch=-.20-.05*smooth(u/.2)+.25*smooth((u-.55)/.45)+.05*smooth((u-.82)/.18)
        stage="swing"
    fy=ay-(HIP_Y+dy)
    dist=math.hypot(f,fy)
    if dist<abs(THIGH-SHANK)-1e-6 or dist>THIGH+SHANK+1e-6:
        raise ValueError("IK_UNREACHABLE")
    dist=min(dist,THIGH+SHANK-1e-7)
    along=(THIGH*THIGH-SHANK*SHANK+dist*dist)/(2*dist*dist)
    high=math.sqrt(max(0,THIGH*THIGH-(along*dist)**2))
    knee_f=along*f+high*(-fy)/dist
    knee_y=along*fy+high*f/dist
    thigh=math.atan2(knee_f,-knee_y)-math.atan2(-.01,.4)
    lower=math.atan2(f-knee_f,-(fy-knee_y))-math.atan2(-.01,.375)
    knee=lower-thigh
    ankle=-(thigh+knee)+pitch
    angles={"hip":thigh,"knee":knee,"ankle":ankle}
    for role,a in angles.items():
        lo,hi=BOUNDS[role]
        if not lo-1e-4<=a<=hi+1e-4:
            raise ValueError("ROM_BOUNDS_"+role)
    return {"phase":p,"stage":stage,"ankle_y":ay,"fwd":f,
            "knee_fwd":knee_f,"angles":angles}

def pose(frame,which):
    t=frame/FPS
    p=(t/PERIOD+(0 if which==0 else .22))%1.
    dy=-.006-.012*(.5+.5*math.cos(4*math.pi*p))
    legs={"L":leg(p,dy),"R":leg((p+.5)%1,dy)}
    drive=math.cos(2*math.pi*p)
    arms={"L":{"shoulder":-.32*drive,"elbow":.34-.25*drive},
          "R":{"shoulder":.32*drive,"elbow":.34+.25*drive}}
    return {"phase":p,"pelvis_delta":dy,"legs":legs,"arms":arms}

def quat(angle):
    return (math.sin(angle/2),0.,0.,math.cos(angle/2))

def animate(input_glb,output_glb):
    raw=Path(input_glb).read_bytes()
    d,binary=decode(raw)
    if d["extras"].get("rig_profile")!="ORIGINAL_FUNCTIONAL_35JOINT_RESEARCH":
        raise ValueError("REQUIRES_EXACT_SOURCE_RIG35")
    if len(d["skins"])!=2 or any(len(s["joints"])!=35 for s in d["skins"]):
        raise ValueError("REQUIRES_DUAL_35JOINT")
    before={k:json.dumps(d[k],sort_keys=True) for k in ("meshes","skins","materials")}
    nodeids={n["name"]:i for i,n in enumerate(d["nodes"])}
    anim=d["animations"][0]
    ids={(c["target"]["node"],c["target"]["path"]):c["sampler"] for c in anim["channels"]}
    timeacc=anim["samplers"][0]["input"]
    buffer=bytearray(binary)
    controls=0
    for which,actor in enumerate(("AsterOriginal","JuniperOriginal")):
        poses=[pose(f,which) for f in range(FRAMES)]
        def track(role,path,arr,fmt):
            nonlocal controls
            name=actor+"_"+role
            if name not in nodeids:raise ValueError("MISSING_RIG_ROLE:"+name)
            node=nodeids[name]
            accessor=add_accessor(d,buffer,arr,fmt,3 if fmt=="VEC3" else 4)
            key=(node,path)
            if key in ids:
                anim["samplers"][ids[key]]["output"]=accessor
            else:
                si=len(anim["samplers"])
                anim["samplers"].append({"input":timeacc,"output":accessor,"interpolation":"LINEAR"})
                anim["channels"].append({"sampler":si,
                      "target":{"node":node,"path":path}})
                ids[key]=si
            controls+=1
        pelvis=[]
        for p in poses:pelvis.extend([0,.93+p["pelvis_delta"],0])
        track("pelvis","translation",pelvis,"VEC3")
        for side in ("L","R"):
            for role in ("hip","knee","ankle","shoulder","elbow",
                         "clavicle","heel","ball","toe"):
                values=[]
                for p in poses:
                    foot=p["legs"][side]
                    if role in ("hip","knee","ankle"):
                        angle=foot["angles"][role]
                    elif role in ("shoulder","elbow"):
                        angle=p["arms"][side][role]
                    elif role=="clavicle":
                        angle=.022*math.sin(2*math.pi*foot["phase"])
                    elif role=="heel":
                        angle=-.035*(1-smooth(foot["phase"]/.10)) if foot["stage"]=="stance" else 0
                    elif role=="ball":
                        angle=.12*smooth((foot["phase"]-.43)/.17) if foot["stage"]=="stance" else 0
                    else:
                        angle=.20*smooth((foot["phase"]-.46)/.14) if foot["stage"]=="stance" else 0
                    values.extend(quat(angle))
                track(role+"_"+side,"rotation",values,"VEC4")
        for role in ("spine","head"):
            values=[]
            for p in poses:
                a=(.012 if role=="spine" else -.010)*math.sin(2*math.pi*p["phase"])
                values.extend(quat(a))
            track(role,"rotation",values,"VEC4")
    assert controls==42
    # Exact source-owner heading semantics of unmerged public PR #289:
    # local forward -Z rotates into +X for Aster, -X for Juniper.
    for actor,degrees in (("AsterOriginal",-90),("JuniperOriginal",90)):
        root=nodeids[actor+"_SceneRoot"]
        if "rotation" in d["nodes"][root] or "matrix" in d["nodes"][root]:
            raise ValueError("ROOT_ALREADY_ROTATED")
        if (root,"rotation") in ids:
            raise ValueError("ANIMATED_ROOT_YAW_REFUSED")
        angle=math.radians(degrees)/2
        d["nodes"][root]["rotation"]=[0.0,math.sin(angle),0.0,math.cos(angle)]
    assert all(json.dumps(d[k],sort_keys=True)==before[k] for k in before)
    d["extras"]["gait_profile"]="ORIGINAL_PHASE_AWARE_35JOINT_IK_RESEARCH"
    d["extras"]["heading_profile"]="OWNER_ORIGINAL_PR289_NEG90_POS90_ROOT_YAW"
    d["extras"]["gait_source_reference"]="public-original #290 @ aeeccaf6b00a55483e8b9e503d8aa7fb4a3c7532"
    d["extras"]["human_gait_acceptance"]="UNKNOWN"
    output=glb_pack(d,buffer)
    Path(output_glb).write_bytes(output)
    return {"schema":"scp.r009.original_phase_gait35.v1",
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "derived_sha256":hashlib.sha256(output).hexdigest(),
        "actors":2,"rig_joints_each":35,"frames":72,
        "modified_animation_targets":controls,
        "heading_yaw_deg":{"AsterOriginal":-90,"JuniperOriginal":90},
        "mesh_skin_materials_unchanged":True,
        "foot_phases":"60pct stance / 40pct swing, bounded kinematic proxy",
        "human_gait_acceptance":"UNKNOWN_NOT_QUALIFIED"}

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--input",required=True)
    a.add_argument("--output",required=True)
    a.add_argument("--receipt",required=True)
    opts=a.parse_args()
    result=animate(opts.input,opts.output)
    Path(opts.receipt).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))
