"""R050 independent GLB (Khronos glTF) morph accessor vs real Godot GPU-baked
per-index source-vertex displacement. Pure Python stdlib only, source-safe.

This is a 1:1 glTF POSITION morph displacement check, NOT Blender-native,
game-frame appearance, skin pose, muscle/tissue or human anatomy acceptance.
"""
import argparse
import hashlib
import itertools
import json
import math
import os
import statistics
from collections import defaultdict
import struct
from pathlib import Path

THRESHOLD_METERS=0.0001

def hold(message):
    raise ValueError("R050_GLTF_GODOT_MORPH_HOLD "+message)

def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as stream:
        for piece in iter(lambda:stream.read(1<<20),b""):
            h.update(piece)
    return h.hexdigest()

def parse_glb(path):
    raw=Path(path).read_bytes()
    if len(raw)<20 or raw[:4]!=b"glTF":
        hold("source GLB header invalid")
    magic,version,total=struct.unpack_from("<4sII",raw,0)
    if version!=2 or total!=len(raw):
        hold("invalid source GLB version/declared byte length")
    offset=12
    chunks=[]
    while offset<len(raw):
        if offset+8>len(raw):hold("truncated chunk header")
        length,kind=struct.unpack_from("<II",raw,offset)
        offset+=8
        if offset+length>len(raw):hold("truncated chunk body")
        chunks.append((kind,memoryview(raw)[offset:offset+length]))
        offset+=length
    if len(chunks)!=2 or chunks[0][0]!=0x4e4f534a or chunks[1][0]!=0x004e4942:
        hold("expected exactly one JSON and one BIN glTF chunk")
    manifest=json.loads(bytes(chunks[0][1]).decode("utf-8"))
    return manifest,chunks[1][1]

def accessor_xyz(manifest,buf,index):
    """Decode an actual float32 glTF VEC3, including spec sparse overrides."""
    acc=manifest["accessors"][index]
    if acc["componentType"]!=5126 or acc["type"]!="VEC3":
        hold("requires actual float32 VEC3 morph source accessor")
    count=acc["count"]
    if count<=0 or count>1000000:
        hold("invalid source accessor cardinality")
    result=[(0.0,0.0,0.0)]*count
    views=manifest["bufferViews"]
    def bounded_view(view_id,offset,length):
        if not (0<=view_id<len(views)):
            hold("invalid glTF sparse/dense bufferView ID")
        view=views[view_id]
        if "extensions" in view:
            hold("compressed glTF source view unsupported without independent decoder")
        size=view["byteLength"]
        if offset<0 or length<0 or offset+length>size:
            hold("sparse/dense glTF accessor escaped declared bufferView bounds")
        pos=view.get("byteOffset",0)+offset
        if pos<0 or pos+length>len(buf):
            hold("glTF accessor escaped actual GLB binary chunk")
        return pos,view
    if "bufferView" in acc:
        view_id=acc["bufferView"]
        view=views[view_id]
        stride=view.get("byteStride",12)
        if stride<12 or stride>4096:
            hold("unexpected glTF VEC3 stride")
        pos,_=bounded_view(view_id,acc.get("byteOffset",0),(count-1)*stride+12)
        result=[struct.unpack_from("<fff",buf,pos+j*stride) for j in range(count)]
    elif not acc.get("sparse"):
        hold("glTF accessor missing both dense and sparse source data")
    elif acc.get("byteOffset",0)!=0:
        hold("accessor with no bufferView has an unsupported byteOffset")
    sparse=acc.get("sparse")
    if sparse:
        sn=sparse["count"]
        if not (0<sn<=count):
            hold("invalid glTF sparse count")
        ids=sparse["indices"]
        dtype=ids["componentType"]
        format_by_dtype={5121:("<B",1),5123:("<H",2),5125:("<I",4)}
        if dtype not in format_by_dtype:
            hold("unsupported glTF sparse index component type")
        fmt,bytes_per_idx=format_by_dtype[dtype]
        iview=views[ids["bufferView"]]
        istride=iview.get("byteStride",bytes_per_idx)
        if istride<bytes_per_idx:
            hold("invalid sparse index stride")
        ipos,_=bounded_view(ids["bufferView"],ids.get("byteOffset",0),(sn-1)*istride+bytes_per_idx)
        sv=sparse["values"]
        vview=views[sv["bufferView"]]
        vstride=vview.get("byteStride",12)
        if vstride<12:
            hold("invalid sparse VEC3 stride")
        vpos,_=bounded_view(sv["bufferView"],sv.get("byteOffset",0),(sn-1)*vstride+12)
        last=-1
        for j in range(sn):
            at=struct.unpack_from(fmt,buf,ipos+j*istride)[0]
            if at>=count or at<=last:
                hold("sparse glTF morph indices out of range, duplicate or unsorted")
            last=at
            value=struct.unpack_from("<fff",buf,vpos+j*vstride)
            if not all(math.isfinite(k) for k in value):
                hold("nonfinite glTF sparse morph displacement")
            result[at]=value
    if any(not all(math.isfinite(k) for k in v) for v in result):
        hold("nonfinite glTF POSITION or morph displacement source")
    return result

