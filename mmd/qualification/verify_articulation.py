#!/usr/bin/env python3
"""Independent binary glTF and actual-PNG G7 articulation falsification."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from verify_interchange import parse_glb


def vector_accessor(g, raw, index, dimension):
    accessor=g["accessors"][index]
    expected={1:"SCALAR",4:"VEC4"}[dimension]
    if accessor["componentType"] != 5126 or accessor["type"] != expected:
        raise ValueError("unsupported animation accessor")
    if accessor.get("sparse"):
        raise ValueError("sparse animation accessor not independently supported")
    bv=g["bufferViews"][accessor["bufferView"]]
    if bv.get("buffer",0)!=0:
        raise ValueError("external GLB animation bytes")
    count=accessor["count"]
    if count<2 or count>1000:
        raise ValueError("missing/oversized sampled track")
    stride=bv.get("byteStride",dimension*4)
    if stride<dimension*4:
        raise ValueError("invalid accessor stride")
    off=bv.get("byteOffset",0)+accessor.get("byteOffset",0)
    values=[]
    for i in range(count):
        k=off+i*stride
        if k+dimension*4>len(raw):
            raise ValueError("out of bounds animation accessor")
        v=struct.unpack_from("<"+"f"*dimension,raw,k)
        if not all(math.isfinite(x) for x in v):
            raise ValueError("NaN or infinite channel sample")
        values.append(v if dimension!=1 else v[0])
    return values


def inspect_rotations(g, raw):
    joints={j for skin in g.get("skins",[]) for j in skin.get("joints",[])}
    if len(joints)<3:
        raise AssertionError("expected at least 3 true skin joints")
    out=[]
    for anim in g.get("animations",[]):
        for channel in anim.get("channels",[]):
            target=channel["target"]
            if target.get("path")!="rotation" or target.get("node") not in joints:
                continue
            sampler=anim["samplers"][channel["sampler"]]
            times=vector_accessor(g,raw,sampler["input"],1)
            quats=vector_accessor(g,raw,sampler["output"],4)
            if len(times)!=len(quats):
                raise AssertionError("quaternion/timestamp sample count mismatch")
            if any(b<a for a,b in zip(times,times[1:])):
                raise AssertionError("non-monotonic quaternion sample times")
            if abs(times[0])>1e-4 or abs(times[-1]-1.0)>1e-3:
                raise AssertionError("misaligned rotation channel time domain: "+str((times[0],times[-1])))
            for q in quats:
                norm=sum(v*v for v in q)
                if abs(norm-1.0)>.05:
                    raise AssertionError("invalid nonunit quaternion")
            dot=abs(sum(x*y for x,y in zip(quats[0],quats[-1])))
            angle=2*math.acos(max(-1.0,min(1.0,dot)))
            if angle>.10:
                out.append({"node":target["node"],"samples":len(times),"angle_radians":angle,
                            "first_second":times[0],"last_second":times[-1]})
    if len({x["node"] for x in out})<2:
        raise AssertionError("two independently rotated skinned joint channels missing "+str(out))
    return {"skin_joint_count":len(joints),"animated_rotation_tracks":out}


def self_test():
    try:
        inspect_rotations({"skins":[],"animations":[]},b"")
    except AssertionError:
        pass
    else:
        raise AssertionError("accepted missing skeleton")
    bad={"accessors":[{"type":"VEC4","componentType":5126,"bufferView":0,"count":2}],
         "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":32}]}
    try:
        vector_accessor(bad,b"\xff"*32,0,4)
    except ValueError:
        pass
    else:
        raise AssertionError("accepted NaN/Inf rotation track")
    print("EXPECTED_REJECTIONS missing_skeleton nonfinite_quaternion")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        self_test()
        return
    glb=a.out/"articulated_ribbon.glb"
    g,raw=parse_glb(glb)
    rot=inspect_rotations(g,raw)
    report=json.loads((a.out/"articulation_blender_receipt.json").read_text())
    if report.get("status")!="PASS_IMPORTED_MULTI_BONE_WEIGHTED_SKIN_AND_TWO_JOINT_ROTATIONS":
        raise AssertionError("failed raw Blender evaluation receipt")
    if report.get("tip_min_motion",0)<=.12 or report.get("anchor_max_motion",1)>=.08:
        raise AssertionError("wrist moved without correct root fixture skin anchoring")
    from PIL import Image,ImageChops
    images=[]
    for n in (0,15,30):
        img=a.out/f"articulation_{n:04d}.png"
        if img.stat().st_size<1000:
            raise AssertionError("missing/empty visual proof "+str(img))
        with Image.open(img) as it:
            assert it.size==(360,360),it.size
            images.append(it.convert("RGB"))
    if len({hashlib.sha256(x.tobytes()).hexdigest() for x in images})<3:
        raise AssertionError("frame sequence frozen")
    changed=[]
    for img in images[1:]:
        delta=ImageChops.difference(images[0],img)
        count=sum(1 for px in delta.getdata() if max(px)>20)
        changed.append(count)
        if count<250:
            raise AssertionError("visible wrist/arm articulation not demonstrated")
    contact=Image.new("RGB",(1080,360))
    for i,img in enumerate(images):
        contact.paste(img,(i*360,0))
    contact.save(a.out/"articulation_contact_sheet.png")
    proof={
      "schema":"scp.mmd.articulation.verification.v1",
      "result":"PASS_INDEPENDENT_MULTI_JOINT_ROTATIONS_SKIN_AND_VISIBLE_MOTION",
      "source_glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
      "animation":rot,
      "pixel_change_f15":changed[0],
      "pixel_change_f30":changed[1],
      "source_rights":"synthetic generated fixture only",
      "render_scope":"diagnostic emission, not toon/material equivalence",
      "unqualified":["MMD IK","rigidbody physics","morphs","full-human anatomy","native MMD solver parity"]
    }
    (a.out/"articulation_verified.json").write_text(json.dumps(proof,indent=2,sort_keys=True)+"\n")
    print(json.dumps(proof,sort_keys=True))


if __name__=="__main__":
    main()
