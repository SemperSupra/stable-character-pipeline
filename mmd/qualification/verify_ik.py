#!/usr/bin/env python3
"""G10a pure-Python independent PMX IK metadata preservation and negative controls."""
import argparse
import hashlib
import json
from pathlib import Path
from verify_interchange import parse_glb

def inspect(g):
    bones=g.get("extras",{}).get("mmd",{}).get("bones",[])
    names=["腰","ひざ","足首","足ＩＫ"]
    if len(bones)!=4 or [x.get("name") for x in bones]!=names:
        raise AssertionError("original four PMX rig bones/names lost in extras")
    if [x.get("parent") for x in bones]!=[-1,0,1,-1]:
        raise AssertionError("PMX kinematic chain parentage drift")
    iknodes=[x for x in g.get("nodes",[]) if x.get("name")=="足ＩＫ"]
    if len(iknodes)!=1:
        raise AssertionError("original Japanese IK control node missing")
    ik=iknodes[0].get("extras",{}).get("mmd",{}).get("ik")
    if not isinstance(ik,dict):
        raise AssertionError("MMD-specific IK targets/links were discarded")
    if ik.get("target")!=2 or [x.get("bone") for x in ik.get("links",[])]!=[1,0]:
        raise AssertionError("IK goal/chain source topology not preserved")
    if ik.get("loop")!=24 or abs(ik.get("limit_angle",0)-.45)>.0001:
        raise AssertionError("source MMD IK iterations/angle cap corrupted")
    if len(g.get("skins",[]))!=1 or len(g["skins"][0].get("joints",[]))!=4:
        raise AssertionError("GLB missing four-joint skin")
    return {"source_bone_names":names,"source_ik":ik,
            "skin_joint_count":len(g["skins"][0]["joints"]),
            "animation_channels":sum(len(a.get("channels",[])) for a in g.get("animations",[]))}

def negative(g):
    clone=json.loads(json.dumps(g))
    for x in clone["nodes"]:
        if x.get("name")=="足ＩＫ":
            x["extras"]["mmd"]["ik"]["links"][0]["bone"]=3
            break
    try: inspect(clone)
    except AssertionError: pass
    else: raise AssertionError("accepted invalid IK link topology")
    clone=json.loads(json.dumps(g))
    clone["extras"]["mmd"]["bones"][2]["parent"]=-1
    try: inspect(clone)
    except AssertionError: pass
    else: raise AssertionError("accepted amputated ankle parent chain")
    print("EXPECTED_REJECTIONS invalid_IK_link broken_ankle_parent")

def main():
    p=argparse.ArgumentParser()
    for n in ("ik","no-ik","out"):
        p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args()
    ik,ib=parse_glb(a.ik)
    fk,fb=parse_glb(a.no_ik)
    k1=inspect(ik)
    k2=inspect(fk)
    negative(ik)
    receipt={
      "schema":"scp.mmd.ik.structural.v1",
      "status":"PASS_DIRECT_CONVERTER_SOURCE_IK_STRUCTURAL_PRESERVATION",
      "ik":k1,
      "no_ik":k2,
      "ik_baked_output_sha256":hashlib.sha256(a.ik.read_bytes()).hexdigest(),
      "fk_only_output_sha256":hashlib.sha256(a.no_ik.read_bytes()).hexdigest(),
      "ik_vs_noik_bytes_differ":ib!=fb or ik!=fk,
      "scope":"real source PMX IK topology and dual converter paths; NOT foot-contact precision or native MMD CCD solver parity",
      "unqualified":["Blender IK solve","foot lock","physics contact","native MMD CCD vs Blender","retargets","human gait"]
    }
    a.out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    main()
