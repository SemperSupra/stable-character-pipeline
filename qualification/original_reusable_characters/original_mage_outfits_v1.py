#!/usr/bin/env python3
"""Original mage-adventure garment cuts, two actors, separable 35-joint GLB skins.

Costume silhouettes are newly authored in geometry code. Fairy Tail characters
are conceptual costume references only; no downloaded costume geometry, series
graphics, UV sheets, trademarks, or textures are imported. Static cloth is an
experimental base mesh, not a physical-cloth/collision acceptance claim.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

import humanization_v2 as h
from modular_wardrobe_v1 import ACTORS, PRESETS
from parametric_morphology_v1 import DEFAULT, deform, transformed_normal
from rig35_v2 import glb_pack
from verify_original_glb import accessory, decode

SCHEMA = "scp.r009.original_mage_outfits.v1"
ADVENTURE = ("body", "hair", "style_top", "style_bottom", "footwear", "accessory")
VALID_PRESETS = {**PRESETS, "adventure": ADVENTURE}
PALETTE = {
    "AsterOriginal": {
        "style_top": (.115, .175, .275, 1.),
        "style_trim": (.69, .48, .20, 1.),
        "style_bottom": (.29, .32, .38, 1.),
    },
    "JuniperOriginal": {
        "style_top": (.43, .19, .36, 1.),
        "style_trim": (.77, .62, .43, 1.),
        "style_bottom": (.27, .18, .39, 1.),
    },
}

def torso_weights(y):
    if y < 1.11:
        return ("pelvis", "spine", max(0., min(1., (1.11-y)/.20)))
    return ("spine", "chest", max(0., min(1., (1.38-y)/.27)))

def geometry(actor):
    """Independent topology: sleeveless vest + cropped pants or shaped top + skirt."""
    g = h.v1.Geometry()
    if actor == "AsterOriginal":
        # No sleeves: forearms, shoulder joints and collar remain visible.
        h.loft_anatomy(g, "style_top", [
            (1.030, 0., .168, .143), (1.130, 0., .184, .158),
            (1.235, 0., .209, .185), (1.325, 0., .210, .168),
            (1.385, 0., .173, .131), (1.421, 0., .108, .090)
        ], torso_weights, 36)
        # Separate trim/standing collar, same rig as vest; not a pasted emblem.
        h.loft_anatomy(g, "style_trim", [
            (1.394, 0., .133, .099), (1.410, 0., .120, .095),
            (1.430, 0., .095, .086)
        ], torso_weights, 36)
        h.loft_anatomy(g, "style_bottom", [
            (.680, 0., .146, .122), (.800, 0., .212, .157),
            (.900, 0., .223, .169), (1.010, 0., .179, .147)
        ], torso_weights, 36)
        for sign, side in ((-1, "L"), (1, "R")):
            hip = h.v1.POS["hip_"+side]
            knee = h.v1.POS["knee_"+side]
            # Distinct loose knee-cropped pant cut and hem.
            g.tube("style_bottom", hip, knee, .136, .105,
                   "hip_"+side, "knee_"+side, steps=16, sides=24)
            hem = (sign*.140, .350, 0.)
            g.tube("style_bottom", knee, hem, .107, .115,
                   "knee_"+side, "ankle_"+side, steps=8, sides=24)
    else:
        # Fitted long-sleeveless bodice: independent from original teal jacket.
        h.loft_anatomy(g, "style_top", [
            (1.016, 0., .168, .132), (1.095, 0., .157, .136),
            (1.190, 0., .181, .157), (1.266, 0., .202, .185),
            (1.342, 0., .181, .149), (1.415, 0., .086, .077)
        ], torso_weights, 36)
        h.loft_anatomy(g, "style_trim", [
            (1.025, 0., .175, .141), (1.044, 0., .171, .144),
            (1.059, 0., .169, .145)
        ], torso_weights, 36)
        # Separate flared skirt, lower hem intentionally wider than the hips.
        h.loft_anatomy(g, "style_bottom", [
            (.560, 0., .292, .224), (.635, 0., .272, .213),
            (.755, 0., .235, .182), (.857, 0., .222, .169),
            (.940, 0., .212, .159), (1.035, 0., .172, .145)
        ], torso_weights, 48)
    return g

def accessor_add(doc, bb, values, fmt, typ, components, target, extrema=False):
    if len(values) % components: raise ValueError("NEW_GARMENT_ACCESSOR_COUNT")
    while len(bb) % 4: bb.append(0)
    off = len(bb)
    if fmt == "f":
        if not all(math.isfinite(x) for x in values):
            raise ValueError("NEW_GARMENT_NONFINITE")
    bb.extend(struct.pack("<"+fmt*len(values), *values))
    view = len(doc["bufferViews"])
    doc["bufferViews"].append({
        "buffer": 0, "byteOffset": off,
        "byteLength": len(values) * struct.calcsize(fmt), "target": target
    })
    a = {"bufferView": view, "componentType": {"f":5126, "B":5121, "I":5125}[fmt],
         "type":typ, "count":len(values)//components}
    if extrema:
        a["min"] = [min(values[k::components]) for k in range(components)]
        a["max"] = [max(values[k::components]) for k in range(components)]
    index = len(doc["accessors"])
    doc["accessors"].append(a)
    return index

def add_original_outfits(src, src_manifest, out, out_manifest, receipt):
    paths = [Path(v).resolve() for v in (src, src_manifest, out, out_manifest, receipt)]
    if len(set(paths)) != 5: raise ValueError("OUTFIT_SOURCE_OVERWRITE")
    raw = Path(src).read_bytes()
    manifest = json.loads(Path(src_manifest).read_text())
    if manifest.get("schema") != "scp.original_wardrobe_manifest.v1" or (
            manifest.get("derived_sha256") != hashlib.sha256(raw).hexdigest()):
        raise ValueError("OUTFIT_SOURCE_MANIFEST_SHA")
    doc, binary = decode(raw)
    if doc.get("extras", {}).get("source_class") != "ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("OUTFIT_NOT_ORIGINAL_SOURCE")
    if doc.get("extras", {}).get("parametric_morphology", {}).get("schema") != (
            "scp.r009.morphology_profile.v1"):
        raise ValueError("OUTFIT_REQUIRES_MORPH_PROFILE")
    if len(doc["skins"]) != 2 or any(len(s["joints"]) != 35 for s in doc["skins"]):
        raise ValueError("OUTFIT_35_JOINT_SKIN")
    bb = bytearray(binary)
    names = {node["name"]: i for i, node in enumerate(doc["nodes"])}
    profiles = doc["extras"]["parametric_morphology"]["profiles"]
    counts = {}
    for actor_i, actor in enumerate(ACTORS):
        g = geometry(actor)
        mats = {}
        for material, rgba in PALETTE[actor].items():
            idx = len(doc["materials"])
            doc["materials"].append({
                "name": actor+"_"+material+"_ORIGINAL_CUT",
                "pbrMetallicRoughness": {
                    "baseColorFactor": list(rgba),
                    "metallicFactor": 0., "roughnessFactor": .90},
                "doubleSided": True
            })
            mats[material] = idx
        grouped = {"style_top": [], "style_bottom": []}
        counts[actor] = {}
        for material, part in g.parts.items():
            slot = "style_bottom" if material == "style_bottom" else "style_top"
            positions0 = [tuple(part["p"][i:i+3]) for i in range(0, len(part["p"]), 3)]
            normals0 = [tuple(part["n"][i:i+3]) for i in range(0, len(part["n"]), 3)]
            alias = "bottom" if slot == "style_bottom" else "top"
            transformed = [deform(x, alias, profiles[actor]) for x in positions0]
            normals = [transformed_normal(x, n, alias, profiles[actor])
                       for x,n in zip(positions0, normals0)]
            if not (len(transformed) == len(normals) and part["i"]):
                raise ValueError("OUTFIT_EMPTY_GEOMETRY")
            a = {
                "POSITION": accessor_add(doc, bb, [v for row in transformed for v in row],
                                         "f", "VEC3", 3, 34962, extrema=True),
                "NORMAL": accessor_add(doc, bb, [v for row in normals for v in row],
                                       "f", "VEC3", 3, 34962),
                "JOINTS_0": accessor_add(doc, bb, part["j"], "B", "VEC4", 4, 34962),
                "WEIGHTS_0": accessor_add(doc, bb, part["w"], "f", "VEC4", 4, 34962)
            }
            inds = accessor_add(doc, bb, part["i"], "I", "SCALAR", 1, 34963)
            grouped[slot].append({
                "attributes": a, "indices": inds, "material": mats[material]
            })
            counts[actor][material] = len(transformed)
        root = doc["nodes"][names[actor+"_SceneRoot"]]
        for slot, prims in grouped.items():
            if not prims: raise ValueError("OUTFIT_SLOT_EMPTY")
            mesh_id = len(doc["meshes"])
            doc["meshes"].append({"name": actor+"_"+slot+"_NEW_CUT", "primitives": prims})
            node_id = len(doc["nodes"])
            doc["nodes"].append({
                "name": actor+"_Wardrobe_"+slot,
                "mesh":mesh_id, "skin":actor_i,
                "extras":{"wardrobe_slot":slot, "actor":actor,
                          "original_geometry":True, "cloth_sim_accepted":False}
            })
            root.setdefault("children", []).append(node_id)
            manifest["actor_slots"][actor][slot] = {
                "node":node_id, "mesh":mesh_id, "skin":actor_i,
                "material_ids": sorted({x["material"] for x in prims}),
            }
    manifest["new_cut_parent_sha256"] = hashlib.sha256(raw).hexdigest()
    manifest["presets"] = {k:list(v) for k,v in VALID_PRESETS.items()}
    manifest["separate_new_geometry_for_adventure"] = True
    manifest["cloth_sim_accepted"] = False
    manifest["appearance_accepted"] = False
    doc["extras"]["original_mage_outfits"] = {
        "schema": SCHEMA, "original_new_cut":True,
        "preset":"adventure", "new_garment_slots":["style_top","style_bottom"],
        "physical_cloth_accepted":False, "visual_fit_accepted":False
    }
    payload = glb_pack(doc, bb)
    manifest["derived_sha256"] = hashlib.sha256(payload).hexdigest()
    result = {
        "schema": "scp.r009.original_mage_outfits_receipt.v1",
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "derived_sha256":hashlib.sha256(payload).hexdigest(),
        "garment_vertex_counts":counts, "joints_each":35,
        "original_new_geometry":True, "human_visual_accepted":False,
        "garment_collision_accepted":False
    }
    for path, data in (
            (out,payload),
            (out_manifest,(json.dumps(manifest, sort_keys=True, indent=2)+"\n").encode()),
            (receipt,(json.dumps(result, sort_keys=True, indent=2)+"\n").encode())):
        p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    return result

def export_adventure(src, manifest_path, out, receipt, presets):
    paths = [Path(p).resolve() for p in (src,manifest_path,out,receipt)]
    if len(set(paths)) != 4:raise ValueError("ADVENTURE_SOURCE_OVERWRITE")
    if set(presets) != set(ACTORS) or any(x not in VALID_PRESETS for x in presets.values()):
        raise ValueError("ADVENTURE_UNKNOWN_PRESET")
    raw = Path(src).read_bytes()
    m = json.loads(Path(manifest_path).read_text())
    if m.get("derived_sha256") != hashlib.sha256(raw).hexdigest() or (
            "adventure" not in m.get("presets",{})):
        raise ValueError("ADVENTURE_MANIFEST_SHA")
    d,b = decode(raw)
    if d.get("extras",{}).get("original_mage_outfits",{}).get("schema") != SCHEMA:
        raise ValueError("ADVENTURE_NOT_OWNED_GARMENT")
    names={n["name"]:i for i,n in enumerate(d["nodes"])}
    status={}
    for actor in ACTORS:
        root=d["nodes"][names[actor+"_SceneRoot"]]
        wanted=set(VALID_PRESETS[presets[actor]])
        for slot,meta in m["actor_slots"][actor].items():
            node=meta["node"]
            if slot in wanted and node not in root["children"]:
                root["children"].append(node)
            elif slot not in wanted and node in root["children"]:
                root["children"].remove(node)
        active=sorted(slot for slot,meta in m["actor_slots"][actor].items()
                      if meta["node"] in root["children"])
        if set(active) != wanted.intersection(m["actor_slots"][actor]):
            raise ValueError("ADVENTURE_VISIBLE_LAYER_MISMATCH")
        if not {"body","hair"}.issubset(active):
            raise ValueError("ADVENTURE_BODY_GROOM_MISSING")
        status[actor]=active
    d["extras"]["wardrobe_preset_state"] = {
        "schema":"scp.r009.original_mage_portable.v1",
        "actor_presets":dict(presets), "active_layers":status,
        "geometry_unchanged_from_authoring_source":True
    }
    output=glb_pack(d,b)
    result={
        "source_sha256":hashlib.sha256(raw).hexdigest(),
        "derived_sha256":hashlib.sha256(output).hexdigest(),
        "preset_selection":dict(presets), "active_layers":status,
        "human_visual_accepted":False
    }
    Path(out).write_bytes(output)
    Path(receipt).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    return result

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--out-manifest",required=True)
    p.add_argument("--receipt",required=True)
    args=p.parse_args()
    print(json.dumps(add_original_outfits(args.input,args.manifest,args.out,
                                          args.out_manifest,args.receipt),sort_keys=True))
