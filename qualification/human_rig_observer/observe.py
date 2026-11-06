#!/usr/bin/env python3
"""Read-only, standalone GLB 35-joint human/wardrobe geometry contract observer.

Does not import the producer or rely on its asserted receipts. Source-original
synthetic Aster/Juniper only; no private identity, Blender render or photo fit.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

ACTORS=("AsterOriginal","JuniperOriginal")
REQUIRED=("body","hair","top","bottom","footwear","alt_top","alt_bottom")

class InvalidModel(ValueError):
    pass

def require(ok, message):
    if not ok:raise InvalidModel(message)

def load_glb(raw):
    require(len(raw)>=32 and raw[:4]==b"glTF","invalid binary GLB magic/header")
    magic,version,total=struct.unpack_from("<4sII",raw)
    require(version==2 and total==len(raw),"inconsistent GLB length/version")
    n,kind=struct.unpack_from("<I4s",raw,12)
    require(kind==b"JSON" and 20+n+8<=len(raw),"missing GLB JSON chunk")
    try:doc=json.loads(raw[20:20+n])
    except (ValueError,UnicodeError) as e:raise InvalidModel("invalid glTF document") from e
    pos=20+n
    length,tag=struct.unpack_from("<I4s",raw,pos)
    require(tag==b"BIN\0" and pos+8+length==len(raw),"invalid GLB BIN chunk")
    require(isinstance(doc,dict),"GLB JSON root must be object")
    return doc,raw[pos+8:]

def values(doc,blob,index):
    require(type(index) is int and 0<=index<len(doc["accessors"]),"invalid accessor")
    a=doc["accessors"][index]
    require("bufferView" in a and "sparse" not in a,"sparse or absent accessor unsupported")
    view=doc["bufferViews"][a["bufferView"]]
    require(view.get("buffer")==0 and "byteStride" not in view,"noncontiguous or external buffer unsupported")
    types={5121:("B",1),5123:("H",2),5125:("I",4),5126:("f",4)}
    dims={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4,"MAT4":16}
    require(a.get("componentType") in types and a.get("type") in dims,"unsupported accessor type")
    letter,width=types[a["componentType"]]
    per=dims[a["type"]]
    count=a.get("count")
    require(type(count) is int and 0<count<=5_000_000,"invalid accessor count")
    off=view.get("byteOffset",0)+a.get("byteOffset",0)
    size=count*per*width
    require(off>=0 and size<=len(blob) and off+size<=len(blob),"accessor outside BIN")
    require(off+size<=view.get("byteOffset",0)+view["byteLength"],"accessor outside buffer view")
    return list(struct.iter_unpack("<"+letter*per,blob[off:off+size]))

def hierarchy(doc):
    nodes=doc["nodes"];parents={}
    for i,n in enumerate(nodes):
        for child in n.get("children",[]):
            require(type(child) is int and 0<=child<len(nodes) and child!=i,"invalid child")
            require(child not in parents,"duplicate node parent")
            parents[child]=i
    visited=set()
    def visit(i,visiting):
        require(i not in visiting,"node hierarchy cycle")
        if i in visited:return
        visiting.add(i)
        for child in nodes[i].get("children",[]):visit(child,visiting)
        visiting.remove(i)
        visited.add(i)
    for i in range(len(nodes)):visit(i,set())
    return parents

def analyze(data):
    doc,blob=load_glb(data)
    require(doc.get("asset",{}).get("version")=="2.0","wrong glTF version")
    extras=doc.get("extras",{})
    require(extras.get("source_class")=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","source outside public synthetic custody")
    wc=extras.get("wardrobe_contract",{})
    require(wc.get("schema")=="scp.original_wardrobe.v1","missing wardrobe contract")
    require(wc.get("appearance_approved") is False,"unexpected appearance claim")
    skins=doc.get("skins",[])
    require(len(skins)==2,"expected two independently rigged original humans")
    nodes=doc["nodes"]
    parents=hierarchy(doc)
    names={n.get("name"):i for i,n in enumerate(nodes)}
    require(len(names)==len(nodes),"duplicate node names")
    all_meshes=doc["meshes"]
    actor_metrics={}
    for actor_index,actor in enumerate(ACTORS):
        skin=skins[actor_index]
        joints=skin["joints"]
        require(len(joints)==35 and len(set(joints))==35,"missing or duplicate 35 joints")
        require(all(type(j) is int and 0<=j<len(nodes) for j in joints),"joint index outside nodes")
        require(all(nodes[j].get("name","").startswith(actor+"_") for j in joints),"cross-actor joint contamination")
        ibm=values(doc,blob,skin["inverseBindMatrices"])
        require(len(ibm)==35 and all(len(m)==16 and all(math.isfinite(x) for x in m) for m in ibm),"invalid inverse binds")
        roots=[i for i,n in enumerate(nodes) if n.get("name")==actor+"_SceneRoot"]
        require(len(roots)==1,"missing actor scene root")
        target=roots[0];slots={};triangles=0;points=0;vertices_weighted=0
        for slot in REQUIRED:
            name=actor+"_Wardrobe_"+slot
            require(name in names,"missing required detachable clothing/body slot "+name)
            i=names[name];n=nodes[i]
            require(n.get("skin")==actor_index,"garment does not use own skeleton")
            mesh=n.get("mesh")
            require(type(mesh) is int and 0<=mesh<len(all_meshes),"invalid mesh binding")
            slots[slot]=mesh
            require(all_meshes[mesh].get("primitives"),"empty mesh")
            for prim in all_meshes[mesh]["primitives"]:
                att=prim.get("attributes",{})
                require(all(x in att for x in ("POSITION","JOINTS_0","WEIGHTS_0")),"missing skin channels")
                pos=values(doc,blob,att["POSITION"])
                js=values(doc,blob,att["JOINTS_0"])
                ws=values(doc,blob,att["WEIGHTS_0"])
                require(len(pos)==len(js)==len(ws),"inconsistent vertex attribute counts")
                require(len(pos)>0,"zero vertex primitive")
                for vv,jv,wv in zip(pos,js,ws):
                    require(len(jv)==4 and len(wv)==4,"invalid influence count")
                    require(all(math.isfinite(x) for x in vv+wv),"nonfinite vertex or weight")
                    require(all(type(x) is int and 0<=x<35 for x in jv),"invalid skin joint index")
                    require(all(v>=0 for v in wv) and abs(sum(wv)-1)<1e-4,"skin weights not normalized")
                    if len([x for x in wv if x>1e-5])>1:vertices_weighted+=1
                ind=values(doc,blob,prim["indices"])
                require(len(ind)%3==0 and all(0<=x[0]<len(pos) for x in ind),"bad triangle indices")
                triangles+=len(ind)//3;points+=len(pos)
        require(slots["body"]!=slots["top"] and slots["body"]!=slots["alt_top"],"body merged into clothing mesh")
        require(triangles>100 and points>100,"insufficient skinned body+wardrobe")
        actor_metrics[actor]={"joint_count":35,"required_slots":list(REQUIRED),
                              "vertices":points,"triangles":triangles,"multi_influence_vertices":vertices_weighted}
    anims=doc.get("animations",[])
    require(len(anims)==1 and len(anims[0].get("channels",[]))>=60,"missing original gait animation")
    channels=anims[0]["channels"];samplers=anims[0]["samplers"]
    for ch in channels:
        s=samplers[ch["sampler"]]
        times=values(doc,blob,s["input"])
        require(len(times)==72 and abs(times[0][0])<1e-6 and abs(times[-1][0]-71/12)<1e-4,"wrong 72-frame clock")
        require(all(times[i][0]<times[i+1][0] for i in range(71)),"nonmonotonic animation clock")
    return {
      "schema":"scp.r009_35joint_readonly_observation.v1",
      "sha256":hashlib.sha256(data).hexdigest(),
      "subject_class":"public_original_synthetic_human",
      "actors":actor_metrics,
      "frame_count":72,
      "camera_observations":"NOT_RUN",
      "photo_fit":"NOT_RUN",
      "skin_collision":"UNKNOWN",
      "bone_anatomy":"UNKNOWN",
      "visual_acceptance":False,
      "model_mutation":False,
      "disposition":"STRUCTURAL_35JOINT_AND_WARDROBE_OBSERVED_ONLY"
    }

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True)
 p.add_argument("--out",required=True)
 a=p.parse_args()
 data=Path(a.input).read_bytes()
 if len(data)>64<<20:raise InvalidModel("GLB too large")
 r=analyze(data)
 Path(a.out).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
 print(json.dumps(r,sort_keys=True))
if __name__=="__main__":main()
