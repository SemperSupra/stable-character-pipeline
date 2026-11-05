#!/usr/bin/env python3
"""Apply immutable reversible wardrobe preset to an imported Blender scene.

Run with Blender:
blender -b original_park_editable.blend --python wardrobe_switch_blender.py \
 -- --preset unclothed --out body_only.blend --receipt body_only.json

The face/body stays intact; toggles independently skinned garment objects,
never deletes geometry or armature and never overwrites the source .blend.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy

PRESETS={
 "unclothed":{"body","hair"},
 "signature":{"body","hair","top","bottom","footwear","accessory"},
 "alternate":{"body","hair","alt_top","alt_bottom","footwear"},
}
ACTORS=("AsterOriginal","JuniperOriginal")
NEEDED={"body","hair","top","bottom","footwear","alt_top","alt_bottom"}

def collect():
    objects={}
    for obj in bpy.data.objects:
        if obj.type!="MESH":continue
        name=obj.name if "_Wardrobe_" in obj.name else obj.data.name
        if "_Wardrobe_" not in name:continue
        actor,slot=name.split("_Wardrobe_",1)
        slot=slot.split(".")[0]
        if actor not in ACTORS:raise ValueError("UNKNOWN_WARDROBE_ACTOR")
        if (actor,slot) in objects:raise ValueError("DUPLICATE_GARMENT_SLOT")
        objects[(actor,slot)]=obj
    for actor in ACTORS:
        slots={x for a,x in objects if a==actor}
        if not NEEDED.issubset(slots):raise ValueError("REQUIRED_GARMENT_SLOTS_MISSING")
        for slot in slots:
            obj=objects[(actor,slot)]
            if not any(x.type=="ARMATURE" for x in obj.modifiers):
                raise ValueError("GARMENT_NOT_SKINNED_TO_ARMATURE")
    return objects

def apply(preset,actor="all"):
    if preset not in PRESETS:raise ValueError("UNKNOWN_PRESET")
    if actor!="all" and actor not in ACTORS:raise ValueError("UNKNOWN_ACTOR")
    wardrobe=collect()
    for (name,slot),obj in wardrobe.items():
        if actor=="all" or name==actor:
            obj.hide_render=slot not in PRESETS[preset]
            obj.hide_set(slot not in PRESETS[preset])
    result={}
    for name in ACTORS:
        shown=sorted(slot for (who,slot),obj in wardrobe.items()
                     if who==name and not obj.hide_render)
        if "body" not in shown:raise ValueError("BODY_MUST_REMAIN")
        result[name]=shown
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--preset",choices=sorted(PRESETS),required=True)
    p.add_argument("--actor",default="all")
    p.add_argument("--out",required=True)
    p.add_argument("--receipt",required=True)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    source=Path(bpy.data.filepath).resolve()
    target=Path(args.out).resolve()
    receipt=Path(args.receipt).resolve()
    if not source.is_file():raise ValueError("SAVED_INPUT_BLEND_REQUIRED")
    if source in (target,receipt) or target==receipt:
        raise ValueError("SOURCE_OVERWRITE_REFUSED")
    sourcehash=hashlib.sha256(source.read_bytes()).hexdigest()
    visible=apply(args.preset,args.actor)
    bpy.context.scene["scp_wardrobe_preset"]=args.preset
    bpy.context.scene["scp_wardrobe_actor"]=args.actor
    target.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(target))
    if hashlib.sha256(source.read_bytes()).hexdigest()!=sourcehash:
        raise ValueError("SOURCE_CHANGED")
    result={"schema":"scp.r009.original_wardrobe_blender_switch.v1",
      "source_blend_sha256":sourcehash,
      "derived_blend_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
      "preset":args.preset,"actor":args.actor,"visible_layers":visible,
      "body_mesh_preserved":True,"source_unchanged":True,
      "garment_fit_quality":"UNKNOWN","human_appearance_accepted":False}
    receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
