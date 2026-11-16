"""R051 original-synthetic two-export glTF repeatability probe (stdlib).

Never silently equates unchanged GPU morph deltas with identical model bytes.
Only compares one source body primitive POSITION + eight source morph arrays.
"""
import argparse
import hashlib
import json
import os
import struct
from pathlib import Path
from gltf_godot_morph_compare import parse_glb, expected_morph_arrays

def hold(message):
    raise RuntimeError("R051_GLTF_REPRO_HOLD "+message)

def filehash(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1048576),b""):
            h.update(b)
    return h.hexdigest()

def fingerprint(path):
    base,targets=expected_morph_arrays(path)
    if len(base)<13000 or len(targets)!=8:
        hold("malformed actual source MPFB semantic geometry")
    h=hashlib.sha256()
    h.update(struct.pack("<II",len(base),len(targets)))
    for a in [base]+targets:
        if len(a)!=len(base):hold("mismatched actual morph buffer lengths")
        for vec in a:
            h.update(struct.pack("<fff",*vec))
    manifest,raw=parse_glb(path)
    # A byte-different GLB can have equivalent source geometry yet different
    # object/mesh order, animation JSON, metadata, material or other attributes.
    mesh=list(manifest.get("meshes",[]))
    if not mesh:hold("source GLB has no meshes")
    keyset={
        "gltf_meshes":len(mesh),
        "gltf_nodes":len(manifest.get("nodes",[])),
        "gltf_accessors":len(manifest.get("accessors",[])),
        "gltf_animations":len(manifest.get("animations",[])),
        "gltf_materials":len(manifest.get("materials",[])),
        "gltf_buffer_views":len(manifest.get("bufferViews",[])),
        "gltf_binary_bytes":len(raw),
    }
    normalized=json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("utf-8")
    return {"whole_sha256":filehash(path),
        "source_body_positions_and_8_morphs_sha256":h.hexdigest(),
        "gltf_json_sha256":hashlib.sha256(normalized).hexdigest(),
        "source_vertices":len(base), "morph_channels":len(targets),
        "parts":keyset}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--first",required=True)
    p.add_argument("--second",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    a=fingerprint(args.first)
    b=fingerprint(args.second)
    # Deliberate semantic negative control (no source/protected byte mutation).
    sample=hashlib.sha256(bytes.fromhex(a["source_body_positions_and_8_morphs_sha256"])+b"\0").hexdigest()
    if sample==a["source_body_positions_and_8_morphs_sha256"]:
        hold("semantic hasher corruption negative accidentally passed")
    eq=a["source_body_positions_and_8_morphs_sha256"]==b["source_body_positions_and_8_morphs_sha256"]
    result={
        "schema":"r051.glb.body-semantic-repeatability.v1",
        "status":"PASS_NARROW_BODY_SOURCE_SEMANTIC_REPEATABILITY" if eq else "HOLD_SOURCE_MORPH_OR_POSITION_CHANGED",
        "first":a,"second":b,
        "body_position_and_eight_morphs_semantically_identical":eq,
        "whole_glb_byte_identical":a["whole_sha256"]==b["whole_sha256"],
        "gltf_json_byte_identical_after_key_sort":a["gltf_json_sha256"]==b["gltf_json_sha256"],
        "different_full_glb_but_same_body_semantics":a["whole_sha256"]!=b["whole_sha256"] and eq,
        "limits":"Only one original-synthetic body POSITION/eight morph attributes; says nothing about full animation, skin weights, normals, UV, tangent, materials or VFX/game product identity"}
    Path(args.out).write_text(json.dumps(result,sort_keys=True,indent=2),encoding="utf-8")
    print("R051_GLB_REPEATABILITY_RECEIPT "+json.dumps(result,sort_keys=True))
    if not eq:hold("actual source GLB body/morph semantics differed across two independent exports")
if __name__=="__main__":main()
