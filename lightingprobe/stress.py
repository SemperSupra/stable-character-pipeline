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
    # Build EXACTLY one scene, then change only lights and shader nodes.
    # Never rebuild any geometry between either lighting or material treatment.
    scene=base.make_scene("baseline")
    source_geometry=base.geometry_digest()
    camera=base.canonical_hash({
        "matrix":[round(float(v),7) for row in scene.camera.matrix_world for v in row],
        "projection":"ORTHO","scale":scene.camera.data.ortho_scale,
        "resolution":base.RESOLUTION
    })
    records={}
    for name,config in sorted(CONDITIONS.items()):
        records[name]={
            "config":config,
            "lighting_sha256":base.canonical_hash(config),
            "geometry_sha256":source_geometry,
            "camera_sha256":camera,
        }
    for arm in ("baseline","physical_material"):
        if arm=="physical_material":
            base.apply_material_treatment()
            if base.geometry_digest()!=source_geometry:
                raise RuntimeError("R044 mesh drift under material treatment")
        for name,config in sorted(CONDITIONS.items()):
            for light_name,value in [("key","key_power"),("fill","fill_power"),("rim","rim_power")]:
                light=bpy.data.objects.get(light_name)
                if light is None or light.type!="LIGHT":
                    raise RuntimeError("R044 missing expected light "+light_name)
                light.data.energy=config[value]
            bpy.data.objects["key"].data.size=config["key_size"]
            bpy.context.view_layer.update()
            if base.geometry_digest()!=source_geometry:
                raise RuntimeError("R044 mesh drift under lighting intervention")
            render_dir=out/name/arm
            base.run(arm,str(render_dir),scene)
            receipt=read_receipt(render_dir/"receipt.json")
            if receipt["geometry_sha256"]!=source_geometry or receipt["camera_sha256"]!=camera:
                raise RuntimeError("R044 source or camera drift in emitted receipt")
            key="baseline_receipt_sha256" if arm=="baseline" else "material_receipt_sha256"
            records[name][key]=hashlib.sha256((render_dir/"receipt.json").read_bytes()).hexdigest()
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
