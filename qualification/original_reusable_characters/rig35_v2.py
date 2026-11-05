#!/usr/bin/env python3
"""Source-original 17 -> 35 joint rig expansion, reversible GLB derivative.

Self-authored skeleton helpers, per-vertex skin attributes, toe and finger
keyframes. No third-party models or protected R009 source. This verifies
functional extra control paths, not human anatomical or physical accuracy.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from verify_original_glb import decode, accessory

def glb_pack(d, b):
    b = bytes(b)
    d["buffers"][0]["byteLength"] = len(b)
    raw = json.dumps(d, sort_keys=True, separators=(",", ":")).encode()
    raw += b" " * (-len(raw) % 4)
    b += b"\0" * (-len(b) % 4)
    total = 12 + 8 + len(raw) + 8 + len(b)
    return (struct.pack("<4sII", b"glTF", 2, total) +
            struct.pack("<I4s", len(raw), b"JSON") + raw +
            struct.pack("<I4s", len(b), b"BIN\0") + b)

def add_accessor(d, b, values, typ, components):
    while len(b) % 4: b.append(0)
    offset = len(b)
    b.extend(struct.pack("<" + "f"*len(values), *values))
    view = len(d["bufferViews"])
    d["bufferViews"].append({"buffer":0,"byteOffset":offset,
                              "byteLength":4*len(values)})
    idx = len(d["accessors"])
    d["accessors"].append({"bufferView":view,"componentType":5126,
                           "count":len(values)//components,"type":typ})
    return idx

def main_expand(input_glb, output_glb):
    raw=Path(input_glb).read_bytes()
    d,bb=decode(raw)
    assert d["extras"]["source_class"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
    assert len(d["skins"])==len(d["meshes"])==2
    b=bytearray(bb)
    nodes=d["nodes"]
    animation=d["animations"][0]
    altered={"clavicle":0,"heel":0,"ball":0,"toe":0,"finger":0}
    all_additions=[]
    frames=72
    source_times=animation["samplers"][0]["input"]
    for actor in ("AsterOriginal","JuniperOriginal"):
        actor_i=0 if actor=="AsterOriginal" else 1
        skin=d["skins"][actor_i]
        assert len(skin["joints"])==17
        old_matrix=accessory(d,bb,skin["inverseBindMatrices"])
        assert len(old_matrix)==17
        ibm=[v for matrix in old_matrix for v in matrix]
        node_id={x["name"].removeprefix(actor+"_"):i for i,x in enumerate(nodes)
                 if x["name"].startswith(actor+"_")}
        for role in ("chest","shoulder_L","shoulder_R","ankle_L",
                     "ankle_R","wrist_L","wrist_R"):
            assert role in node_id
        created={}
        specs=[]
        for sign,side in ((-1,"L"),(1,"R")):
            specs.extend([
              ("clavicle_"+side,"chest",(sign*.115,1.375,0),.025),
              ("heel_"+side,"ankle_"+side,(sign*.14,.060,.055),.03),
              ("ball_"+side,"ankle_"+side,(sign*.14,.055,-.115),.15),
              ("toe_"+side,"ball_"+side,(sign*.14,.055,-.170),.20)])
            for finger in range(5):
                specs.append((f"finger{finger}_{side}","wrist_"+side,
                    (sign*.45+(finger-2)*.018,.689,0),.020))
        rest={
            "chest":(0,1.38,0),
            "ankle_L":(-.14,.115,.02),"ankle_R":(.14,.115,.02),
            "wrist_L":(-.45,.79,0),"wrist_R":(.45,.79,0),
        }
        by_role={}
        for role,parent,xyz,amp in specs:
            parent_id=created[parent] if parent in created else node_id[parent]
            if parent not in rest: raise ValueError("UNKNOWN_REST_PARENT:"+parent)
            parent_pos=rest[parent]
            rel=[xyz[k]-parent_pos[k] for k in range(3)]
            idx=len(nodes)
            nodes.append({"name":actor+"_"+role,"translation":rel})
            nodes[parent_id].setdefault("children",[]).append(idx)
            created[role]=idx
            rest[role]=xyz
            by_role[role]=len(skin["joints"])
            skin["joints"].append(idx)
            x,y,z=xyz
            ibm.extend([1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,-x,-y,-z,1.])
            # Genuine animated quaternion channel; small source-authored control.
            quats=[]
            for f in range(frames):
                t=f/12.
                phase=2*math.pi*1.25*t+(0 if actor_i==0 else .4)
                angle=amp*math.sin(phase)
                quats.extend((math.sin(angle/2),0.,0.,math.cos(angle/2)))
            out=add_accessor(d,b,quats,"VEC4",4)
            sampler=len(animation["samplers"])
            animation["samplers"].append({"input":source_times,
                   "output":out,"interpolation":"LINEAR"})
            animation["channels"].append({"sampler":sampler,
                   "target":{"node":idx,"path":"rotation"}})
            all_additions.append(role)
        # Only rest-axis preserving reparenting of original shoulder nodes.
        for sign,side in ((-1,"L"),(1,"R")):
            parent=node_id["chest"]
            shoulder=node_id["shoulder_"+side]
            assert shoulder in nodes[parent]["children"]
            nodes[parent]["children"].remove(shoulder)
            nodes[created["clavicle_"+side]].setdefault("children",[]).append(shoulder)
            nodes[shoulder]["translation"]=[sign*.120,-.025,0.]
        skin["inverseBindMatrices"]=add_accessor(d,b,ibm,"MAT4",16)
        assert len(skin["joints"])==35
        # Rewrite only own generated skin/vertex joint attributes in place.
        for prim in d["meshes"][actor_i]["primitives"]:
            mat=d["materials"][prim["material"]]["name"]
            attr=prim["attributes"]
            pos=accessory(d,bb,attr["POSITION"])
            ja=d["accessors"][attr["JOINTS_0"]]
            wa=d["accessors"][attr["WEIGHTS_0"]]
            jv=d["bufferViews"][ja["bufferView"]]
            wv=d["bufferViews"][wa["bufferView"]]
            assert ja["componentType"]==5121 and wa["componentType"]==5126
            joff=jv["byteOffset"]+ja.get("byteOffset",0)
            woff=wv["byteOffset"]+wa.get("byteOffset",0)
            for n,(x,y,z) in enumerate(pos):
                new=None;kind=None
                if mat in ("darkBoots","earthBoots") and y<.16:
                    side="L" if x<0 else "R"
                    if z<-.155:kind="toe"
                    elif z<-.075:kind="ball"
                    elif z>.005:kind="heel"
                    if kind:new=[(by_role[kind+"_"+side],1.)]
                elif mat in ("coralJacket","tealJacket") and y>1.26 and abs(x)>.16 and abs(x)<.31:
                    side="L" if x<0 else "R"
                    kind="clavicle"
                    new=[(by_role["clavicle_"+side],.38),(2,.62)]
                elif mat in ("skinWarm","skinCool") and .615<y<.712 and abs(x)>.40:
                    side="L" if x<0 else "R"
                    center= -.45 if side=="L" else .45
                    finger=min(range(5),key=lambda i:abs(x-(center+(i-2)*.018)))
                    if abs(x-(center+(finger-2)*.018))<.013:
                        kind="finger"
                        new=[(by_role[f"finger{finger}_{side}"],1.)]
                if new:
                    joints=[v for v,_ in new]+[0]*(4-len(new))
                    weights=[v for _,v in new]+[0.]*(4-len(new))
                    struct.pack_into("<4B",b,joff+4*n,*joints)
                    struct.pack_into("<4f",b,woff+16*n,*weights)
                    altered[kind]+=1
    assert len(all_additions)==36
    assert all(altered[k]>0 for k in altered),altered
    d["extras"]["rig_profile"]="ORIGINAL_FUNCTIONAL_35JOINT_RESEARCH"
    d["extras"]["human_gait_acceptance"]="UNKNOWN"
    d["extras"]["anatomical_acceptance"]="UNKNOWN"
    payload=glb_pack(d,b)
    Path(output_glb).write_bytes(payload)
    return {"schema":"scp.r009.original_35_joint_experimental.v1",
            "original_sha256":hashlib.sha256(raw).hexdigest(),
            "derived_sha256":hashlib.sha256(payload).hexdigest(),
            "per_actor_joints":35,"new_animated_channels":36,
            "per_vertex_affected":altered,"frames":72,
            "scientific_acceptance":"UNKNOWN_NOT_HUMAN_QUALIFIED"}

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True);ap.add_argument("--output",required=True)
    ap.add_argument("--receipt",required=True)
    a=ap.parse_args()
    r=main_expand(a.input,a.output)
    Path(a.receipt).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print(json.dumps(r,sort_keys=True))
