#!/usr/bin/env python3
"""R077 source-original two-actor rig/clock/foot-contact falsifier. Not acceptance."""
import argparse,hashlib,json,math,struct,sys
from pathlib import Path
SCHEMA="scp.r077.source-rig-contact-envelope.v1"
ACTORS=("AsterOriginal","JuniperOriginal")
BONES=("pelvis","spine","chest","neck","head","hip_L","knee_L","ankle_L","hip_R","knee_R","ankle_R","shoulder_L","elbow_L","wrist_L","shoulder_R","elbow_R","wrist_R")
class Hold(ValueError):pass
def require(cond,why):
    if not cond:raise Hold(why)
def unique(pairs):
    d={}
    for k,v in pairs:
        require(k not in d,"DUPLICATE_JSON_KEY");d[k]=v
    return d
def decode_glb(raw):
    require(len(raw)>=32 and raw[:4]==b"glTF","NOT_GLB")
    _,ver,total=struct.unpack_from("<4sII",raw)
    require(ver==2 and total==len(raw),"GLB_VERSION_OR_LENGTH")
    chunks=[];off=12
    while off<total:
        require(off+8<=total,"TRUNCATED_CHUNK")
        n,t=struct.unpack_from("<I4s",raw,off);off+=8
        require(n%4==0 and off+n<=total,"CHUNK_RANGE_INVALID")
        chunks.append((t,raw[off:off+n]));off+=n
    require(len(chunks)==2 and chunks[0][0]==b"JSON" and chunks[1][0]==b"BIN\x00","GLB_CHUNKS_INVALID")
    try:doc=json.loads(chunks[0][1],object_pairs_hook=unique,parse_constant=lambda x: (_ for _ in ()).throw(Hold("NONFINITE_JSON")))
    except (UnicodeError,json.JSONDecodeError) as exc:raise Hold("GLB_JSON_INVALID") from exc
    require(isinstance(doc,dict) and doc.get("asset",{}).get("version")=="2.0","NOT_GLTF2")
    require(len(doc.get("buffers",[]))==1,"BUFFER_DECLARATION")
    count=doc["buffers"][0]["byteLength"];data=chunks[1][1]
    require(type(count) is int and 0<=count<=len(data) and len(data)-count<=3,"BUFFER_LENGTH_MISMATCH")
    return doc,data
def floats(doc,data,idx,typ):
    ac=doc.get("accessors",[]);views=doc.get("bufferViews",[])
    require(type(idx) is int and 0<=idx<len(ac),"ACCESSOR_BAD_INDEX")
    a=ac[idx]
    require(a.get("componentType")==5126 and a.get("type")==typ and "sparse" not in a,"ACCESSOR_TYPE_INVALID")
    vi=a.get("bufferView")
    require(type(vi) is int and 0<=vi<len(views),"ACCESSOR_VIEW_INVALID")
    v=views[vi];dim={"SCALAR":1,"VEC3":3}[typ]
    count=a.get("count");stride=v.get("byteStride",dim*4)
    base=v.get("byteOffset",0)+a.get("byteOffset",0)
    limit=v.get("byteOffset",0)+v.get("byteLength",0)
    require(type(count) is int and 0<count<=720 and type(stride) is int and stride>=4*dim and type(base) is int and base>=0,"ACCESSOR_BAD_LAYOUT")
    require(base+stride*(count-1)+4*dim<=min(limit,len(data)),"ACCESSOR_OUT_OF_RANGE")
    rows=[struct.unpack_from("<"+"f"*dim,data,base+i*stride) for i in range(count)]
    require(all(math.isfinite(x) for row in rows for x in row),"NONFINITE_ACCESSOR")
    return rows
