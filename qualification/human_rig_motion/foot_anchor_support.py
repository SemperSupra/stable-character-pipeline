#!/usr/bin/env python3
"""Read-only original 35-joint foot-anchor support/slip screening.

The foot *joint origins* are NOT evaluated shoe soles, true terrain, force,
human gait acceptance, normative JCS/ROM, or signed mesh penetration.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "human_rig_observer"))
from observe import ACTORS, InvalidModel, analyze, hierarchy, load_glb, require, values

FRAMES=72
FPS=12
ROLES=("heel","ball","toe")

def norm(q):
    require(len(q)==4 and all(math.isfinite(c) for c in q),"bad quaternion")
    mag=math.sqrt(sum(c*c for c in q))
    require(abs(mag-1.)<=.002,"unnormalized orientation")
    return tuple(c/mag for c in q)

def qmul(a,b):
    x,y,z,w=a; i,j,k,v=b
    return norm((w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,
                 w*k+x*j-y*i+z*v,w*v-x*i-y*j-z*k))

def qrotate(q,v):
    x,y,z,w=norm(q)
    vx,vy,vz=v
    tx=2*(y*vz-z*vy);ty=2*(z*vx-x*vz);tz=2*(x*vy-y*vx)
    return (vx+w*tx+y*tz-z*ty,vy+w*ty+z*tx-x*tz,vz+w*tz+x*ty-y*tx)

def add(a,b):
    return tuple(x+y for x,y in zip(a,b))

def read_channels(doc,blob):
    animation=doc["animations"][0]
    channel_map={}
    for channel in animation["channels"]:
        target=channel["target"];node=target["node"];path=target["path"]
        require(type(node) is int and 0<=node<len(doc["nodes"]),"bad target node")
        require(path in ("translation","rotation","scale","weights"),"unsupported target")
        key=(node,path)
        require(key not in channel_map,"duplicate animation target")
        sampler=animation["samplers"][channel["sampler"]]
        require(sampler.get("interpolation","LINEAR")=="LINEAR","unsampled nonlinear curve")
        times=values(doc,blob,sampler["input"])
        require(len(times)==FRAMES and all(abs(t[0]-i/FPS)<1e-4 for i,t in enumerate(times)),
                "wrong original animation clock")
        if path in ("translation","rotation"):
            sample=values(doc,blob,sampler["output"])
            require(len(sample)==FRAMES,"missing track samples")
            require(all(len(row)==(3 if path=="translation" else 4)
                        and all(math.isfinite(x) for x in row) for row in sample),"bad track")
            channel_map[key]=sample
        elif path=="scale":
            raise InvalidModel("animated hierarchy scale unsupported")
    return channel_map

def node_tracks(doc,blob):
    parents=hierarchy(doc)
    tracks=read_channels(doc,blob)
    nodes=doc["nodes"]
    cache={}
    def world_pose(i,frame):
        key=(i,frame)
        if key in cache:return cache[key]
        node=nodes[i]
        require("matrix" not in node,"explicit matrix unsupported")
        scale=node.get("scale",(1,1,1))
        require(len(scale)==3 and all(abs(c-1.)<1e-6 for c in scale),
                "nonunit static scale unsupported")
        animated_t=tracks.get((i,"translation"))
        animated_q=tracks.get((i,"rotation"))
        t=tuple(animated_t[frame]) if animated_t else tuple(node.get("translation",(0,0,0)))
        q=norm(animated_q[frame] if animated_q else node.get("rotation",(0,0,0,1)))
        require(len(t)==3 and all(math.isfinite(c) for c in t),"bad local translation")
        parent=parents.get(i)
        if parent is None:pose=(t,q)
        else:
            pt,pq=world_pose(parent,frame)
            pose=(add(pt,qrotate(pq,t)),qmul(pq,q))
        cache[key]=pose
        return pose
    return world_pose

def inspect(raw):
    original=analyze(raw)
    doc,blob=load_glb(raw)
    names={n.get("name"):i for i,n in enumerate(doc["nodes"])}
    require(len(names)==len(doc["nodes"]),"duplicate node names")
    world=node_tracks(doc,blob)
    actors={}
    for actor in ACTORS:
        positions={}
        for side in ("L","R"):
            for role in ROLES:
                name=actor+"_"+role+"_"+side
                require(name in names,"missing original foot marker "+name)
                positions[role+"_"+side]=[world(names[name],f)[0] for f in range(FRAMES)]
        # This is an inferred source extremum, not a camera-observed floor.
        ground=min(p[1] for points in positions.values() for p in points)
        feet={}
        for side in ("L","R"):
            rows={}
            for role in ROLES:
                label=role+"_"+side
                coords=positions[label]
                near=[p[1]-ground<=.025 for p in coords]
                speeds=[math.hypot(b[0]-a[0],b[2]-a[2])*FPS
                        for a,b in zip(coords,coords[1:])]
                potential=[i for i in range(FRAMES-1) if near[i] and near[i+1]]
                skates=[i for i in potential if speeds[i]>.24]
                rows[label]={"samples":FRAMES,
                             "min_joint_y_m":round(min(p[1] for p in coords),6),
                             "max_joint_y_m":round(max(p[1] for p in coords),6),
                             "source_support_candidate_steps":len(potential),
                             "possible_anchor_skate_indices":skates,
                             "max_horizontal_anchor_speed_m_s":round(max(speeds),6),
                             "support_tolerance_m":.025,
                             "skate_screen_speed_m_s":.24}
            feet[side]=rows
        actors[actor]={"relative_joint_minimum_y_m":round(ground,6),"feet":feet}
    return {"schema":"scp.r009.original_35j_joint_anchor_support_screen.v1",
            "source_glb_sha256":hashlib.sha256(raw).hexdigest(),
            "independent_structure_sha256":original["sha256"],
            "frames":FRAMES,"fps":FPS,"actors":actors,
            "floor_basis":"minimum of source foot joint origins, NOT camera observed terrain",
            "foot_sole_mesh_penetration":"NOT_MEASURED",
            "garment_body_collision":"NOT_MEASURED",
            "independent_anatomical_JCS_ROM":"NOT_PROVEN",
            "human_gait_accepted":False,"release_or_CPE_admission":False,"model_mutation":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--glb",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    target=Path(a.out)
    require(not target.exists(),"refuse overwrite receipt")
    raw=Path(a.glb).read_bytes()
    require(len(raw)<64*1024*1024,"oversize GLB")
    target.write_text(json.dumps(inspect(raw),sort_keys=True,indent=2)+"\n")
    print("SOURCE_JOINT_SUPPORT_SCREEN_NOT_REAL_FOOT_SOLE_OR_GAIT_ACCEPTANCE")

if __name__=="__main__":
    main()
