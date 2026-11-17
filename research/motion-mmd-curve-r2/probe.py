#!/usr/bin/env python3
"""Real pinned upstream MMD Tools VMD v2 round-trip, original synthetic tracks only.

This is NOT native MMD/Blender playback or character-rig compatibility.
All assertions are directly on actual independently loaded VMD binary data.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import math
import pathlib
import struct
import sys
import tempfile

UPSTREAM = "f1d8a98db5e185cfa73c9b8a8a67fa42d9eb4b14"
NAME = "センター"
MORPH = "まばたき"
IK = "左足ＩＫ"
CURVE = (16, 110, 80, 123)
LINEAR = (20, 20, 107, 107)

def upstream(root: pathlib.Path):
    p = root / "mmd_tools" / "core" / "vmd" / "__init__.py"
    assert p.is_file(), "pinned upstream module missing"
    spec = importlib.util.spec_from_file_location("source_pinned_mmd_vmd", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

def interpolation(curve):
    assert len(curve) == 4 and all(0 <= v <= 127 for v in curve)
    out = []
    for channel in range(4):
        bank = [0] * 16
        for i, v in zip((0, 4, 8, 12), curve if channel == 0 else LINEAR):
            bank[i] = v
        out.extend(bank)
    assert len(out) == 64
    return tuple(out)

def authored(vmd, outpath: pathlib.Path, curve=CURVE):
    obj = vmd.File()
    obj.header = vmd.Header()
    obj.header.model_name = "SCP_R2_ORIGINAL"
    obj.boneAnimation = vmd.BoneAnimation()
    for frame, x in ((0, 0.0), (30, 1.0)):
        k = vmd.BoneFrameKey()
        k.frame_number, k.location = frame, (x, 0.0, 0.0)
        k.rotation = (0.0, 0.0, 0.0, 1.0)
        k.interp = interpolation(curve if frame == 30 else LINEAR)
        obj.boneAnimation[NAME].append(k)
    obj.shapeKeyAnimation = vmd.ShapeKeyAnimation()
    for frame, weight in ((0, 0.0), (30, 0.75)):
        k = vmd.ShapeKeyFrameKey()
        k.frame_number, k.weight = frame, weight
        obj.shapeKeyAnimation[MORPH].append(k)
    obj.propertyAnimation = vmd.PropertyAnimation()
    for frame, state in ((0, 1), (30, 0)):
        k = vmd.PropertyFrameKey()
        k.frame_number, k.visible = frame, True
        k.ik_states = [(IK, state)]
        obj.propertyAnimation.append(k)
    obj.save(filepath=str(outpath))
    return obj

def loaded(vmd, path):
    obj = vmd.File()
    obj.load(filepath=str(path))
    return obj

def check_strict_semantics(obj, curve=CURVE):
    keys = obj.boneAnimation[NAME]
    assert len(keys) == 2 and [x.frame_number for x in keys] == [0, 30]
    assert keys[1].location == (1.0, 0.0, 0.0)
    assert keys[1].rotation == (0.0, 0.0, 0.0, 1.0)
    assert tuple(keys[1].interp) == interpolation(curve), "native VMD interpolation changed"
    shapes = obj.shapeKeyAnimation[MORPH]
    assert [x.frame_number for x in shapes] == [0, 30]
    assert abs(shapes[1].weight - 0.75) < 1e-7
    assert len(obj.propertyAnimation) == 2
    assert [(x.frame_number, x.ik_states) for x in obj.propertyAnimation] == [
        (0, [(IK, 1)]), (30, [(IK, 0)])
    ]
    return {"bones": len(keys), "morph_keys": len(shapes),
            "ik_switches": len(obj.propertyAnimation),
            "target_curve": list(keys[1].interp[0:16:4])}

def cubic(v0, v1, u):
    return 3 * (1-u)**2 * u * v0 + 3 * (1-u) * u*u * v1 + u**3

def curve_at(t, curve):
    # Endpoint invariants are exact; interior x inversion uses bounded bisection.
    # First hosted RED #44037581312 approached endpoints asymptotically instead.
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    x1,y1,x2,y2 = (v/127.0 for v in curve)
    assert 0 <= x1 <= x2 <= 1 and 0 <= y1 <= y2 <= 1
    lo,hi=0.0,1.0
    for _ in range(70):
        mid=(lo+hi)*0.5
        if cubic(x1,x2,mid) < t: lo=mid
        else: hi=mid
    return cubic(y1,y2,(lo+hi)*0.5)

def strict_byte_sections(path, expected):
    data=path.read_bytes()
    assert data.startswith(b"Vocaloid Motion Data 0002") and len(data)>200
    assert struct.unpack_from("<I",data,50)[0] == 2
    assert expected == hashlib.sha256(data).hexdigest()
    # Original generated file has two bone records; then 2 morph records.
    at=54 + 2*111
    assert struct.unpack_from("<I",data,at)[0] == 2
    # Morph records: 15-byte name + 4-byte frame + 4-byte float.
    at+=4 + 2*23
    # Camera, light, self-shadow sections are empty (4B each).
    for _ in range(3):
        assert struct.unpack_from("<I",data,at)[0] == 0
        at += 4
    assert struct.unpack_from("<I",data,at)[0] == 2  # property records
    # Keep full byte count bound by actual upstream serializer, not a general parser.
    assert at + 4 < len(data)
    return len(data)

def run(lane, root):
    vmd=upstream(root)
    with tempfile.TemporaryDirectory(prefix="mmd-r2-original-") as d:
        rootpath=pathlib.Path(d)
        p=rootpath/"nonlinear_original.vmd"
        authored(vmd,p)
        raw=p.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        assert p.stat().st_size < 2048
        report={"lane":lane, "source_class":"SELF_AUTHORED_SYNTHETIC",
                "vendor_commit":UPSTREAM, "source_sha256":digest}
        if lane=="native-parser":
            report.update(check_strict_semantics(loaded(vmd,p)))
            report["bytes"] = strict_byte_sections(p,digest)
            rep=rootpath/"repeat.vmd"
            authored(vmd,rep)
            assert rep.read_bytes()==raw, "nondeterministic VMD serializer"
        elif lane=="subframe-loss":
            native=loaded(vmd,p)
            check_strict_semantics(native)
            control=tuple(native.boneAnimation[NAME][1].interp[0:16:4])
            sample={str(t):curve_at(t,control) for t in (.25,.5,.75)}
            report["subframe_curve"]=sample
            report["linear_counterfactual"]={str(t):t for t in (.25,.5,.75)}
            deviation=max(abs(v-float(k)) for k,v in sample.items())
            report["max_curve_vs_linear"]=deviation
            assert deviation > .10, "nonlinear VMD curve collapsed into linear interpolation"
            # 30 fps endpoint-only export looks identical but loses the subframe profile.
            assert curve_at(0,control)==0 and abs(curve_at(1,control)-1)<1e-15
            assert all(0 < v < 1 for v in sample.values())
        elif lane=="semantic-loss":
            original=loaded(vmd,p)
            check_strict_semantics(original)
            # Derivative with SAME bone positions but omitted morph and IK tracks.
            altered=rootpath/"stripped.vmd"
            stripped=authored(vmd,altered)
            stripped.shapeKeyAnimation=vmd.ShapeKeyAnimation()
            stripped.propertyAnimation=vmd.PropertyAnimation()
            stripped.save(filepath=str(altered))
            again=loaded(vmd,altered)
            assert [(k.frame_number,k.location) for k in again.boneAnimation[NAME]] == [
                (k.frame_number,k.location) for k in original.boneAnimation[NAME]]
            assert not again.shapeKeyAnimation and not again.propertyAnimation
            try:
                check_strict_semantics(again)
            except (AssertionError,KeyError):
                pass
            else:
                raise AssertionError("bone-only derivative silently passed morph/IK admission")
            report["lost_channels"]=["shape_morph","property_ik_switch"]
            # VMD source-byte binding rejects any semantic derivative substituted for original.
            assert hashlib.sha256(altered.read_bytes()).hexdigest()!=digest
        else:
            raise ValueError("unsupported lane")
        report["status"]="PASS_NARROW_VMD_NATIVE_BINARY_RESEARCH"
        report["mmd_playback"]="NOT_RUN"
        report["blender_animated_evaluation"]="NOT_RUN"
        report["cross_rig_or_film"]="UNQUALIFIED"
        print(json.dumps(report,sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream",type=pathlib.Path,required=True)
    p.add_argument("--lane",choices=("native-parser","subframe-loss","semantic-loss"),required=True)
    a=p.parse_args()
    run(a.lane,a.upstream)