def evaluate(doc,data,sha):
    require(doc.get("extras",{}).get("source_class")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","SOURCE_NOT_ORIGINAL_SYNTHETIC")
    nodes=doc.get("nodes",[]);skins=doc.get("skins",[]);anims=doc.get("animations",[])
    require(len(nodes)<256 and len(skins)==2 and len(anims)==1,"SOURCE_ACTOR_SKIN_ANIMATION_COUNT")
    names=[n.get("name","") for n in nodes]
    require(len(set(names))==len(names),"DUPLICATE_NODE_NAMES")
    roots=[];joints=[]
    for actor in ACTORS:
        root=actor+"_SceneRoot"
        require(names.count(root)==1,"SOURCE_ROOT_MISSING");roots.append(names.index(root))
        nameset=[actor+"_"+bone for bone in BONES]
        require(all(names.count(n)==1 for n in nameset),"SOURCE_JOINT_MISSING")
        joints.append({names.index(n) for n in nameset})
    scene=doc.get("scenes",[{}])[doc.get("scene",0)]
    require(set(scene.get("nodes",[]))==set(roots),"SOURCE_SCENE_ROOT_SET_CHANGED")
    available=[set(x.get("joints",[])) for x in skins]
    require(all(js in available for js in joints),"SOURCE_SKIN_JOINT_SET_CHANGED")
    anim=anims[0];samplers=anim.get("samplers",[]);tracks={}
    for channel in anim.get("channels",[]):
        target=channel.get("target",{});ni=target.get("node");prop=target.get("path")
        require(type(ni) is int and 0<=ni<len(nodes),"ANIMATION_TARGET_INVALID")
        si=channel.get("sampler")
        require(type(si) is int and 0<=si<len(samplers),"ANIMATION_SAMPLER_INVALID")
        sm=samplers[si]
        clock=floats(doc,data,sm.get("input"),"SCALAR")
        require(len(clock)==72 and all(abs(clock[i][0]-i/12)<1e-5 for i in range(72)),"CLOCK_72F_12FPS_MISMATCH")
        require(sm.get("interpolation")=="LINEAR","INTERPOLATION_CHANGED")
        if ni in roots and prop=="translation":
            require(ni not in tracks,"ROOT_DUPLICATE_TRACK")
            tracks[ni]=floats(doc,data,sm.get("output"),"VEC3")
    require(set(tracks)==set(roots),"ROOT_TRACKS_MISSING")
    a,b=(tracks[n] for n in roots)
    require(len(a)==len(b)==72,"ROOT_TIMELINE_SIZE")
    start=abs(a[0][0]-b[0][0]);end=abs(a[-1][0]-b[-1][0])
    require(start>2 and end<start-.5 and a[-1][0]>a[0][0] and b[-1][0]<b[0][0],"TWO_ACTOR_APPROACH_NOT_PROVEN")
    tokens={"heel","toe","toes","foot","ball","metatarsal"}
    articulated=[n for n in names if any(t in n.lower().split("_") for t in tokens)]
    reasons=["PHYSICAL_FOOT_CONTACT_UNOBSERVED","SKIN_FLOOR_COLLISION_UNOBSERVED","HEEL_TOE_FORCE_AND_SLIP_UNOBSERVED"]
    if not articulated:reasons.append("NO_SOURCE_HEEL_TOE_ARTICULATION")
    return {"schema":SCHEMA,"status":"HOLD_SOURCE_CONTACT_AND_GAIT",
      "source_sha256":sha,"source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
      "actor_count":2,"bone_count_each":len(BONES),"sampled_frame_count":72,"source_clock_fps":12,
      "root_separation_start_m":round(start,6),"root_separation_end_m":round(end,6),
      "articulated_heel_toe_nodes":len(articulated),"reasons":reasons,
      "native_blender_evaluated":False,"foot_contact_qualified":False,
      "film_accepted":False,"mvp_accepted":False,"release_authorized":False}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--glb",required=True,type=Path);p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    require(not args.out.exists() and args.out.resolve()!=args.glb.resolve(),"REFUSE_OUTPUT_OVERWRITE")
    raw=args.glb.read_bytes();require(len(raw)<20000000,"SOURCE_OVER_BYTE_CAP")
    doc,bin=decode_glb(raw)
    result=evaluate(doc,bin,hashlib.sha256(raw).hexdigest())
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__":
    try:main()
    except (OSError,Hold,TypeError,IndexError,KeyError) as exc:
        print("R077_SOURCE_REJECT",str(exc),file=sys.stderr)
        sys.exit(12)