def expected_morph_arrays(path):
    manifest,blob=parse_glb(path)
    found=[]
    for node in manifest.get("nodes",[]):
        if "R043_EditableMask_MPFB_Body" in node.get("name","") and "mesh" in node:
            found.append(node["mesh"])
    if len(found)!=1:hold("unambiguous original MPFB GLB node missing")
    mesh=manifest["meshes"][found[0]]
    parts=mesh["primitives"]
    if len(parts)!=1:hold("body uses multiple glTF primitives; unsupported seam map")
    primitive=parts[0]
    if len(primitive.get("targets",[]))!=8:
        hold("actual MPFB source has not eight glTF morph target arrays")
    base=accessor_xyz(manifest,blob,primitive["attributes"]["POSITION"])
    count=len(base)
    if count<13000:
        hold("glTF source shape unusually small")
    all_morph=[]
    for target in primitive["targets"]:
        if "POSITION" not in target:hold("source morph target missing POSITION")
        points=accessor_xyz(manifest,blob,target["POSITION"])
        if len(points)!=count:hold("morph target source count differs from body")
        all_morph.append(points)
    return base,all_morph

def godot_morph_arrays(path):
    raw=Path(path).read_bytes()
    if len(raw)<8 or len(raw)>10000000:hold("invalid runtime delta binary size")
    channels,vertices=struct.unpack_from("<II",raw,0)
    if channels!=8 or not (13000<=vertices<=1000000):
        hold("unexpected runtime morph binary cardinality")
    expected=8+(channels+1)*vertices*12
    if len(raw)!=expected:
        hold("runtime baseline/morph binary actual length does not match declared arrays")
    baseline=[struct.unpack_from("<fff",raw,8+i*12) for i in range(vertices)]
    if any(not all(math.isfinite(v) for v in xyz) for xyz in baseline):
        hold("runtime baseline has nonfinite vertices")
    off=8+vertices*12
    data=[]
    for _ in range(channels):
        arr=[struct.unpack_from("<fff",raw,off+i*12) for i in range(vertices)]
        if any(not all(math.isfinite(v) for v in x) for x in arr):
            hold("runtime morph binary contains nonfinite numeric data")
        data.append(arr)
        off+=vertices*12
    return baseline,data


def apply_axis(point,transform):
    return tuple(transform["sign"][k]*point[transform["axis"][k]] for k in range(3))

