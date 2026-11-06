#!/usr/bin/env python3
"""Strict, source-preserving Blender-compatible portable exporter for original R009 mage wardrobes.

The wardrobe v1 scene-root-only switch leaves unreferenced mesh-bearing nodes.
Blender imports those orphan meshes; actual wardrobe_v2 owner PR #303 already
identified this first RED. This consumer-specific adapter implements the same
fail-closed principle for *new adventure cuts* without modifying upstream source.
"""
import argparse
import hashlib
import json
from pathlib import Path

from modular_wardrobe_v1 import ACTORS
from original_mage_outfits_v1 import SCHEMA as MAGE_SCHEMA
from original_mage_outfits_v1 import VALID_PRESETS
from rig35_v2 import glb_pack
from verify_original_glb import decode

SCHEMA = "scp.r009.strict_mage_portable.v1"


def export(source, manifest, out, receipt, choices):
    src, meta, target, receipt_path = (Path(p).resolve() for p in (
        source, manifest, out, receipt))
    if len({src, meta, target, receipt_path}) != 4:
        raise ValueError("STRICT_SOURCE_OR_RECEIPT_OVERWRITE")
    if target.exists() or receipt_path.exists():
        raise FileExistsError("STRICT_REFUSE_OVERWRITE")
    if set(choices) != set(ACTORS) or any(p not in VALID_PRESETS
                                          for p in choices.values()):
        raise ValueError("STRICT_UNKNOWN_ACTOR_OR_PRESET")
    raw = src.read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()
    m = json.loads(meta.read_text(encoding="utf8"))
    if m.get("derived_sha256") != source_sha or m.get("schema") != (
            "scp.original_wardrobe_manifest.v1"):
        raise ValueError("STRICT_SOURCE_MANIFEST_SHA")
    doc, binary = decode(raw)
    if doc.get("extras", {}).get("source_class") != "ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("STRICT_NOT_ORIGINAL_SOURCE")
    if doc.get("extras", {}).get("original_mage_outfits", {}).get("schema") != MAGE_SCHEMA:
        raise ValueError("STRICT_MISSING_MAGE_SOURCE")
    if doc.get("extras", {}).get("parametric_morphology", {}).get("schema") != (
            "scp.r009.morphology_profile.v1"):
        raise ValueError("STRICT_MISSING_MORPH")
    if len(doc.get("skins", [])) != 2 or any(len(s["joints"]) != 35
                                            for s in doc["skins"]):
        raise ValueError("STRICT_INVALID_RIG")
    # Work only on the decoded in-memory derivative document. The original
    # authoring GLB has all mesh-bearing nodes and 35-joint skin entries intact.
    names = {n.get("name"): i for i, n in enumerate(doc["nodes"])}
    retained, removed = {}, {}
    for actor_i, actor in enumerate(ACTORS):
        root_name = actor + "_SceneRoot"
        if root_name not in names:
            raise ValueError("STRICT_SCENE_ROOT_MISSING")
        root = doc["nodes"][names[root_name]]
        children = root.get("children")
        if not isinstance(children, list) or len(children) != len(set(children)):
            raise ValueError("STRICT_SCENE_ROOT_INVALID")
        slots = m["actor_slots"][actor]
        wanted = set(VALID_PRESETS[choices[actor]])
        if not {"body", "hair"}.issubset(wanted):
            raise ValueError("STRICT_MISSING_BODY")
        if not wanted.issubset(slots):
            # E.g. Juniper has no optional scarf/accessory. Allowed optional
            # absence is explicit; presence of mandatory slots remains checked.
            if wanted - set(slots) != {"accessory"}:
                raise ValueError("STRICT_MISSING_REQUIRED_SLOT")
        still, missing = [], []
        for slot, entry in slots.items():
            index = entry["node"]
            node = doc["nodes"][index]
            if node.get("name") != actor + "_Wardrobe_" + slot or (
                    entry["skin"] != actor_i or entry["mesh"] != node.get("mesh")
                    or node.get("skin") != actor_i):
                raise ValueError("STRICT_SLOT_SOURCE_MISMATCH:" + actor + ":" + slot)
            if slot in wanted:
                if index not in children: children.append(index)
                still.append(slot)
            else:
                if index in children: children.remove(index)
                node.pop("mesh")
                node.pop("skin")
                missing.append(slot)
        expected = set(wanted).intersection(slots)
        if set(still) != expected:
            raise ValueError("STRICT_VISIBLE_LAYERS_UNEXPECTED")
        retained[actor] = sorted(still)
        removed[actor] = sorted(missing)
    # Confirm we left the entire mesh/skin/animation payload untouched.
    doc["extras"]["strict_mage_portable"] = {
        "schema": SCHEMA, "source_sha256": source_sha,
        "choices": dict(choices), "active_layers": retained,
        "inactive_mesh_skin_binding_removed": removed,
        "mesh_library_preserved": True, "visual_accepted": False,
        "blender_import_accepted": False,
    }
    payload = glb_pack(doc, binary)
    result = {
        "schema": SCHEMA + ".receipt",
        "source_sha256": source_sha,
        "derived_sha256": hashlib.sha256(payload).hexdigest(),
        "active_layers": retained, "inactive_layers": removed,
        "choices": dict(choices), "source_mesh_library_preserved": True,
        "joints_each": 35, "visual_accepted": False,
        "blender_import_accepted": False,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or receipt_path.exists():
        raise FileExistsError("STRICT_REFUSE_OVERWRITE")
    # Source remains immutable; artifacts refuse overwrite to prevent stale
    # proof laundering. On a failed second write, partial derivative only.
    with target.open("xb") as f: f.write(payload)
    with receipt_path.open("x", encoding="utf8") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if hashlib.sha256(src.read_bytes()).hexdigest() != source_sha:
        raise ValueError("STRICT_SOURCE_CHANGED")
    return result


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt", required=True)
    ap.add_argument("--aster", choices=sorted(VALID_PRESETS), default="adventure")
    ap.add_argument("--juniper", choices=sorted(VALID_PRESETS), default="adventure")
    a=ap.parse_args()
    print(json.dumps(export(a.input, a.manifest, a.out, a.receipt,
                            {"AsterOriginal":a.aster,
                             "JuniperOriginal":a.juniper}), sort_keys=True))
