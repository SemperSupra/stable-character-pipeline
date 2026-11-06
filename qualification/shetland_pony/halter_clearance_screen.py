#!/usr/bin/env python3
"""Conservative public-original halter-to-head analytical rest-pose screen.

Works on exact exported glTF GLB vertex positions. The registered head loft
is curved and includes tangent-plane offsets, so an interpolated elliptical
cross-section is only a SCREEN, not exact triangle collision or live-animal
tack safety approval. Preserve all possible negative results.
"""
import json
import math
import struct
import sys
from pathlib import Path
from equine_sculpt import HEAD

EXPECTED=("halter_cheek_L","halter_cheek_R","halter_crownpiece",
          "halter_noseband","halter_throatlatch")
MAX_BYTES=100*1024*1024


def load_glb(path):
    b=Path(path).read_bytes()
    if not 20<=len(b)<=MAX_BYTES or b[:4]!=b"glTF":
        raise ValueError("not a bounded GLB")
    magic,version,nbytes=struct.unpack_from("<4sII",b)
    if version!=2 or nbytes!=len(b):raise ValueError("bad GLB length/version")
    i=12; chunks=[]
    while i<len(b):
        if i+8>len(b):raise ValueError("truncated chunk header")
        count,typ=struct.unpack_from("<I4s",b,i)
        if count%4 or i+8+count>len(b):raise ValueError("bad chunk extent")
        chunks.append((typ,b[i+8:i+8+count]))
        i+=8+count
    if len(chunks)!=2 or chunks[0][0]!=b"JSON" or chunks[1][0]!=b"BIN\x00":
        raise ValueError("expected JSON + BIN")
    return json.loads(chunks[0][1].decode()),chunks[1][1]


def position_accessor(g,binary,index):
    a=g["accessors"][index]
    if a["type"]!="VEC3" or a["componentType"]!=5126 or a["count"]>10000:
        raise ValueError("non-plain position accessor")
    view=g["bufferViews"][a["bufferView"]]
    stride=view.get("byteStride",12)
    if stride<12 or stride%4:raise ValueError("bad vertex stride")
    start=view.get("byteOffset",0)+a.get("byteOffset",0)
    if start<0 or start+(a["count"]-1)*stride+12>len(binary):
        raise ValueError("truncated vertices")
    result=[struct.unpack_from("<fff",binary,start+i*stride) for i in range(a["count"])]
    if any(not math.isfinite(x) for p in result for x in p):
        raise ValueError("nonfinite halter vertex")
    return result


def sample_envelope(point):
    # glTF export is x axial, Y height, Z lateral for the original Blender
    # source. Interpolate the script's registered synthetic x/Z/width/depth.
    if len(point)!=3 or any(not math.isfinite(x) for x in point):
        raise ValueError("invalid source point")
    x,height,lateral=point
    if not HEAD[0][0]<=x<=HEAD[-1][0]:
        return None
    i=next((j for j in range(len(HEAD)-1) if HEAD[j][0]<=x<=HEAD[j+1][0]),len(HEAD)-2)
    a,b=HEAD[i],HEAD[i+1]
    t=(x-a[0])/(b[0]-a[0])
    zcenter=a[1]*(1-t)+b[1]*t
    width=a[2]*(1-t)+b[2]*t
    depth=a[3]*(1-t)+b[3]*t
    return math.hypot(lateral/width,(height-zcenter)/depth)


def screen(path):
    g,binary=load_glb(path)
    by_name={n.get("name"):n for n in g.get("nodes",[])}
    if not set(EXPECTED)<=set(by_name):
        raise ValueError("missing halter nodes")
    report={"schema":"equine.halter.clearance.analytic_screen.v1",
            "scope":"REST POSE ONLY, NOT actual skinned/deformed triangle intersections",
            "science":"POTENTIAL_ONLY; envelope is simplified, holds remain",
            "parts":{}}
    for name in EXPECTED:
        node=by_name[name]
        if "mesh" not in node:raise ValueError("missing mesh for "+name)
        if any(k in node for k in ("translation","rotation","scale","matrix")):
            # Do not silently evaluate arbitrary object transforms.
            raise ValueError("unexpected transformed halter node "+name)
        mesh=g["meshes"][node["mesh"]]
        points=[]
        for p in mesh["primitives"]:
            points.extend(position_accessor(g,binary,p["attributes"]["POSITION"]))
        signed=[sample_envelope(p) for p in points]
        signed=[x for x in signed if x is not None]
        if not signed:raise ValueError("no in-head-range samples for "+name)
        count=sum(x<1.0 for x in signed)
        near=sum(x<1.05 for x in signed)
        report["parts"][name]={"sampled_vertices":len(signed),
            "fraction_inside_analytic_envelope":round(count/len(signed),5),
            "fraction_within_5pct_envelope":round(near/len(signed),5),
            "min_normalized_envelope_radius":round(min(signed),5),
            "verdict":"POTENTIAL_CLIP_INVESTIGATE" if count else "NO_ANALYTIC_INTERSECTION_ONLY"}
    report["any_possible_intersection"]=any(p["verdict"]=="POTENTIAL_CLIP_INVESTIGATE"
                                         for p in report["parts"].values())
    return report


def selftest():
    assert sample_envelope((HEAD[2][0],HEAD[2][1],0))==0.0
    assert abs(sample_envelope((HEAD[2][0],HEAD[2][1],HEAD[2][2]))-1.0)<1e-9
    assert sample_envelope((HEAD[2][0],HEAD[2][1],HEAD[2][2]*1.5))>1.4
    assert sample_envelope((99.,0.,0.)) is None
    try:sample_envelope((float("nan"),0.,0.))
    except ValueError:pass
    else:raise AssertionError("accepted nonfinite")


if __name__=="__main__":
    selftest()
    if len(sys.argv)!=3:
        raise SystemExit("usage: halter_clearance_screen.py <original-synthetic.glb> <receipt.json>")
    receipt=screen(sys.argv[1])
    Path(sys.argv[2]).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,sort_keys=True))
