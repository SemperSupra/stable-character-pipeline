"""R052 bounded source-safe forensic comparison of two independently exported GLBs.

Classifies packaging drift without pretending that an equal body morph fingerprint
establishes equality of skins, animation, materials, other meshes or visual output.
Works with original synthetic GLBs; never uploads their binary bytes.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from gltf_godot_morph_compare import parse_glb

def digest(data):
    return hashlib.sha256(data).hexdigest()

def inspect_glb(path):
    raw=Path(path).read_bytes()
    manifest, binary=parse_glb(path)  # strict length, version, two-chunk oracle
    json_len,json_kind=struct.unpack_from("<II",raw,12)
    if json_kind!=0x4e4f534a:
        raise ValueError("R052_GLTF_HOLD wrong JSON chunk type")
    text=raw[20:20+json_len]
    if len(text)!=json_len:
        raise ValueError("R052_GLTF_HOLD truncated JSON")
    canonical=json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    return {
        "whole_sha256":digest(raw),
        "whole_bytes":len(raw),
        "json_chunk_sha256":digest(text),
        "json_canonical_sha256":digest(canonical),
        "json_chunk_bytes":len(text),
        "binary_chunk_sha256":digest(binary),
        "binary_chunk_bytes":len(binary),
    },manifest

def changed_paths(a,b,prefix="$",limit=32):
    """Path-only differences; never include raw model values in public receipts."""
    changes=[]
    def walk(x,y,path):
        if len(changes)>=limit:
            return
        if type(x) is not type(y):
            changes.append(path+":type");return
        if isinstance(x,dict):
            for key in sorted(set(x)|set(y)):
                if len(changes)>=limit:return
                p=path+"."+key
                if key not in x or key not in y:changes.append(p+":membership")
                else:walk(x[key],y[key],p)
        elif isinstance(x,list):
            if len(x)!=len(y):changes.append(path+":length")
            for i in range(min(len(x),len(y))):
                if len(changes)>=limit:return
                walk(x[i],y[i],path+"["+str(i)+"]")
        elif x!=y:changes.append(path)
    walk(a,b,prefix)
    return changes

def compare(first,second,require_body=False):
    a,ja=inspect_glb(first)
    b,jb=inspect_glb(second)
    json_changed=a["json_canonical_sha256"]!=b["json_canonical_sha256"]
    bin_changed=a["binary_chunk_sha256"]!=b["binary_chunk_sha256"]
    bytes_changed=a["whole_sha256"]!=b["whole_sha256"]
    if not bytes_changed:kind="BYTE_IDENTICAL"
    elif json_changed and bin_changed:kind="JSON_AND_BINARY_SEMANTIC_DRIFT"
    elif json_changed:kind="JSON_SEMANTIC_DRIFT"
    elif bin_changed:kind="BINARY_PAYLOAD_DRIFT"
    else:kind="SERIALIZATION_OR_PADDING_ONLY_DRIFT"
    result={
        "schema":"r052.gltf.packaging-forensics.v1",
        "status":"PASS_NARROW_PACKAGING_CLASSIFIED",
        "classification":kind,
        "first":a,
        "second":b,
        "canonical_json_changed":json_changed,
        "binary_chunk_changed":bin_changed,
        "whole_file_changed":bytes_changed,
        "json_changed_paths_limited":changed_paths(ja,jb),
        "body_geometry_checked":False,
        "limits":"Only 2-chunk GLB packaging and optional original-synthetic MPFB body POSITION/8 morph comparison. No full skin/UV/animation equivalence, engine, human/visual or release acceptance",
    }
    if require_body:
        from r051_glb_repeatability import fingerprint
        s1=fingerprint(first)
        s2=fingerprint(second)
        same=(s1["source_body_positions_and_8_morphs_sha256"]==
              s2["source_body_positions_and_8_morphs_sha256"])
        result["body_geometry_checked"]=True
        result["source_body_and_eight_morphs_identical"]=same
        result["source_body_morph_sha256_first"]=s1["source_body_positions_and_8_morphs_sha256"]
        result["source_body_morph_sha256_second"]=s2["source_body_positions_and_8_morphs_sha256"]
        if not same:result["status"]="HOLD_SOURCE_BODY_MORPH_CHANGED"
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--first",required=True)
    p.add_argument("--second",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--require-body",action="store_true")
    args=p.parse_args()
    report=compare(args.first,args.second,args.require_body)
    Path(args.out).write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("R052_GLTF_FORENSICS "+json.dumps(report,sort_keys=True))
    if report["status"].startswith("HOLD_"):
        raise SystemExit(12)

if __name__=="__main__":main()
