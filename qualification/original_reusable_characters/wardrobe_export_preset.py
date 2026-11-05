#!/usr/bin/env python3
"""Portable preset GLB exporter: same skinned body and independent clothing.

A complete wardrobe library GLB contains ALL layers for authoring. Standard
glTF viewers display every reachable mesh by default, so this export derives
a viewer-ready scene by detaching only unused garment nodes from scene roots.
No vertex/bone/animation/material deletion and no source mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path
from modular_wardrobe_v1 import PRESETS,ACTORS
from rig35_v2 import glb_pack
from verify_original_glb import decode

def export(src,manifest,out,receipt,presets):
    paths=[Path(v).resolve() for v in (src,manifest,out,receipt)]
    if len(set(paths))!=4:raise ValueError("SOURCE_OR_RECEIPT_OVERWRITE_REFUSED")
    if set(presets)!=set(ACTORS) or any(v not in PRESETS for v in presets.values()):
        raise ValueError("INVALID_ACTOR_OR_PRESET")
    raw=Path(src).read_bytes()
    m=json.loads(Path(manifest).read_text())
    if m.get("schema")!="scp.original_wardrobe_manifest.v1" or (
      m.get("derived_sha256")!=hashlib.sha256(raw).hexdigest()):
        raise ValueError("SOURCE_MANIFEST_SHA_MISMATCH")
    d,b=decode(raw)
    if d.get("extras",{}).get("wardrobe_contract",{}).get("schema")!="scp.original_wardrobe.v1":
        raise ValueError("WRONG_SOURCE_CONTRACT")
    roots={n["name"]:i for i,n in enumerate(d["nodes"])}
    status={}
    for actor in ACTORS:
        root=d["nodes"][roots[actor+"_SceneRoot"]]
        children=root["children"]
        wanted=set(PRESETS[presets[actor]])
        actor_map=m["actor_slots"][actor]
        if "body" not in wanted:raise ValueError("BODY_CANNOT_BE_REMOVED")
        for slot,entry in actor_map.items():
            idx=entry["node"]
            if slot in wanted:
                if idx not in children:children.append(idx)
            else:
                if idx in children:children.remove(idx)
        active=sorted(slot for slot,entry in actor_map.items() if entry["node"] in children)
        if not {"body","hair"}.issubset(active):
            raise ValueError("BASE_BODY_AND_GROOM_REQUIRED")
        if (set(active)-wanted):
            raise ValueError("INACTIVE_GARMENT_STILL_VISIBLE")
        status[actor]=active
    d["extras"]["wardrobe_preset_state"]={
      "schema":"scp.r009.original_wardrobe_portable_preset.v1",
      "active_presets":dict(presets),
      "active_layers":status,"preserves_all_source_geometry_and_skin":True,
      "body_topology_acceptance":"UNKNOWN"}
    payload=glb_pack(d,b)
    Path(out).parent.mkdir(parents=True,exist_ok=True)
    Path(out).write_bytes(payload)
    result={
       "schema":"scp.r009.original_wardrobe_preset_receipt.v1",
       "source_sha256":hashlib.sha256(raw).hexdigest(),
       "derived_sha256":hashlib.sha256(payload).hexdigest(),
       "presets":dict(presets),"active_layers":status,
       "joints_each":35,"source_geometry_preserved":True,
       "human_appearance_accepted":False}
    Path(receipt).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--receipt",required=True)
    p.add_argument("--aster",choices=sorted(PRESETS),default="signature")
    p.add_argument("--juniper",choices=sorted(PRESETS),default="signature")
    a=p.parse_args()
    print(json.dumps(export(a.input,a.manifest,a.out,a.receipt,
        {"AsterOriginal":a.aster,"JuniperOriginal":a.juniper}),sort_keys=True))
