#!/usr/bin/env python3
"""W04 independent full 31-frame 4-joint WORLD-TRANSLATION parity falsifier.

Test source is the original self-authored G10 PMX/VMD. No native Blender CCD or
physics equality claim. Do not silently drop mismatched bones or frames.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

NAMES=("腰","ひざ","足首","足ＩＫ")
TOL=.002 # source PMX units: imposed BEFORE looking at data

def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

def assess(runtime,direct):
    if runtime.get("status")!="PASS_BABYLON_MMD_ACTUAL_BOUND_RUNTIME_31_FRAMES_ONLY":
        raise ValueError("real MmdRuntime 31-frame source evidence absent")
    cases=[c for c in runtime["cases"] if c.get("case")=="g10"]
    if len(cases)!=1:raise ValueError("G10 original source case ambiguous")
    x=cases[0]
    if x.get("model_sha256")!="fadfc3cb3d365cdb4b0c4cc26652c2e831a02ec7da518caae9142dd711468583":
        raise ValueError("wrong source PMX")
    if x.get("motion_sha256")!="e61ae2953c6cd34904fec2c59ae95fe64ed043ce0cde93e1c3d5db3d12ed149c":
        raise ValueError("wrong source VMD")
    if len(x["snapshots"])!=len(direct)!=31:raise ValueError("incomplete 31-frame evidence")
    comparisons=[]
    for i,(b,d) in enumerate(zip(x["snapshots"],direct)):
        if b["frame"]!=i or d["frame"]!=i:raise ValueError("frame displaced/duplicated")
        bone_list=b["bones"]
        names=[j["name"] for j in bone_list]
        if len(names)!=4 or set(names)!=set(NAMES):raise ValueError("missing/duplicated source bones")
        bone_by_name={j["name"]:j["world_xyz"] for j in bone_list}
        if set(d["bones"])!=set(NAMES):raise ValueError("independent glTF bones unavailable")
        for name in NAMES:
            a=bone_by_name[name];p=d["bones"][name]
            if len(a)!=3 or len(p)!=3 or not all(math.isfinite(v) for v in list(a)+list(p)):
                raise ValueError("nonfinite invalid 3D bone translations")
            dist=math.dist(a,p)
            comparisons.append({"frame":i,"joint_name":name,"world_translation_delta_source_unit":dist,
                                "babylon_xyz":a,"independent_converter_xyz":p})
    fail=[z for z in comparisons if z["world_translation_delta_source_unit"]>TOL]
    first=fail[0] if fail else None
    return {
      "schema":"scp.mmd.w04-31frame-four-bone-world-parity.v1",
      "status":"FAIL_REAL_BABYLON_VS_DIRECT_31FRAME_WORLD_POSE" if first else "PASS_REAL_BABYLON_VS_DIRECT_31FRAME_WORLD_POSE",
      "comparison_scope":"31 frames x 4 named source joint world-space translations, not rotations or skin vertex deformation",
      "source_scale":"PMX_SOURCE_UNIT; METERS_PER_UNIT_UNKNOWN",
      "tested_world_joint_samples":len(comparisons),
      "source_joint_names":list(NAMES),
      "max_world_joint_position_difference":max(z["world_translation_delta_source_unit"] for z in comparisons),
      "tolerance_source_unit":TOL,
      "failed_samples_count":len(fail),
      "first_failure":first,
      "all_samples":comparisons,
      "unqualified":["full bone rotation parity","skin vertex parity","native MikuMikuDance CCD parity",
                     "physical foot-ground contact","actual Babylon browser-rendered pixel output"]
    }

def main():
    p=argparse.ArgumentParser()
    for field in ("runtime","glb","prior","original-glb-verifier","crosscheck","out"):
        p.add_argument("--"+field,required=True,type=Path)
    args=p.parse_args()
    original=load_module(args.original_glb_verifier,"g10b_original")
    bridge=load_module(args.crosscheck,"w04_31_original")
    prior=json.loads(args.prior.read_text())
    source=bridge.glb_31(args.glb,prior,original)
    run=json.loads(args.runtime.read_text())
    report=assess(run,source)
    # Independent negative controls mutate real confirmed source receipts.
    cases=[
      ("wrong_midframe_joint",lambda r:r["cases"][0]["snapshots"][17]["bones"][1]["world_xyz"].__setitem__(0,111.)),
      ("drop_midframe",lambda r:r["cases"][0]["snapshots"].pop(9)),
      ("duplicate_joint",lambda r:r["cases"][0]["snapshots"][7]["bones"][0].update(name="足首")),
    ]
    rejected=[]
    for label,change in cases:
        clone=copy.deepcopy(run)
        change(clone)
        try:
            test=assess(clone,source)
        except ValueError:
            rejected.append(label)
            continue
        if test["status"]!="FAIL_REAL_BABYLON_VS_DIRECT_31FRAME_WORLD_POSE":
            raise AssertionError(f"adversarial world-joint mutation accepted: {label}")
        rejected.append(label)
    report["negative_controls_rejected"]=rejected
    report["input_receipts_sha256"]={q:hashlib.sha256(f.read_bytes()).hexdigest() for q,f in (
        ("native_babylon",args.runtime),("original_mit_glb",args.glb),
        ("g10b_receipt",args.prior),("untouched_g10b_reader",args.original_glb_verifier))}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("W04_WORLD_POSE_31_RESULT",json.dumps({k:v for k,v in report.items() if k!="all_samples"},sort_keys=True),flush=True)
    if report["status"].startswith("FAIL"):raise SystemExit(3)
if __name__=="__main__":main()
