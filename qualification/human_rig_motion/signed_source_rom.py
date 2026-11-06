#!/usr/bin/env python3
"""Independent signed source-local X gait screen for fictional original 35-joint humans.

The source author's hip/knee/ankle angular bounds are NOT normative biological
human JCS, clinical ROM, gait, body/cloth collision or physical plausibility.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

FPS=12
FRAMES=72
ACTORS=("AsterOriginal","JuniperOriginal")
SOURCE_BOUNDS={"hip":(-.40,.70),"knee":(-1.30,0.),"ankle":(-.40,.72)}

class InvalidGait(ValueError): pass

def require(ok,message):
    if not ok:raise InvalidGait(message)

def sagittal(q):
    require(len(q)==4 and all(math.isfinite(x) for x in q),"nonfinite or wrong-size quaternion")
    require(abs(sum(x*x for x in q)-1.)<=.002,"unnormalized quaternion")
    require(abs(q[1])<.0002 and abs(q[2])<.0002,"not a source-local X-only joint")
    angle=2*math.atan2(q[0],q[3])
    return math.atan2(math.sin(angle),math.cos(angle))

def measure(angles,bounds):
    require(len(angles)==FRAMES,"not 72 source samples")
    require(all(math.isfinite(x) for x in angles),"nonfinite angle")
    lower,upper=bounds
    violations=[i for i,x in enumerate(angles) if not lower-.00001<=x<=upper+.00001]
    steps=[abs(y-x) for x,y in zip(angles,angles[1:])]
    return {"samples":len(angles),"min_rad":round(min(angles),6),
            "max_rad":round(max(angles),6),"max_step_rad":round(max(steps),6),
            "source_limit_violations":violations,"source_limits_rad":[lower,upper],
            "signed_axis":"original source local X; NOT ISB human JCS"}

def glb(raw):
    require(len(raw)>=36 and raw[:4]==b"glTF","invalid GLB header")
    _,version,total=struct.unpack_from("<4sII",raw)
    require(version==2 and total==len(raw),"GLB size or version mismatch")
    jsonlen,typ=struct.unpack_from("<I4s",raw,12)
    require(typ==b"JSON" and 20+jsonlen+8<=len(raw),"missing GLB JSON")
    doc=json.loads(raw[20:20+jsonlen]);offset=20+jsonlen
    binlen,bintyp=struct.unpack_from("<I4s",raw,offset)
    require(bintyp==b"BIN\0" and offset+8+binlen==len(raw),"bad GLB BIN")
    require(doc.get("extras",{}).get("source_class")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","unadmitted source")
    return doc,raw[offset+8:]

def values(doc,buf,index):
    require(type(index) is int and 0<=index<len(doc["accessors"]),"bad accessor index")
    accessor=doc["accessors"][index]
    require(accessor.get("componentType")==5126 and accessor.get("type") in ("SCALAR","VEC4"),
            "unapproved animation accessor")
    require(type(accessor.get("count")) is int and accessor["count"]==FRAMES,"wrong channel samples")
    view=doc["bufferViews"][accessor["bufferView"]]
    require(view.get("buffer")==0 and "byteStride" not in view and "sparse" not in accessor,
            "unsupported strided/sparse data")
    width=4 if accessor["type"]=="SCALAR" else 16
    start=view.get("byteOffset",0)+accessor.get("byteOffset",0)
    require(start>=0 and start+FRAMES*width<=len(buf) and
            start+FRAMES*width<=view.get("byteOffset",0)+view["byteLength"],
            "out-of-buffer animation accessor")
    return list(struct.iter_unpack("<"+"f"*(width//4),buf[start:start+FRAMES*width]))

def inspect(data):
    doc,blob=glb(data)
    require(len(doc.get("skins",[]))==2 and all(len(s.get("joints",[]))==35 for s in doc["skins"]),
            "not two original 35-joint rigs")
    require(len(doc.get("animations",[]))==1,"wrong animation count")
    anim=doc["animations"][0]
    targets={};nodes=doc["nodes"]
    for channel in anim["channels"]:
        target=channel["target"];node=target["node"]
        require(type(node) is int and 0<=node<len(nodes),"invalid node index")
        key=(nodes[node].get("name"),target["path"])
        require(key not in targets,"duplicate animation target")
        targets[key]=channel["sampler"]
    records={};total_violations=0
    for actor in ACTORS:
        rows={}
        for side in ("L","R"):
            for role,bounds in SOURCE_BOUNDS.items():
                key=(actor+"_"+role+"_"+side,"rotation")
                require(key in targets,"missing signed gait target "+repr(key))
                sampler=anim["samplers"][targets[key]]
                times=values(doc,blob,sampler["input"])
                require(all(abs(t[0]-i/FPS)<.0001 for i,t in enumerate(times)),
                        "source clock drift")
                quats=values(doc,blob,sampler["output"])
                entry=measure([sagittal(q) for q in quats],bounds)
                total_violations+=len(entry["source_limit_violations"])
                rows[role+"_"+side]=entry
        records[actor]=rows
    return {"schema":"scp.r009.original_sagittal_source_bounds.v1",
            "source_glb_sha256":hashlib.sha256(data).hexdigest(),
            "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "source_rigs":2,"source_rig_joints_each":35,
            "tracks_observed":12,"frames_per_track":FRAMES,
            "actors":records,"total_authoring_limit_violations":total_violations,
            "source_authored_limit_verdict":"SOURCE_LIMIT_SCREEN_PASS"
                if not total_violations else "SOURCE_LIMIT_SCREEN_FAIL",
            "independent_human_JCS":"NOT_PROVEN","normative_human_ROM":"NOT_PROVEN",
            "body_foot_skate_collision":"NOT_RUN",
            "scientific_human_gait_accepted":False,"release_or_CPE_admission":False,
            "model_mutation":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--glb",required=True)
    parser.add_argument("--out",required=True)
    opts=parser.parse_args()
    dest=Path(opts.out);require(not dest.exists(),"refuse overwrite evidence")
    raw=Path(opts.glb).read_bytes();require(len(raw)<64*1024*1024,"bounded GLB size")
    result=inspect(raw)
    dest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("SIGNED_ORIGINAL_JOINT_AUTHORED_LIMITS_ONLY",result["source_authored_limit_verdict"])

if __name__=="__main__":main()
