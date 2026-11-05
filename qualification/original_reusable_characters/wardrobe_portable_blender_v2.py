#!/usr/bin/env python3
"""Native Blender independent portable-GLB scene/skin acceptance boundary.

Checks *active* layers and rig import, not appearance or cloth physics.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy

ACTORS=("AsterOriginal","JuniperOriginal")

def run(src,preset_receipt,out):
    src=Path(src).resolve();out=Path(out).resolve()
    requested=json.loads(Path(preset_receipt).read_text())
    if requested.get("schema")!="scp.r009.original_wardrobe_preset_receipt.v1":
        raise ValueError("BAD_PORTABLE_RECEIPT")
    if requested.get("derived_sha256")!=hashlib.sha256(src.read_bytes()).hexdigest():
        raise ValueError("PORTABLE_SOURCE_SHA_MISMATCH")
    if src==out:raise ValueError("SOURCE_OVERWRITE_REFUSED")
    bpy.ops.import_scene.gltf(filepath=str(src))
    observed={a:set() for a in ACTORS}
    for ob in bpy.data.objects:
        if ob.type!="MESH":continue
        name=ob.name if "_Wardrobe_" in ob.name else ob.data.name
        if "_Wardrobe_" not in name:continue
        actor,slot=name.split("_Wardrobe_",1)
        slot=slot.split(".")[0]
        if actor not in observed:raise ValueError("UNKNOWN_ACTOR")
        observed[actor].add(slot)
        mods=[m for m in ob.modifiers if m.type=="ARMATURE"]
        if len(mods)!=1 or len(mods[0].object.data.bones)!=35:
            raise ValueError("PORTABLE_SKIN_IMPORT_FAIL")
    for actor in ACTORS:
        wanted=set(requested["active_layers"][actor])
        if observed[actor]!=wanted:
            raise ValueError("PORTABLE_SCENE_LAYER_MISMATCH:"+actor+
                             ":"+str(sorted(observed[actor]))+"!="+str(sorted(wanted)))
        if not {"body","hair"}.issubset(observed[actor]):
            raise ValueError("PORTABLE_BODY_MISSING")
    result={"schema":"scp.r009.original_portable_native.v2",
        "source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
        "actors":{a:sorted(observed[a]) for a in ACTORS},
        "joint_count_per_actor":35,"scene_skin_import":"PASS",
        "visual_garment_body_intersection":"UNKNOWN_NOT_MEASURED",
        "human_appearance_accepted":False}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--portable-receipt",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    print(json.dumps(run(args.input,args.portable_receipt,args.out),sort_keys=True))
