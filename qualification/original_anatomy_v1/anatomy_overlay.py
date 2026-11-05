#!/usr/bin/env python3
"""Reversible original-only body/head/face geometry overlay for Aster and Juniper.

Changes a source-frozen original glTF GLB into a derived GLB. Preserves the
17-joint skin, animation channels and root trajectories. It does NOT assert
natural walking, photorealism, realistic clothes or human likeness acceptance.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

ACTORS = ("AsterOriginal", "JuniperOriginal")
HEAD_SCALE = (.93, .72, .96)
FEATURES = ("nose", "ear_L", "ear_R", "brow_L", "brow_R",
            "upper_lip", "lower_lip", "chin")

def decode(raw):
    if len(raw) < 28 or raw[:4] != b'glTF':
        raise ValueError("BAD_GLB_HEADER")
    _,version,total = struct.unpack_from("<4sII",raw)
    if version!=2 or total!=len(raw):raise ValueError("BAD_GLB_LENGTH")
    size,kind=struct.unpack_from("<I4s",raw,12)
    if kind!=b'JSON' or 28+size>len(raw):raise ValueError("BAD_JSON_CHUNK")
    doc=json.loads(raw[20:20+size]);size2,kind2=struct.unpack_from("<I4s",raw,20+size)
    if kind2!=b'BIN\0' or 28+size+size2!=len(raw):raise ValueError("BAD_BIN_CHUNK")
    return doc,bytearray(raw[28+size:])

def encode(doc,data):
    doc["buffers"][0]["byteLength"]=len(data)
    js=json.dumps(doc,separators=(",",":"),sort_keys=True).encode()
    js+=b' '*(-len(js)%4)
    b=bytes(data)+b'\0'*(-len(data)%4)
    total=28+len(js)+len(b)
    return (struct.pack("<4sII",b'glTF',2,total)+struct.pack("<I4s",len(js),b'JSON')
            +js+struct.pack("<I4s",len(b),b'BIN\0')+b)

def put(doc,data,flat,fmt,kind,target):
    nc={"SCALAR":1,"VEC3":3,"VEC4":4}[kind]
    if len(flat)%nc:raise ValueError("BAD_COMPONENT_COUNT")
    while len(data)%4:data.append(0)
    off=len(data);blob=struct.pack("<"+fmt*len(flat),*flat);data.extend(blob)
    vi=len(doc["bufferViews"])
    doc["bufferViews"].append({"buffer":0,"byteOffset":off,
                               "byteLength":len(blob),"target":target})
    acc={"bufferView":vi,"componentType":{"f":5126,"B":5121,"I":5125}[fmt],
         "count":len(flat)//nc,"type":kind}
    if kind=="VEC3" and fmt=="f":
        acc["min"]=[min(flat[k::3]) for k in range(3)]
        acc["max"]=[max(flat[k::3]) for k in range(3)]
    doc["accessors"].append(acc)
    return len(doc["accessors"])-1

def positions(doc,data,idx):
    acc=doc["accessors"][idx];v=doc["bufferViews"][acc["bufferView"]]
    if acc["componentType"]!=5126 or acc["type"]!="VEC3" or "sparse" in acc:
        raise ValueError("UNSUPPORTED_ACCESSOR")
    if v.get("buffer")!=0 or v.get("byteStride") not in (None,12):
        raise ValueError("UNSUPPORTED_POSITION_LAYOUT")
    start=v.get("byteOffset",0)+acc.get("byteOffset",0)
    if start<0 or start+12*acc["count"]>min(len(data),v.get("byteOffset",0)+v["byteLength"]):
        raise ValueError("ACCESSOR_OUT_OF_BOUNDS")
    return start,[list(struct.unpack_from("<fff",data,start+12*i)) for i in range(acc["count"])]

def write_positions(data,off,rows):
    for i,p in enumerate(rows):
        if not all(math.isfinite(v) for v in p):raise ValueError("NONFINITE_VERTEX")
        struct.pack_into("<fff",data,off+12*i,*p)

def ellipsoid(center,radius,lat=10,lon=16):
    points=[];normals=[];indices=[]
    for i in range(lat+1):
        theta=math.pi*i/lat
        for j in range(lon+1):
            phi=2*math.pi*j/lon
            u=(math.sin(theta)*math.cos(phi),math.cos(theta),
               math.sin(theta)*math.sin(phi))
            points.append([center[k]+radius[k]*u[k] for k in range(3)])
            n=[u[k]/radius[k] for k in range(3)]
            mag=math.sqrt(sum(t*t for t in n));normals.append([t/mag for t in n])
    row=lon+1
    for i in range(lat):
        for j in range(lon):
            a=i*row+j;b=a+row
            if i>0:indices.extend((a,b,a+1))
            if i<lat-1:indices.extend((a+1,b,b+1))
    return points,normals,indices

def feature(doc,data,mesh,material,head,tag,center,radius):
    p,n,ix=ellipsoid(center,radius)
    pa=put(doc,data,[v for row in p for v in row],"f","VEC3",34962)
    na=put(doc,data,[v for row in n for v in row],"f","VEC3",34962)
    ja=put(doc,data,[head,0,0,0]*len(p),"B","VEC4",34962)
    wa=put(doc,data,[1.,0.,0.,0.]*len(p),"f","VEC4",34962)
    ia=put(doc,data,ix,"I","SCALAR",34963)
    mesh["primitives"].append({"attributes":{"POSITION":pa,"NORMAL":na,
                              "JOINTS_0":ja,"WEIGHTS_0":wa},"indices":ia,
                              "material":material,"extras":{"original_added_feature":tag}})
    return len(ix)//3

def sculpt_mesh(doc,data,mesh):
    names=[m.get("name","") for m in doc["materials"]]
    old_count=len(mesh["primitives"])
    head_count=torso_count=0
    for prim in mesh["primitives"]:
        material=names[prim["material"]]
        offset,p=positions(doc,data,prim["attributes"]["POSITION"])
        cy=sum(v[1] for v in p)/len(p)
        head=(cy>=1.57 and material in
              ("skinWarm","skinCool","ebonyHair","chestnutHair","eyeWhite","iris"))
        torso=(material in ("coralJacket","tealJacket") and .9<=cy<=1.45)
        if not (head or torso):continue
        if head:
            head_count+=1
            for v in p:
                v[0]*=HEAD_SCALE[0]
                v[1]=1.64+(v[1]-1.64)*HEAD_SCALE[1]
                v[2]*=HEAD_SCALE[2]
        else:
            torso_count+=1
            for v in p:
                y=v[1];waist=math.exp(-((y-1.10)/.20)**2)
                chest=math.exp(-((y-1.37)/.14)**2)
                v[0]*=1-.12*waist+.075*chest
                v[2]*=1-.06*waist+.04*chest
        write_positions(data,offset,p)
        a=doc["accessors"][prim["attributes"]["POSITION"]]
        if "min" in a:a["min"]=[min(row[k] for row in p) for k in range(3)]
        if "max" in a:a["max"]=[max(row[k] for row in p) for k in range(3)]
        if head:
            noff,ns=positions(doc,data,prim["attributes"]["NORMAL"])
            for n in ns:
                for k in range(3):n[k]/=HEAD_SCALE[k]
                mag=max(1e-10,math.sqrt(sum(t*t for t in n)))
                for k in range(3):n[k]/=mag
            write_positions(data,noff,ns)
    if head_count<3 or torso_count<1 or old_count<5:
        raise ValueError("UNEXPECTED_SOURCE_MESH")
    return head_count,torso_count

def sculpt(raw,expected):
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=expected:raise ValueError("SOURCE_HASH_MISMATCH")
    doc,data=decode(raw)
    extras=doc.get("extras",{})
    if extras.get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or extras.get("third_party_models") is not False:
        raise ValueError("ORIGINAL_ONLY_SOURCE_REQUIRED")
    if len(doc.get("meshes",[]))!=2 or len(doc.get("skins",[]))!=2 or len(doc.get("animations",[]))!=1:
        raise ValueError("TWO_SKIN_SINGLE_CLIP_REQUIRED")
    nodes={n["name"]:i for i,n in enumerate(doc["nodes"])}
    materials={m["name"]:i for i,m in enumerate(doc["materials"])}
    report=[]
    for index,actor in enumerate(ACTORS):
        headname=actor+"_head"
        if headname not in nodes:raise ValueError("HEAD_NODE_MISSING")
        skin=doc["skins"][index]
        if len(skin["joints"])!=17:raise ValueError("SOURCE_RIG_NOT_17")
        try:joint=skin["joints"].index(nodes[headname])
        except ValueError:raise ValueError("HEAD_NOT_SKINNED")
        mesh=doc["meshes"][index]
        hc,tc=sculpt_mesh(doc,data,mesh)
        skin_mat=materials["skinWarm" if index==0 else "skinCool"]
        hair_mat=materials["ebonyHair" if index==0 else "chestnutHair"]
        lip="anatomyLipWarm" if index==0 else "anatomyLipCool"
        rgb=[.57,.26,.27,1.] if index==0 else [.43,.20,.19,1.]
        doc["materials"].append({"name":lip,"pbrMetallicRoughness":{
                "baseColorFactor":rgb,"metallicFactor":0,"roughnessFactor":.85},
                "doubleSided":False})
        lip_mat=len(doc["materials"])-1
        features={
            "nose":(skin_mat,(0,1.627,-.132),(.028,.052,.041)),
            "ear_L":(skin_mat,(-.136,1.639,0),(.028,.051,.024)),
            "ear_R":(skin_mat,(.136,1.639,0),(.028,.051,.024)),
            "brow_L":(hair_mat,(-.050,1.686,-.113),(.046,.009,.012)),
            "brow_R":(hair_mat,(.050,1.686,-.113),(.046,.009,.012)),
            "upper_lip":(lip_mat,(0,1.574,-.126),(.043,.009,.013)),
            "lower_lip":(lip_mat,(0,1.560,-.121),(.039,.010,.012)),
            "chin":(skin_mat,(0,1.535,-.089),(.048,.017,.021))}
        triangles=sum(feature(doc,data,mesh,mat,joint,name,center,radius)
                      for name,(mat,center,radius) in features.items())
        report.append({"actor":actor,"head_primitives_sculpted":hc,
                       "torso_primitives_sculpted":tc,
                       "facial_features_added":len(features),"new_triangles":triangles,
                       "head_joint_skin_index":joint})
    doc.setdefault("extras",{})["r009_anatomy_overlay_v1"]={
       "source_sha256":sha,"original_owner_source":True,"source_unchanged":True,
       "head_scale":list(HEAD_SCALE),"facial_features_each":len(FEATURES),
       "bones_each":17,"rig_v2":"NOT_IMPLEMENTED",
       "native_blender":"NOT_RUN","human_visual":"NOT_ACCEPTED",
       "real_gait":"NOT_ACCEPTED","clothing_strain":"UNKNOWN",
       "release_approved":False}
    return encode(doc,data),report

def produce(source,out,receipt,sha):
    src,out,receipt=map(lambda p:Path(p).resolve(),(source,out,receipt))
    if len({src,out,receipt})!=3:raise ValueError("SOURCE_OR_RECEIPT_OVERWRITE_REFUSED")
    raw=src.read_bytes();data,characters=sculpt(raw,sha)
    if hashlib.sha256(src.read_bytes()).hexdigest()!=sha:raise ValueError("SOURCE_MUTATED")
    out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(out.suffix+".tmp");tmp.write_bytes(data);tmp.replace(out)
    r={"schema":"scp.r009.original_anatomy.v1","status":"DERIVED_SOURCE_NOT_ACCEPTED",
       "source_sha256":sha,"derived_sha256":hashlib.sha256(data).hexdigest(),
       "source_bytes_unchanged":True,"characters":characters,"frames":72,"fps":12,
       "bones_each":17,"human_visual_accepted":False,"real_gait_accepted":False}
    receipt.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    return r

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--receipt",required=True)
    p.add_argument("--sha256",required=True)
    a=p.parse_args()
    try:print(json.dumps(produce(a.source,a.out,a.receipt,a.sha256),sort_keys=True))
    except Exception as ex:raise SystemExit("ANATOMY_V1_FAIL:"+str(ex))
