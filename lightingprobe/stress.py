#!/usr/bin/env python3
"""R044 source-original lighting stress: material-only control under two lights.
Uses R037 one-scene matched Cycles experiment. No real actor/source asset.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"renderlab"))
import synthetic_scene as base

CONDITIONS={
    "diffuse_soft":{"key_power":230.0,"key_size":5.0,"fill_power":250.0,"rim_power":150.0},
    "directional_hard":{"key_power":730.0,"key_size":0.45,"fill_power":55.0,"rim_power":350.0},
}

def read_receipt(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    records={}
    geometry_reference=None
    camera_reference=None
    for name,config in sorted(CONDITIONS.items()):
        scene=base.make_scene("baseline")
        for light_name,value in [("key","key_power"),("fill","fill_power"),("rim","rim_power")]:
            light=bpy.data.objects.get(light_name)
            assert light is not None and light.type=="LIGHT"
            light.data.energy=config[value]
        bpy.data.objects["key"].data.size=config["key_size"]
        bpy.context.view_layer.update()

        source_geometry=base.geometry_digest()
        camera=base.canonical_hash({
            "matrix":[round(float(v),7) for row in scene.camera.matrix_world for v in row],
            "projection":"ORTHO","scale":scene.camera.data.ortho_scale,
            "resolution":base.RESOLUTION
        })
        if geometry_reference is not None and source_geometry!=geometry_reference:
            raise RuntimeError("R044 geometry drift between lighting scenes")
        if camera_reference is not None and camera!=camera_reference:
            raise RuntimeError("R044 camera drift between lighting scenes")
        geometry_reference=source_geometry
        camera_reference=camera
        before=base.geometry_digest()
        base.run("baseline",str(out/name/"baseline"),scene)
        base.apply_material_treatment()
        if base.geometry_digest()!=before:
            raise RuntimeError("R044 mesh changed under material treatment")
        base.run("physical_material",str(out/name/"physical_material"),scene)
        baseline=read_receipt(out/name/"baseline"/"receipt.json")
        treatment=read_receipt(out/name/"physical_material"/"receipt.json")
        if baseline["geometry_sha256"]!=treatment["geometry_sha256"]:
            raise RuntimeError("R044 receipt geometry drift")
        if baseline["camera_sha256"]!=treatment["camera_sha256"]:
            raise RuntimeError("R044 receipt camera drift")
        records[name]={
            "config":config,
            "lighting_sha256":base.canonical_hash(config),
            "geometry_sha256":source_geometry,
            "camera_sha256":camera,
            "baseline_receipt_sha256":hashlib.sha256((out/name/"baseline"/"receipt.json").read_bytes()).hexdigest(),
            "material_receipt_sha256":hashlib.sha256((out/name/"physical_material"/"receipt.json").read_bytes()).hexdigest(),
        }
    report={
        "schema":"r044.original.lighting.v1",
        "status":"RENDERED_FOR_INDEPENDENT_EVALUATION",
        "rights":"ORIGINAL_SYNTHETIC",
        "qualification":"NOT_PHOTOREALISM_OR_REAL_CHARACTER_EVIDENCE",
        "source_script_sha256":hashlib.sha256(Path(base.__file__).read_bytes()).hexdigest(),
        "scenarios":records,
    }
    (out/"lighting_manifest.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("R044_REAL_2_LIGHT_X_2_MATERIAL_CYCLES",json.dumps({x:v["lighting_sha256"] for x,v in records.items()},sort_keys=True))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    run(args.out)

if __name__=="__main__":
    main()
