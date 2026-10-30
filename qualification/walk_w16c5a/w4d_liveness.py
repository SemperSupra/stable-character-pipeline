"""Independent stdlib GLB accessor/timing/actual animated joint liveness witness.

Unlike C5A's single-frame animation objects, authentic animation requires
>=24 distinct time samples and nonzero rotation data on BOTH skinned actors.
Not a proof of locomotion, foot contact, joint anatomy, or visual quality.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

MAX=20*1024*1024

def decode_glb(raw):
    if len(raw)<28 or len(raw)>MAX or raw[:4]!=b"glTF":
        raise ValueError("GLB_BYTES_OR_MAGIC")
    version,total=struct.unpack_from("<II",raw,4)
    if version!=2 or total!=len(raw):
        raise ValueError("GLB_VERSION_OR_LENGTH")
    size,kind=struct.unpack_from("<II",raw,12)
    if kind!=0x4e4f534a or size%4 or 20+size+8>len(raw):
        raise ValueError("GLB_JSON_CHUNK")
    j=json.loads(raw[20:20+size].decode("utf8"))
    offset=20+size
    bsize,btype=struct.unpack_from("<II",raw,offset)
    if btype!=0x004e4942 or offset+8+bsize!=len(raw):
        raise ValueError("GLB_BIN_CHUNK")
    return j,raw[offset+8:]

def float_accessor(doc,binary,index,shape):
    accessors=doc.get("accessors",[])
    if type(index)!=int or not 0<=index<len(accessors):
        raise ValueError("ACCESSOR_INDEX")
    a=accessors[index]
    dim={"SCALAR":1,"VEC3":3,"VEC4":4}[shape]
    if a.get("type")!=shape or a.get("componentType")!=5126 or a.get("sparse") or a.get("count",0)<1:
        raise ValueError("ACCESSOR_FORMAT")
    viewid=a.get("bufferView")
    views=doc.get("bufferViews",[])
    if type(viewid)!=int or not 0<=viewid<len(views):
        raise ValueError("BUFFER_VIEW")
    v=views[viewid]
    if v.get("buffer",0)!=0:
        raise ValueError("BUFFER_INDEX")
    size=4*dim
    stride=v.get("byteStride",size)
    if stride<size or stride%4:
        raise ValueError("BUFFER_STRIDE")
    start=v.get("byteOffset",0)+a.get("byteOffset",0)
    maxend=start+(a["count"]-1)*stride+size
    if start<0 or maxend>len(binary) or maxend>v.get("byteOffset",0)+v.get("byteLength",0):
        raise ValueError("BUFFER_VIEW_BOUNDS")
    values=[]
    for i in range(a["count"]):
        values.append(struct.unpack_from("<"+"f"*dim,binary,start+i*stride))
    if any(not math.isfinite(x) for row in values for x in row):
        raise ValueError("NONFINITE_ANIMATION_ACCESSOR")
    return values

def liveness(doc,binary,receipt):
    if receipt.get("schema") not in ("scp.walk_w4d_native_24frame_smoke.v1","scp.walk_w5d_native_grounded.v1") or        receipt.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or        receipt.get("frame_count")!=24 or receipt.get("fps_num")!=12:
        raise ValueError("SOURCE_RIGHTS_OR_CLOCK")
    skinsets=[set(s.get("joints",[])) for s in doc.get("skins",[])]
    if len(skinsets)!=2 or any(len(s)<6 for s in skinsets):
        raise ValueError("TWO_SKINNED_SIX_BONE_ACTORS_REQUIRED")
    nodes=doc.get("nodes",[])
    if any(any(type(n)!=int or n<0 or n>=len(nodes) for n in skin) for skin in skinsets):
        raise ValueError("SKIN_JOINT_INDEX_INVALID")
    moving=set();counts=[]
    if not doc.get("animations"):
        raise ValueError("ACTUAL_GLTF_ANIMATION_MISSING")
    for anim in doc["animations"]:
        samplers=anim.get("samplers",[])
        for ch in anim.get("channels",[]):
            target=ch.get("target",{})
            nodeid=target.get("node")
            if type(nodeid)!=int or not 0<=nodeid<len(nodes):
                raise ValueError("ANIMATION_TARGET_NODE")
            if target.get("path")!="rotation":
                continue
            if type(ch.get("sampler"))!=int or not 0<=ch["sampler"]<len(samplers):
                raise ValueError("ANIMATION_SAMPLER_ID")
            s=samplers[ch["sampler"]]
            if s.get("interpolation","LINEAR") not in ("LINEAR","STEP"):
                raise ValueError("UNQUALIFIED_CUBIC_ANIMATION")
            ticks=[x[0] for x in float_accessor(doc,binary,s["input"],"SCALAR")]
            q=float_accessor(doc,binary,s["output"],"VEC4")
            if len(ticks)<24 or len(q)!=len(ticks):
                continue
            if any(abs(t-i/12)>2e-4 for i,t in enumerate(ticks[:24])) or                any(ticks[i]<=ticks[i-1] for i in range(1,len(ticks))):
                raise ValueError("ANIMATED_CLOCK_OR_DUPLICATE_TIMESTAMPS")
            if len(ticks)!=24 or abs(ticks[-1]-23/12)>2e-4:
                raise ValueError("NOT_EXACT_24_FRAME_TIMELINE")
            if not "Lower" in nodes[nodeid].get("name",""):
                continue
            first=q[0]
            if max(math.dist(row,first) for row in q)>.005:
                for ai,skin in enumerate(skinsets):
                    if nodeid in skin:moving.add(ai)
                counts.append(len(ticks))
    if moving!={0,1}:
        raise ValueError("NO_REAL_24FRAME_LOWER_BONE_MOTION_FOR_BOTH_ACTORS")
    return {"schema":"scp.walk_w4d_independent_liveness.v1",
            "status":"PASS_SYNTHETIC_GLB_24FRAME_LOWER_BONE_LIVENESS_ONLY",
            "source_glb_sha256":receipt["glb_sha256"],
            "moving_skin_actors":sorted(moving),"validated_lower_bone_channel_frames":counts,
            "human_anatomy":"UNKNOWN_UNAPPROVED",
            "sole_contact":"UNKNOWN_UNVALIDATED",
            "full_body":"FAIL_ONLY_ABSTRACT_LEGS",
            "visual_quality":"UNKNOWN_NO_VIDEO"}

def observe(folder):
    folder=Path(folder)
    raw=(folder/"original_synthetic_24frame_skinned.glb").read_bytes()
    receipt=json.loads((folder/"source_motion_receipt.json").read_text())
    if receipt.get("glb_sha256")!=hashlib.sha256(raw).hexdigest():
        raise ValueError("GLB_SOURCE_HASH_MISMATCH")
    doc,binary=decode_glb(raw)
    result=liveness(doc,binary,receipt)
    (folder/"independent_animation_liveness.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("W4D_ACTUAL_BINARY_ANIMATION_LIVENESS",json.dumps(result,sort_keys=True))
    return result
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("folder")
    observe(p.parse_args().folder)
