"""R051 source lineage diagnosis for two zero-displacement MPFB morph exports.

Admits neither a named shape key nor active slider as a real geometry control
unless native visible source keys and actual glTF POSITION target agree.
"""
import argparse
import json
import math
import os
import sys
import bpy

sys.path.insert(0,os.path.dirname(__file__))
import morph_mask_preserving as core

def hold(msg): raise RuntimeError("R051_MORPH_SOURCE_HOLD "+msg)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True)
    opts=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    source_path=os.path.join(opts.out,"mpfb-official-anatomy.blend")
    original_hash=core.hfile(source_path)
    body=bpy.data.objects.get("R036_Official_MPFB_Human")
    rig=bpy.data.objects.get("R036_Official_MPFB_Rig")
    if body is None or rig is None: hold("official native body/rig missing")
    masked=[m for m in body.modifiers if m.type=="MASK"]
    if len(masked)!=1: hold("source must have one known helper-mask")
    keep,removed=core.mask_members(body,masked[0])
    meta=core.keymeta(body)
    keys=body.data.shape_keys.key_blocks
    if len(meta)!=9 or len(keep)!=13380:
        hold("original source morph/body/visible cardinality drifted")
    results=[]
    for entry in meta:
        if entry["name"]=="Basis": continue
        k=keys[entry["name"]]
        rel=k.relative_key
        if rel is None:hold("shape key lacks source relative ancestry")
        visible=[(k.data[i].co-rel.data[i].co).length for i in keep]
        hidden=[(k.data[i].co-rel.data[i].co).length for i in removed]
        max_vis=max(visible)
        max_hidden=max(hidden)
        results.append({
            "name":entry["name"],"value":entry["value"],"mute":entry["mute"],
            "visible_points":len(visible),
            "visible_nonzero_points":sum(x>1e-7 for x in visible),
            "max_visible_relative_displacement_m":max_vis,
            "max_hidden_relative_displacement_m":max_hidden,
            "raw_key_effective_on_evaluated_visible_surface":max_vis>1e-7})
    if len(results)!=8:hold("source has not eight relative morph channels")
    if original_hash!=core.hfile(source_path):hold("source .blend mutated")
    receipt={"schema":"r051.native-mpfb.source-morph-effectiveness.v1",
      "status":"SOURCE_NATIVE_MORPH_DIAGNOSTIC_ONLY",
      "source_blend_sha256":original_hash,"original_unchanged":True,
      "evaluated_body_count":len(keep),"raw_count":len(body.data.vertices),
      "source_relative_keys":results,
      "source_effective_visible_morph_count":sum(x["raw_key_effective_on_evaluated_visible_surface"] for x in results),
      "limits":"Only raw Blender source relative-key geometry; actual glTF exported morph comparison is independent; no effective expression/evaluation during simulation, medical anatomy or real film"}
    with open(os.path.join(opts.out,"r051-native-morph-effectiveness.json"),"w",encoding="utf-8") as o:
        json.dump(receipt,o,indent=2,sort_keys=True)
    print("R051_NATIVE_MORPH_AUDIT "+json.dumps(receipt,sort_keys=True))

if __name__=="__main__":main()
