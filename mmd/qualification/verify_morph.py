#!/usr/bin/env python3
"""G9 pure Python independent Blender/direct-converter glTF morph checker."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from verify_interchange import parse_glb
from PIL import Image, ImageChops


def accessor(g,raw,index):
    x=g["accessors"][index]
    if x.get("type")!="SCALAR" or x.get("componentType")!=5126 or x.get("sparse"):
        raise ValueError("unexpected nonfloat/scalar/sparse animation accessor")
    view=g["bufferViews"][x["bufferView"]]
    stride=view.get("byteStride",4)
    if stride<4 or view.get("buffer",0)!=0 or x["count"]>2500:
        raise ValueError("invalid morph animation view")
    off=view.get("byteOffset",0)+x.get("byteOffset",0)
    values=[]
    for k in range(x["count"]):
        at=off+k*stride
        if at+4>len(raw):
            raise ValueError("accessor out of bounds")
        value=struct.unpack_from("<f",raw,at)[0]
        if not math.isfinite(value):
            raise ValueError("nonfinite morph sample")
        values.append(value)
    return values


def inspect(g,raw):
    morphs=[]
    for mesh in g.get("meshes",[]):
        prims=mesh.get("primitives",[])
        if not prims:
            continue
        targets=prims[0].get("targets",[])
        if len(targets)>=2 and all("POSITION" in t for t in targets[:2]):
            morphs.append((mesh,len(targets)))
    if not morphs:
        raise AssertionError("glTF exported no two genuine vertex morph targets")
    target_count=morphs[0][1]
    channels=[]
    for a in g.get("animations",[]):
        for ch in a.get("channels",[]):
            if ch.get("target",{}).get("path")!="weights":
                continue
            sampler=a["samplers"][ch["sampler"]]
            times=accessor(g,raw,sampler["input"])
            weights=accessor(g,raw,sampler["output"])
            if len(times)<3 or len(times)>100 or len(weights)!=len(times)*target_count:
                raise AssertionError("morph key values count inconsistent with target count")
            if abs(times[0])>1e-4 or abs(times[-1]-1.0)>1e-3:
                raise AssertionError("VMD temporal origin drift in glTF morphs")
            if any(b<=a for a,b in zip(times,times[1:])):
                raise AssertionError("morph times unordered/repeated")
            sample_groups=[weights[k*target_count:(k+1)*target_count] for k in range(len(times))]
            mid=min(range(len(times)),key=lambda k:abs(times[k]-.5))
            first, middle, last=sample_groups[0],sample_groups[mid],sample_groups[-1]
            if max(abs(x) for x in first)>.05:
                raise AssertionError("morph is activated at VMD frame 0")
            if sum(x>.92 for x in middle)<1 or not any(.20<x<.50 for x in middle):
                raise AssertionError("two distinct face morphs not reflected at frame 15")
            if sum(x>.92 for x in last)<1 or sum(x>.10 for x in last)>1:
                raise AssertionError("final smile/open blink morph state wrong")
            channels.append({"target_node":ch["target"]["node"],"frames":len(times),
                "source_morph_target_count":target_count,"at_0":first,"at_15":middle,"at_30":last,
                "timeline_seconds":[times[0],times[-1]]})
    if not channels:
        raise AssertionError("animated morph weights channel omitted from GLB")
    return channels


def negative():
    try:
        inspect({"meshes":[]},b"")
    except AssertionError:
        pass
    else:
        raise AssertionError("accepted no morph targets")
    g={"accessors":[{"type":"SCALAR","componentType":5126,"bufferView":0,"count":1}],
       "bufferViews":[{"buffer":0,"byteLength":4}]}
    try:
        accessor(g,struct.pack("<f",float("nan")),0)
    except ValueError:
        pass
    else:
        raise AssertionError("accepted NaN weights")
    print("EXPECTED_REJECTIONS missing_targets nonfinite_morph_weight")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--blender",type=Path)
    p.add_argument("--direct",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        negative()
        return
    assert a.blender and a.direct and a.out
    b,bb=parse_glb(a.blender)
    d,db=parse_glb(a.direct)
    bt=inspect(b,bb)
    dt=inspect(d,db)
    # Both engines must independently preserve two separate simultaneous morph weights.
    base=dt[0]
    rival=bt[0]
    def nearly_unordered(x,y,tol=.11):
        xx=sorted(x)
        yy=sorted(y)
        assert len(xx)==len(yy) and max(abs(i-j) for i,j in zip(xx,yy))<tol,(xx,yy)
    for pos in ("at_0","at_15","at_30"):
        nearly_unordered(base[pos],rival[pos])
    report={
      "schema":"scp.mmd.morph.interchange.v1",
      "status":"PASS_TWO_ENGINE_REAL_VERTEX_MORPH_VMD_WEIGHT_PARITY",
      "blender_sha256":hashlib.sha256(a.blender.read_bytes()).hexdigest(),
      "direct_sha256":hashlib.sha256(a.direct.read_bytes()).hexdigest(),
      "blender_animation":bt,
      "direct_animation":dt,
      "scope":"PMX vertex morph/VMD weights; not likeness, material morph, bone morph, MMD physical or render fidelity"
    }
    a.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