def source_to_godot(source,observed):
    """Find a one-to-one GLB-to-Godot vertex correspondence based on
    independently measured actual rest/baked GPU positions, not morph deltas."""
    if len(source)!=len(observed) or len(source)<13000:
        hold("source-engine baseline count mismatch")
    lo=[min(p[d] for p in source) for d in range(3)]
    hi=[max(p[d] for p in source) for d in range(3)]
    go_lo=[min(p[d] for p in observed) for d in range(3)]
    go_hi=[max(p[d] for p in observed) for d in range(3)]
    candidates=[]
    for axis in itertools.permutations(range(3)):
        for sign in itertools.product((-1,1),repeat=3):
            low=[lo[axis[k]] if sign[k]>0 else -hi[axis[k]] for k in range(3)]
            high=[hi[axis[k]] if sign[k]>0 else -lo[axis[k]] for k in range(3)]
            score=sum(abs(low[k]-go_lo[k])+abs(high[k]-go_hi[k]) for k in range(3))
            candidates.append((score,{"axis":list(axis),"sign":list(sign)}))
    candidates.sort(key=lambda x:(x[0],x[1]["axis"],x[1]["sign"]))
    best={"examined":0,"matched":0}
    cell=0.0001
    limit=0.0002
    for score,transform in candidates[:16]:
        buckets=defaultdict(list)
        for i,p in enumerate(source):
            q=apply_axis(p,transform)
            key=tuple(math.floor(v/cell) for v in q)
            buckets[key].append((i,q))
        options=[]
        matched=0
        for j,p in enumerate(observed):
            key=tuple(math.floor(v/cell) for v in p)
            choices=[]
            for dx,dy,dz in itertools.product((-1,0,1),repeat=3):
                for si,q in buckets.get((key[0]+dx,key[1]+dy,key[2]+dz),()):
                    distance=math.dist(p,q)
                    if distance<=limit:
                        choices.append((distance,si))
            choices.sort()
            if choices:matched+=1
            options.append(choices)
        if matched>best["matched"]:
            best={"examined":len(observed),"matched":matched,"axis":transform,
                  "bbox_score_m":score}
        if matched!=len(observed):
            continue
        assignment=[None]*len(observed)
        used=set()
        for j in sorted(range(len(observed)),key=lambda i:(len(options[i]),i)):
            for distance,si in options[j]:
                if si not in used:
                    assignment[j]=(si,distance)
                    used.add(si)
                    break
        if len(used)!=len(observed):
            continue
        maxerr=max(x[1] for x in assignment)
        mapping=[x[0] for x in assignment]
        print("R050_GLTF_GODOT_BASELINE_MAPPING "+json.dumps(
            {"axis":transform,"bbox_score_m":score,"max_residual_m":maxerr,
             "vertices":len(mapping),"index_order_unchanged":all(i==j for i,j in enumerate(mapping))},
            sort_keys=True))
        return mapping,transform,maxerr
    hold("no unique source glTF to Godot GPU baseline vertex mapping at 0.2mm: "+json.dumps(best,sort_keys=True))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--glb",required=True)
    p.add_argument("--godot",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--stimulus",type=float,default=0.24)
    a=p.parse_args()
    if not(0<a.stimulus<=1):
        hold("invalid stimulus")
    source_baseline,source=expected_morph_arrays(a.glb)
    observed_baseline,observed=godot_morph_arrays(a.godot)
    count=len(source_baseline)
    if len(observed_baseline)!=count:hold("Godot and source raw glTF vertex cardinality mismatch")
    mapping,transform,base_residual=source_to_godot(source_baseline,observed_baseline)
    metrics=[]
    failures=[]
    for channel in range(8):
        deltas=[]
        nonzero=0
        max_expected=0
        max_observed=0
        for i in range(count):
            original=source[channel][mapping[i]]
            expected=[v*a.stimulus for v in apply_axis(original,transform)]
            got=observed[channel][i]
            err=math.sqrt(sum((got[k]-expected[k])**2 for k in range(3)))
            if not math.isfinite(err):hold("nonfinite reference displacement error")
            deltas.append(err)
            mag=math.sqrt(sum(g*g for g in got))
            max_observed=max(max_observed,mag)
            expected_mag=math.sqrt(sum(e*e for e in expected))
            max_expected=max(max_expected,expected_mag)
            if mag>1e-6:nonzero+=1
        deltas.sort()
        met={"channel_index":channel,"vertex_count":count,
             "max_error_m":deltas[-1],
             "mean_error_m":statistics.mean(deltas),
             "p95_error_m":deltas[math.ceil(.95*count)-1],
             "active_vertices":nonzero,
             "max_expected_displacement_m":max_expected,
             "max_observed_displacement_m":max_observed}
        if met["max_error_m"]>THRESHOLD_METERS:failures.append(channel)
        metrics.append(met)
    record={"schema":"r050.gltf.godot.actual-morph-delta.v1",
            "status":"PASS_NARROW_EIGHT_GLTF_MORPH_VERTEX_DELTA_PARITY" if not failures else "FAIL_HOLD_GLTF_VERTEX_DELTA_PARITY",
            "source_glb_sha256":sha(a.glb),
            "godot_delta_sha256":sha(a.godot),
            "source_gltf_vertices":count,
            "source_to_engine_axis":transform,
            "max_source_to_engine_baseline_error_m":base_residual,
            "source_to_engine_position_mapping":"INDEPENDENT_ONE_TO_ONE_NEAREST_BASELINE_POSITION",
            "eight_channels":len(metrics),
            "stimulus":a.stimulus,
            "per_vertex_error_threshold_m":THRESHOLD_METERS,
            "failed_morph_channel_indices":failures,
            "results":metrics,
            "limits":"Per-index original glTF morph delta vs actual Godot Mesa baked mesh; no Blender world-space pose, material/normal/UV, synthetic organ or real anatomical/film acceptance"}
    Path(a.out).write_text(json.dumps(record,sort_keys=True,indent=2),encoding="utf-8")
    print("R050_GLTF_GODOT_MORPH_RECEIPT "+json.dumps(record,sort_keys=True))
    if failures:hold("actual glTF morph deltas did not match engine for indices "+str(failures))

if __name__=="__main__":
    main()
