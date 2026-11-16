#!/usr/bin/env python3
"""Independent bounded R044 receipt validator; technical correctness, not realism."""
import argparse
import hashlib
import json
import math
from pathlib import Path

EXPECTED = {
    "diffuse_soft":{"key_power":230.0,"key_size":5.0,"fill_power":250.0,"rim_power":150.0},
    "directional_hard":{"key_power":730.0,"key_size":0.45,"fill_power":55.0,"rim_power":350.0},
}

def reject(msg):
    raise ValueError("R044_HOLD_"+msg)

def strict_json(path):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: reject("DUPLICATE_KEY")
            result[k]=v
        return result
    if path.is_symlink() or not path.is_file() or path.stat().st_size>2*1024*1024:
        reject("UNSAFE_OR_MISSING_JSON")
    return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=pairs,parse_constant=lambda _:reject("NONFINITE_JSON"))

def sha(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>32*1024*1024:
        reject("UNSAFE_OR_MISSING_ARTIFACT")
    return hashlib.sha256(path.read_bytes()).hexdigest()

def config_hash(config):
    return hashlib.sha256(json.dumps(config,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()

def validate_manifest(data):
    if data.get("schema")!="r044.original.lighting.v1" or data.get("rights")!="ORIGINAL_SYNTHETIC":
        reject("RIGHTS_OR_SCHEMA")
    if data.get("status")!="RENDERED_FOR_INDEPENDENT_EVALUATION" or data.get("qualification")!="NOT_PHOTOREALISM_OR_REAL_CHARACTER_EVIDENCE":
        reject("FALSE_QUALIFICATION")
    scenarios=data.get("scenarios")
    if not isinstance(scenarios,dict) or set(scenarios)!=set(EXPECTED):
        reject("SCENARIOS")
    if len({config_hash(c) for c in EXPECTED.values()})!=2:
        reject("NON_DISTINCT_LIGHTS")
    for name,config in EXPECTED.items():
        found=scenarios[name]
        if found.get("config")!=config or found.get("lighting_sha256")!=config_hash(config):
            reject("LIGHT_CONFIG_MUTATED_"+name)
        if not all(isinstance(x,int) or isinstance(x,float) for x in config.values()):
            reject("NON_NUMERIC_CONFIG")
        if any(not math.isfinite(x) or x<=0 for x in config.values()):
            reject("INVALID_LIGHTS")
        for key in ("geometry_sha256","camera_sha256","baseline_receipt_sha256","material_receipt_sha256"):
            v=found.get(key)
            if not isinstance(v,str) or len(v)!=64 or any(ch not in "0123456789abcdef" for ch in v):
                reject("INVALID_SHA_"+key)
    ss=list(scenarios.values())
    if ss[0]["geometry_sha256"]!=ss[1]["geometry_sha256"] or ss[0]["camera_sha256"]!=ss[1]["camera_sha256"]:
        reject("SCENE_DRIFT_ACROSS_LIGHTS")

def verify(root,source_script):
    m=strict_json(root/"lighting_manifest.json")
    validate_manifest(m)
    if m.get("source_script_sha256")!=sha(source_script):
        reject("SOURCE_SHA")
    result={}
    for name,item in sorted(m["scenarios"].items()):
        b=root/name/"baseline"/"receipt.json"
        t=root/name/"physical_material"/"receipt.json"
        if sha(b)!=item["baseline_receipt_sha256"] or sha(t)!=item["material_receipt_sha256"]:
            reject("RECEIPT_TAMPER")
        br=strict_json(b);tr=strict_json(t)
        if br.get("geometry_sha256")!=item["geometry_sha256"] or tr.get("geometry_sha256")!=item["geometry_sha256"]:
            reject("GEOMETRY_DRIFT")
        if br.get("camera_sha256")!=item["camera_sha256"] or tr.get("camera_sha256")!=item["camera_sha256"]:
            reject("CAMERA_DRIFT")
        if br.get("arm")!="baseline" or tr.get("arm")!="physical_material":
            reject("TREATMENT_SWAP")
        if br.get("source_sha256")!=tr.get("source_sha256") or br.get("animation_sha256")!=tr.get("animation_sha256"):
            reject("SOURCE_OR_MOTION_DRIFT")
        pair=strict_json(root/name/"comparison.json")
        pixel=strict_json(root/name/"exr_pixel_audit.json")
        header=strict_json(root/name/"exr_audit.json")
        if pair.get("status")!="PASS_STRUCTURAL_RENDER_DIFFERENCE_ONLY":
            reject("PAIR_UNVERIFIED")
        if pixel.get("status")!="PASS_NARROW_DECODED_RENDER_PASS_SEMANTICS" or not pixel.get("object_id_exact_equal"):
            reject("EXR_PIXELS_UNVERIFIED")
        if header.get("status")!="EXR_HEADER_CHANNELS_VERIFIED":
            reject("EXR_HEADER_UNVERIFIED")
        if not isinstance(pair.get("changed_pixel_fraction"),(float,int)) or pair["changed_pixel_fraction"]<=.001:
            reject("NO_MATERIAL_DIFFERENCE")
        if not isinstance(pixel.get("max_paired_foreground_depth_delta"),(float,int)) or pixel["max_paired_foreground_depth_delta"]>1e-4:
            reject("UNEXPECTED_DEPTH_DRIFT")
        result[name]={
            "lighting_sha256":item["lighting_sha256"],
            "changed_pixel_fraction":pair["changed_pixel_fraction"],
            "max_paired_depth_delta":pixel["max_paired_foreground_depth_delta"],
            "paired_source":br["source_sha256"]
        }
    return {
        "schema":"r044.original.lighting.v1",
        "status":"PASS_NARROW_2X2_LIGHT_MATERIAL_RENDER_AND_EXR_GATES",
        "qualification":"NO_PHOTOREALISM_OR_HUMAN_PREFERENCE_CONCLUSION",
        "source_sha256":m["source_script_sha256"],
        "conditions":result,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--source-script",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    report=verify(args.root,args.source_script)
    args.out.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
