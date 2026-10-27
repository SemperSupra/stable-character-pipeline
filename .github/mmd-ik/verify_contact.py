#!/usr/bin/env python3
"""G10b independent numerical glTF IK goal vs ankle-contact qualification.

Only public original four-bone PMX/VMD, evaluated two ways by pinned MIT CLI.
Fails closed on inadequate target tracking, but always writes quantitative receipt.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct


def load(path):
    blob=path.read_bytes()
    if len(blob)<20 or blob[:4]!=b"glTF":
        raise ValueError("not GLB")
    _,version,size=struct.unpack_from("<4sII",blob)
    if version!=2 or size!=len(blob):
        raise ValueError("invalid GLB version/length")
    json_size,typ=struct.unpack_from("<I4s",blob,12)
    if typ!=b"JSON":
        raise ValueError("GLB missing JSON chunk")
    scene=json.loads(blob[20:20+json_size].rstrip(b" \t\r\n"))
    next_off=20+json_size
    raw_size,rawtyp=struct.unpack_from("<I4s",blob,next_off)
    if rawtyp!=bytes((66,73,78,0)):
        raise ValueError("GLB missing BIN chunk")
    raw=blob[next_off+8:next_off+8+raw_size]
    return scene,raw


def get_accessor(scene,raw,index):
    a=scene["accessors"][index]
    if a.get("sparse") or a.get("componentType")!=5126:
        raise ValueError("cannot trust sparse or non-F32 motion samples")
    width={"SCALAR":1,"VEC3":3,"VEC4":4}.get(a["type"])
    if width is None or a["count"]>500:
        raise ValueError("unsupported/suspicious glTF motion accessor")
    view=scene["bufferViews"][a["bufferView"]]
    start=view.get("byteOffset",0)+a.get("byteOffset",0)
    stride=view.get("byteStride",width*4)
    if view.get("buffer",0)!=0 or stride<4*width:
        raise ValueError("bad buffer view")
    result=[]
    for n in range(a["count"]):
        off=start+n*stride
        if off+4*width>len(raw):
            raise ValueError("truncated glTF accessor")
        row=struct.unpack_from("<"+"f"*width,raw,off)
        if not all(math.isfinite(v) for v in row):
            raise ValueError("nonfinite kinematic state")
        result.append(row)
    return result


def quat_mul(a,b):
    x,y,z,w=a
    X,Y,Z,W=b
    return (w*X+x*W+y*Z-z*Y,
            w*Y-x*Z+y*W+z*X,
            w*Z+x*Y-y*X+z*W,
            w*W-x*X-y*Y-z*Z)


def rotate(q,v):
    x,y,z,w=q
    t=(2*(y*v[2]-z*v[1]),2*(z*v[0]-x*v[2]),2*(x*v[1]-y*v[0]))
    cross=(y*t[2]-z*t[1],z*t[0]-x*t[2],x*t[1]-y*t[0])
    return tuple(v[i]+w*t[i]+cross[i] for i in range(3))


def contact(path):
    scene,raw=load(path)
    nodes=scene.get("nodes",[])
    names=("腰","ひざ","足首","足ＩＫ")
    index={n:next((i for i,x in enumerate(nodes) if x.get("name")==n),None) for n in names}
    if len(set(index.values()))!=4 or any(x is None for x in index.values()):
        raise AssertionError("missing/duplicated source Japanese IK joint names")
    parent={}
    for i,node in enumerate(nodes):
        for child in node.get("children",[]):
            parent[child]=i
    if parent.get(index["ひざ"])!=index["腰"] or parent.get(index["足首"])!=index["ひざ"]:
        raise AssertionError("joint hierarchy broken")
    action=scene["animations"][0]
    tracks={}
    times=None
    for ch in action["channels"]:
        joint=ch["target"]["node"]
        mode=ch["target"]["path"]
        smpl=action["samplers"][ch["sampler"]]
        t=[v[0] for v in get_accessor(scene,raw,smpl["input"])]
        vals=get_accessor(scene,raw,smpl["output"])
        if len(t)!=31 or any(abs(x-i/30)>1e-3 for i,x in enumerate(t)):
            raise AssertionError("IK motion not sampled on 0–1s 30fps source timeline")
        if times is not None and times!=t:
            raise AssertionError("IK joint timeline differs between channels")
        times=t
        if len(vals)!=len(t):
            raise AssertionError("motion channel missing values")
        tracks[(joint,mode)]=vals

    def world(i,frame,visited=None):
        visited=visited or set()
        if i in visited:
            raise ValueError("cyclic transform graph")
        n=nodes[i]
        tr=tracks.get((i,"translation"),())
        qr=tracks.get((i,"rotation"),())
        loc=tr[frame] if tr else n.get("translation",(0,0,0))
        rot=qr[frame] if qr else n.get("rotation",(0,0,0,1))
        if i not in parent:
            return tuple(loc),tuple(rot)
        pos,base=world(parent[i],frame,visited|{i})
        off=rotate(base,loc)
        return tuple(pos[k]+off[k] for k in range(3)),quat_mul(base,rot)

    errors={}
    for frame in (0,15,30):
        ankle,_=world(index["足首"],frame)
        goal,_=world(index["足ＩＫ"],frame)
        errors[str(frame)]={"ankle_world":ankle,
            "goal_world":goal,"error":math.dist(ankle,goal)}
    if errors["0"]["error"]>.02:
        raise AssertionError("original test fixture not grounded at t=0")
    return errors


def main():
    p=argparse.ArgumentParser()
    for k in ("ik","no-ik","out"):
        p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    enabled=contact(a.ik)
    disabled=contact(a.no_ik)
    # Assert real IK benefit, not merely presence of a solver or more channels.
    # Target 5cm in original scale=1 test geometry and improvement >50% at both mid/end.
    goal_tol=.05
    ratio_tol=.5
    all_good=all(
       enabled[str(f)]["error"]<goal_tol and
       enabled[str(f)]["error"]<ratio_tol*disabled[str(f)]["error"]
       for f in (15,30))
    report={
      "schema":"scp.mmd.ik.contact.v1",
      "status":"PASS_IK_TARGET_TRACKING" if all_good else "FAIL_IK_TARGET_TRACKING",
      "gate_pass":all_good,
      "goal_tolerance_source_units":goal_tol,
      "required_improvement_ratio":ratio_tol,
      "ik_enabled":enabled,
      "ik_disabled":disabled,
      "source_ik_glb_sha256":hashlib.sha256(a.ik.read_bytes()).hexdigest(),
      "source_fk_glb_sha256":hashlib.sha256(a.no_ik.read_bytes()).hexdigest(),
      "scope":"synthetic ankle-to-MMD-goal tracking only; not MMD native solver or rigidbody ground contact"
    }
    a.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps(report,sort_keys=True),flush=True)
    if not all_good:
        raise AssertionError("native-source IK structurally preserved but independent converter failed quantitative foot-goal tracking thresholds")


if __name__=="__main__":
    main()
