#!/usr/bin/env python3
"""Aster-only skinned original trouser weight trials; preserve 35-joint source.

Falsifiable hypotheses from R009 #340 native 72f BVH / p99 edge-strain witness:
the source-authored tube ending at knee / short cropped hem is given excessive
ankle influence, and hip-to-knee tube influence starts late. Fixes here are
EXPERIMENTS, not an animation/anatomical/garment-physics or release acceptance.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

from rig35_v2 import glb_pack
from verify_original_glb import accessory,decode
from humanization_v2 import v1

SCHEMA="scp.r009.aster_original_trouser_skinweight_trials.v1"
OPTIONS={
 "hem_30":("baseline",.30),
 "hem_50":("baseline",.50),
 "hip_linear":("linear",1.),
 "hip_smooth":("smooth",1.),
 "combo_hem30_linear":("linear",.30),
}
ACTOR="AsterOriginal"
SLOT="style_bottom"


def woff(doc,accessor,bb):
    a=doc["accessors"][accessor]
    view=doc["bufferViews"][a["bufferView"]]
    if (a["type"]!="VEC4" or a["componentType"]!=5126 or
        a.get("normalized",False) or "byteStride" in view or
        view["buffer"]!=0 or view["byteLength"]!=a["count"]*16):
        raise ValueError("TROUSER_WEIGHT_ACCESSOR_UNSUPPORTED")
    off=view.get("byteOffset",0)+a.get("byteOffset",0)
    if off<0 or off+a["count"]*16>len(bb):
        raise ValueError("TROUSER_WEIGHT_ACCESSOR_BOUNDS")
    return off,a["count"]


def pt_on_bone(xyz,start,end):
    axis=[end[k]-start[k] for k in range(3)]
    denom=sum(v*v for v in axis)
    if denom<.01:raise ValueError("TROUSER_BONE_AXIS_INVALID")
    t=sum((xyz[k]-start[k])*axis[k] for k in range(3))/denom
    return max(0.,min(1.,t))


def influenced(w,ids,xyz,node_names,hip_rule,hem_factor):
    # Original JOINTS[0:2] are source h.v1.Geometry tube bone_a,b.
    # Do not touch pelvis/spine yoke, body, other materials, or other actor.
    bones=tuple(node_names.get(j) for j in ids[:2])
    a,b=bones
    if a in ("hip_L","hip_R") and b==a.replace("hip_","knee_"):
        if hip_rule=="baseline":return None,"hip_unchanged"
        side=a[-1]
        t=pt_on_bone(xyz,v1.POS["hip_"+side],v1.POS["knee_"+side])
        if hip_rule=="linear":q=t
        elif hip_rule=="smooth":q=t*t*(3.-2.*t)
        else:raise ValueError("TROUSER_HIP_RULE_UNKNOWN")
        return (1.-q,q,0.,0.),"hip_reblend"
    if a in ("knee_L","knee_R") and b==a.replace("knee_","ankle_"):
        if hem_factor>=1.:return None,"hem_unchanged"
        q=w[1]*hem_factor
        return (1.-q,q,0.,0.),"hem_ankle_reduced"
    return None,"non_leg"


def apply(input_glb,strict_receipt,out_glb,receipt,variant):
    if variant not in OPTIONS:raise ValueError("TROUSER_VARIANT_UNKNOWN")
    paths=[Path(v).resolve() for v in
           (input_glb,strict_receipt,out_glb,receipt)]
    if len(set(paths))!=4:raise ValueError("TROUSER_SOURCE_OVERWRITE_REFUSED")
    src,meta,out,re=paths
    if out.exists() or re.exists():raise FileExistsError("TROUSER_OUTPUT_EXISTS")
    raw=src.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
    r=json.loads(meta.read_text())
    if r.get("schema")!="scp.r009.strict_mage_portable.v1.receipt" or (
            r.get("derived_sha256")!=sha) or (
            r.get("choices")!={"AsterOriginal":"adventure",
                             "JuniperOriginal":"adventure"}):
        raise ValueError("TROUSER_STRICT_SOURCE_RECEIPT_MISMATCH")
    d,binary=decode(raw)
    if (d.get("extras",{}).get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
        or d.get("extras",{}).get("strict_mage_portable",{}).get("schema")!=
        "scp.r009.strict_mage_portable.v1" or len(d.get("skins",[]))!=2 or
        any(len(s.get("joints",[]))!=35 for s in d["skins"])):
        raise ValueError("TROUSER_SOURCE_NOT_ORIGINAL_35J")
    names={n.get("name"):i for i,n in enumerate(d["nodes"])}
    node=d["nodes"][names[ACTOR+"_Wardrobe_"+SLOT]]
    if node.get("skin")!=0 or names[ACTOR+"_Wardrobe_"+SLOT] not in (
            d["nodes"][names[ACTOR+"_SceneRoot"]].get("children",[])):
        raise ValueError("TROUSER_SOURCE_NOT_ACTIVE_ACTOR_LAYER")
    skin=d["skins"][0]
    node_names={i:d["nodes"][node_id]["name"].removeprefix(ACTOR+"_")
                for i,node_id in enumerate(skin["joints"])}
    bb=bytearray(binary)
    mesh=d["meshes"][node["mesh"]]
    used_accessors=set()
    counts={"hip_reblend":0,"hem_ankle_reduced":0,"hip_unchanged":0,
            "hem_unchanged":0,"non_leg":0}
    hip_rule,hem_factor=OPTIONS[variant]
    for primitive in mesh["primitives"]:
        at=primitive["attributes"]
        weights_idx=at["WEIGHTS_0"]
        if weights_idx in used_accessors:raise ValueError("TROUSER_SHARED_WEIGHTS")
        used_accessors.add(weights_idx)
        positions=accessory(d,binary,at["POSITION"])
        joints=accessory(d,binary,at["JOINTS_0"])
        old=accessory(d,binary,weights_idx)
        off,count=woff(d,weights_idx,bb)
        if len(positions)!=len(joints) or len(old)!=count:
            raise ValueError("TROUSER_VERTEX_COUNT_DRIFT")
        for i,(xyz,j,w) in enumerate(zip(positions,joints,old)):
            if not all(math.isfinite(v) for v in xyz+w) or (
                any(v<0 for v in w) or abs(sum(w)-1)>2e-3):
                raise ValueError("TROUSER_BAD_SOURCE_VERTEX_OR_WEIGHT")
            updated,category=influenced(w,j,xyz,node_names,hip_rule,hem_factor)
            if updated is None:
                counts[category]+=1
                continue  # preserve raw weight bytes for unmodified vertices
            if abs(sum(updated)-1)>1e-5 or any(x<0 or x>1 for x in updated):
                raise ValueError("TROUSER_BAD_WEIGHT_MUTATION")
            if any(abs(x-y)>1e-6 for x,y in zip(w,updated)):
                struct.pack_into("<4f",bb,off+i*16,*updated)
                counts[category]+=1
    if hip_rule!="baseline" and counts["hip_reblend"]<100:
        raise ValueError("TROUSER_HIP_REBLEND_DID_NOT_HAPPEN")
    if hem_factor<1 and counts["hem_ankle_reduced"]<40:
        raise ValueError("TROUSER_HEM_REBLEND_DID_NOT_HAPPEN")
    d.setdefault("extras",{})["aster_trouser_weight_trial"]={
        "schema":SCHEMA,"source_sha256":sha,"variant":variant,
        "original_joints_35_preserved":True,"original_72f_animation_preserved":True,
        "garment_fit_accepted":False,"surface_collision_accepted":False,
    }
    derived=glb_pack(d,bb)
    result={"schema":SCHEMA+".receipt","source_sha256":sha,
            "derived_sha256":hashlib.sha256(derived).hexdigest(),
            "actor":ACTOR,"slot":SLOT,"variant":variant,
            "counts":counts,"original_vertex_positions_preserved":True,
            "original_joint_indices_preserved":True,
            "original_72f_animations_preserved":True,
            "human_anatomy_accepted":False,"garment_clearance_accepted":False,
            "source_original":True,"release_held":True}
    out.parent.mkdir(parents=True,exist_ok=True)
    re.parent.mkdir(parents=True,exist_ok=True)
    with out.open("xb") as f:f.write(derived)
    with re.open("x",encoding="utf8") as f:
        f.write(json.dumps(result,indent=2,sort_keys=True)+"\n")
    if hashlib.sha256(src.read_bytes()).hexdigest()!=sha:
        raise ValueError("TROUSER_SOURCE_CHANGED_DURING_TRIAL")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True);p.add_argument("--strict-receipt",required=True)
    p.add_argument("--out",required=True);p.add_argument("--receipt",required=True)
    p.add_argument("--variant",required=True,choices=sorted(OPTIONS))
    a=p.parse_args()
    print(json.dumps(apply(a.input,a.strict_receipt,a.out,
                           a.receipt,a.variant),sort_keys=True))
