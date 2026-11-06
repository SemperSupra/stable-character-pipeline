#!/usr/bin/env python3
"""Non-destructive A5 portable viewer export; original wardrobe library retained.

The v1 exporter detaches inactive layers from scene roots, but leaves their
nodes as mesh-bearing orphans. Blender imports those orphans as garment meshes.
V2 removes the 'mesh' and 'skin' bindings from INACTIVE PORTABLE NODES, not the
original immutable authoring library. All original mesh payloads, armatures,
animations and skin joint arrays remain available in the derived GLB.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from modular_wardrobe_v1 import ACTORS,PRESETS
from rig35_v2 import glb_pack
from verify_original_glb import decode
from wardrobe_export_preset import export as export_v1

SCHEMA="scp.r009.original_wardrobe_portable_export.v2"

def export(source,manifest,out,receipt,presets):
    source,manifest,out,receipt=map(lambda p:Path(p).resolve(),
                                    (source,manifest,out,receipt))
    if len({source,manifest,out,receipt})!=4:
        raise ValueError("SOURCE_OR_RECEIPT_OVERWRITE_REFUSED")
    if not source.is_file() or not manifest.is_file():
        raise ValueError("SOURCE_OR_MANIFEST_MISSING")
    if out.exists() or receipt.exists():
        raise FileExistsError("REFUSE_OVERWRITE_EXISTING_PORTABLE_OUTPUT")
    if set(presets)!=set(ACTORS) or any(p not in PRESETS for p in presets.values()):
        raise ValueError("UNKNOWN_ACTOR_OR_PRESET")
    master=source.read_bytes()
    master_sha=hashlib.sha256(master).hexdigest()
    manifest_doc=json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_doc.get("derived_sha256")!=master_sha:
        raise ValueError("SOURCE_MANIFEST_SHA_MISMATCH")
    with TemporaryDirectory() as td:
        root=Path(td)
        intermediate=root/"v1_scene.glb"
        v1_receipt=root/"v1_receipt.json"
        original_receipt=export_v1(source,manifest,intermediate,v1_receipt,presets)
        doc,binary=decode(intermediate.read_bytes())
    before_doc,_=decode(master)
    if doc.get("animations")!=before_doc.get("animations"):
        raise ValueError("SOURCE_ANIMATION_CHANGED")
    if doc.get("skins")!=before_doc.get("skins"):
        raise ValueError("SOURCE_SKINS_CHANGED")
    if doc.get("meshes")!=before_doc.get("meshes"):
        raise ValueError("SOURCE_MESH_LIBRARY_CHANGED")
    inactive={}
    for actor in ACTORS:
        wanted=set(PRESETS[presets[actor]])
        slots=manifest_doc["actor_slots"][actor]
        root_name=actor+"_SceneRoot"
        names={n.get("name"):i for i,n in enumerate(doc["nodes"])}
        if root_name not in names:
            raise ValueError("ACTOR_SCENE_ROOT_MISSING")
        children=set(doc["nodes"][names[root_name]].get("children",[]))
        removed=[]
        for slot,entry in slots.items():
            idx=entry["node"]
            node=doc["nodes"][idx]
            if not node.get("name","").startswith(actor+"_Wardrobe_"):
                raise ValueError("SOURCE_NODE_PROVENANCE_MISMATCH:"+actor+":"+slot)
            active=slot in wanted
            if active:
                if idx not in children or "mesh" not in node:
                    raise ValueError("ACTIVE_PRESET_MESH_MISSING:"+slot)
            else:
                if idx in children:
                    raise ValueError("INACTIVE_SCENE_CHILD_STILL_REACHABLE:"+slot)
                if "mesh" not in node:
                    raise ValueError("INACTIVE_SOURCE_MESH_ALREADY_MISSING:"+slot)
                node.pop("mesh")
                node.pop("skin",None)
                removed.append(slot)
        inactive[actor]=sorted(removed)
    doc.setdefault("extras",{})["portable_export_v2"]={
        "schema":SCHEMA,"active_layers":original_receipt["active_layers"],
        "detached_inactive_mesh_bindings":inactive,
        "untouched_authoring_sha256":master_sha,
        "source_mesh_library_retained":True,
        "native_blender_import_acceptance":"UNKNOWN_UNTIL_INDEPENDENT_A5",
        "human_visual_acceptance":False}
    payload=glb_pack(doc,binary)
    receipt_body={
       **original_receipt,"derived_sha256":hashlib.sha256(payload).hexdigest(),
       "schema":"scp.r009.original_wardrobe_preset_receipt.v1",
       "portable_export_contract":SCHEMA,
       "inactive_mesh_bindings_removed":inactive,
       "source_geometry_preserved":True,
       "native_blender_import_acceptance":"UNKNOWN_UNTIL_INDEPENDENT_A5",
       "human_appearance_accepted":False,"release_approved":False}
    # Refuse overwrites prior to any write; preserve source and first-failure
    # snapshots and leave no intermediate files in the repo.
    out.parent.mkdir(parents=True,exist_ok=True)
    receipt.parent.mkdir(parents=True,exist_ok=True)
    if out.exists() or receipt.exists():
        raise FileExistsError("REFUSE_OVERWRITE_EXISTING_PORTABLE_OUTPUT")
    with out.open("xb") as f:f.write(payload)
    with receipt.open("x",encoding="utf-8") as f:
        f.write(json.dumps(receipt_body,indent=2,sort_keys=True)+"\n")
    if hashlib.sha256(source.read_bytes()).hexdigest()!=master_sha:
        raise ValueError("ORIGINAL_AUTHORING_SOURCE_CHANGED")
    return receipt_body
