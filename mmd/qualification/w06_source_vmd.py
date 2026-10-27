#!/usr/bin/env python3
"""Actual source-native VMD generator: scale original self-authored IK target."""
import argparse,importlib.util,hashlib,json,sys
from pathlib import Path

SRC_SHA="e61ae2953c6cd34904fec2c59ae95fe64ed043ce0cde93e1c3d5db3d12ed149c"
SCALE=0.75
p=argparse.ArgumentParser()
p.add_argument("--source",type=Path,required=True)
p.add_argument("--original",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args()
before=a.original.read_bytes()
if hashlib.sha256(before).hexdigest()!=SRC_SHA:raise ValueError("wrong authoritative rights-clean IK source VMD")
f=a.source/"mmd_tools"/"core"/"vmd"/"__init__.py"
spec=importlib.util.spec_from_file_location("w06_upstream_real_vmd",f)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
doc=mod.File();doc.load(filepath=str(a.original))
tracks=doc.boneAnimation
if set(tracks)!={"足ＩＫ"}:raise ValueError("unexpected source motion controller")
frames=tracks["足ＩＫ"]
if [k.frame_number for k in frames]!=[0,30]:raise ValueError("unexpected source animation time span")
if any(any(abs(x)>1 for x in key.location) for key in frames):raise ValueError("source motion out of bounded range")
old=[tuple(k.location) for k in frames]
for key in frames:
    key.location=tuple(x*SCALE for x in key.location)
a.out.parent.mkdir(parents=True,exist_ok=True)
doc.save(filepath=str(a.out))
ret=mod.File();ret.load(filepath=str(a.out))
expected=[tuple(x*SCALE for x in pos) for pos in old]
got=[tuple(k.location) for k in ret.boneAnimation["足ＩＫ"]]
if any(max(abs(x-y) for x,y in zip(e,o))>1e-6 for e,o in zip(expected,got)):
    raise ValueError("genuine native VMD reload is not source metamorphism")
receipt={"schema":"scp.mmd.w06-source-native-vmd.v1",
    "source_sha256":SRC_SHA,"derived_sha256":hashlib.sha256(a.out.read_bytes()).hexdigest(),
    "source_rights":"original synthetic G10 source only",
    "source_frames":[0,30],"scale":SCALE,"old_goal":old,"derived_goal":got,
    "status":"PASS_NATIVE_MMD_VMD_SERIALIZER_SOURCE_TRANSFORM_RELOAD"}
(a.out.parent/"w06_transform_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print("W06_NATIVE_SOURCE_MOTION",json.dumps(receipt,sort_keys=True))
