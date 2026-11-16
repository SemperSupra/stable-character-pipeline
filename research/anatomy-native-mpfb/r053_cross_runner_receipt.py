"""R053 bounded source-safe independent-runner GLB hash receipt.

Only hashes and bounded structural counts go to GitHub public logs.
No source GLB/BLEND or anatomical mesh bytes are uploaded.
"""
import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from r052_glb_diff import inspect_glb
from r051_glb_repeatability import fingerprint

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--glb",required=True)
    p.add_argument("--blend",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--rep",choices=["a","b"],required=True)
    args=p.parse_args()
    glb,_=inspect_glb(args.glb)
    body=fingerprint(args.glb)
    if body["source_vertices"]!=14517 or body["morph_channels"]!=8:
        raise ValueError("R053_HOLD actual original-synthetic source geometry changed")
    if body["whole_sha256"]!=glb["whole_sha256"]:
        raise ValueError("R053_HOLD independent whole-file SHA disagreement")
    result={
        "schema":"r053.mpfb.cross-runner-chunk-receipt.v1",
        "status":"PASS_NARROW_INDEPENDENT_RUNNER_SHA_RECEIPT",
        "rep":args.rep,
        "commit_sha":os.environ.get("GITHUB_SHA","LOCAL_NOT_CI"),
        "runner_image":os.environ.get("ImageOS","UNKNOWN"),
        "runner_image_version":os.environ.get("ImageVersion","UNKNOWN"),
        "python_version":platform.python_version(),
        "platform":platform.system()+"-"+platform.machine(),
        "upstream_mpfb_sha":"9de0707fdc88438d7c53a1a2ac7937d9221e2431",
        "source_blend_sha256":sha(args.blend),
        "whole_glb_sha256":glb["whole_sha256"],
        "gltf_json_canonical_sha256":glb["json_canonical_sha256"],
        "gltf_json_chunk_sha256":glb["json_chunk_sha256"],
        "gltf_binary_chunk_sha256":glb["binary_chunk_sha256"],
        "gltf_binary_bytes":glb["binary_chunk_bytes"],
        "body_position_eight_morph_sha256":body["source_body_positions_and_8_morphs_sha256"],
        "body_vertices":body["source_vertices"],
        "morph_channels":body["morph_channels"],
        "source_gltf_parts":body["parts"],
        "limits":"Only same-commit original-synthetic source in separate public runner jobs; no binary exchange, exact host image pin, full model equivalence, anatomical truth, posed skin, character identity or release",
    }
    Path(args.out).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("R053_CROSS_RUNNER_RECEIPT "+json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
