"""ROM-FMT A: verifiable source-authored glTF/GLB node metadata, not rig enforcement.

Only test-source contract. Format-agnostic canonical manifest is authority; glTF
node extras are derived. No authored human/animal limits. No external packages.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

MAX=8*1024*1024
TAG="scp_rom_v1"
SCHEMA="scp.rom.joint_annotation.v1"
MAGIC=b"glTF"
JSON_CHUNK=0x4e4f534a


def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False,ensure_ascii=False).encode("utf-8")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def validate_manifest(m):
    if not isinstance(m,dict) or m.get("schema")!=SCHEMA or m.get("rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or m.get("authority")!="SYNTHETIC_TEST_ONLY":
        raise ValueError("AUTHORITY_RIGHTS_OR_SCHEMA")
    if not isinstance(m.get("rig_id"),str) or not m["rig_id"]:
        raise ValueError("RIG_ID")
    joints=m.get("joints")
    if not isinstance(joints,list) or not joints or len(joints)>64:
        raise ValueError("JOINT_COVERAGE")
    seen=set()
    for j in joints:
        if not isinstance(j,dict) or set(j)!={"id","node","parent","kind","axis","unit","frame","hard_min","hard_max","provenance"}:
            raise ValueError("JOINT_FIELDS")
        if (not isinstance(j["id"],str) or not j["id"] or j["id"] in seen or
            not isinstance(j["node"],str) or not j["node"] or
            not isinstance(j["parent"],str) or
            j["kind"] not in ("revolute","prismatic") or
            j["unit"]!=("rad" if j["kind"]=="revolute" else "m") or
            j["frame"]!="PARENT_LOCAL_TEST_ONLY" or j["provenance"]!="SYNTHETIC_TEST_ONLY"):
            raise ValueError("JOINT_ID_COORDINATE_PROVENANCE")
        seen.add(j["id"])
        if not isinstance(j["axis"],list) or len(j["axis"])!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in j["axis"]):
            raise ValueError("AXIS_SHAPE")
        if abs(sum(v*v for v in j["axis"])-1)>1e-6:
            raise ValueError("AXIS_UNIT_LENGTH")
        if any(type(j[k]) not in (int,float) or not math.isfinite(j[k]) for k in ("hard_min","hard_max")) or j["hard_min"]>=j["hard_max"]:
            raise ValueError("HARD_ROM")
    if len({j["node"] for j in joints})!=len(joints):
        raise ValueError("NODE_MAPPING_DUPLICATE")
    return m


def annotation(j,authority_hash):
    return {"schema":SCHEMA,"joint_id":j["id"],"kind":j["kind"],
            "axis":j["axis"],"unit":j["unit"],"frame":j["frame"],
            "hard_min":j["hard_min"],"hard_max":j["hard_max"],
            "manifest_sha256":authority_hash,"authority":"SYNTHETIC_TEST_ONLY"}


def add_extras(asset,manifest):
    validate_manifest(manifest)
    if asset.get("asset",{}).get("version")!="2.0":
        raise ValueError("GLTF_V2_ONLY")
    nodes=asset.get("nodes")
    if not isinstance(nodes,list) or len(nodes)>512:
        raise ValueError("NODE_COUNT")
    skin_nodes=set()
    for skin in asset.get("skins",[]):
        skin_nodes.update(skin.get("joints",[]))
    if not skin_nodes:
        raise ValueError("SKIN_JOINTS_REQUIRED")
    by_name={}
    for i,node in enumerate(nodes):
        if not isinstance(node,dict) or not isinstance(node.get("name"),str):
            continue
        by_name.setdefault(node["name"],[]).append(i)
    hash_value=digest(canonical(manifest))
    for j in manifest["joints"]:
        indexes=by_name.get(j["node"],[])
        if len(indexes)!=1 or indexes[0] not in skin_nodes:
            raise ValueError("JOINT_NODE_NOT_UNIQUE_SKIN")
        node=nodes[indexes[0]]
        if TAG in node.get("extras",{}):
            raise ValueError("ALREADY_ANNOTATED_NO_OVERWRITE")
        node.setdefault("extras",{})[TAG]=annotation(j,hash_value)
    return asset


def verify(asset,manifest):
    validate_manifest(manifest)
    expected=digest(canonical(manifest))
    nodes=asset.get("nodes",[])
    skin_nodes=set()
    for skin in asset.get("skins",[]):
        skin_nodes.update(skin.get("joints",[]))
    if not skin_nodes:
        raise ValueError("SKIN_JOINTS_REQUIRED")
    by_name={}
    for i,node in enumerate(nodes):
        if "name" in node:
            by_name.setdefault(node["name"],[]).append(i)
    seen=set()
    for j in manifest["joints"]:
        indexes=by_name.get(j["node"],[])
        if len(indexes)!=1 or indexes[0] not in skin_nodes:
            raise ValueError("JOINT_NODE_NOT_UNIQUE_SKIN")
        current=nodes[indexes[0]].get("extras",{}).get(TAG)
        if current!=annotation(j,expected):
            raise ValueError("EXTRAS_MISSING_CHANGED_OR_TAMPERED")
        if j["id"] in seen:
            raise ValueError("JOINT_ID_DUPLICATE")
        seen.add(j["id"])
    if len(seen)!=len(manifest["joints"]):
        raise ValueError("INCOMPLETE_SOURCE_COVERAGE")
    return {"schema":"scp.rom.gltf_metadata_receipt.v1",
            "status":"PASS_METADATA_PRESERVED_TEST_ONLY",
            "manifest_sha256":expected,"joints_checked":len(seen),
            "anatomy":"UNKNOWN_NOT_MEASURED","enforcement":"NOT_GUARANTEED_BY_GLTF"}


def to_glb(asset):
    raw=canonical(asset)
    padded=raw+b" "*((-len(raw))%4)
    return MAGIC+struct.pack("<II",2,12+8+len(padded))+struct.pack("<II",len(padded),JSON_CHUNK)+padded


def from_glb(blob):
    if len(blob)>MAX or len(blob)<20 or blob[:4]!=MAGIC:
        raise ValueError("GLB_MAGIC_OR_BOUNDS")
    version,total=struct.unpack_from("<II",blob,4)
    if version!=2 or total!=len(blob):
        raise ValueError("GLB_VERSION_LENGTH")
    size,tag=struct.unpack_from("<II",blob,12)
    if tag!=JSON_CHUNK or size%4!=0 or size<2 or 20+size>len(blob):
        raise ValueError("GLB_JSON_CHUNK_INVALID")
    cursor=20+size
    if cursor<len(blob):
        if cursor+8>len(blob):
            raise ValueError("GLB_TRAILING_CHUNK")
        bsize,btype=struct.unpack_from("<II",blob,cursor)
        if btype!=0x004e4942 or bsize%4!=0 or cursor+8+bsize!=len(blob):
            raise ValueError("GLB_BIN_CHUNK_INVALID")
    result=json.loads(blob[20:20+size].decode("utf-8"))
    if not isinstance(result,dict) or result.get("asset",{}).get("version")!="2.0":
        raise ValueError("GLB_JSON_NOT_GLTF")
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--model",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    manifest=json.loads(Path(a.manifest).read_text())
    model=Path(a.model)
    if model.stat().st_size>MAX:
        raise ValueError("SOURCE_ASSET_BOUNDS")
    if model.suffix.lower()==".glb":
        asset=from_glb(model.read_bytes())
    elif model.suffix.lower()==".gltf":
        asset=json.loads(model.read_text())
    else:
        raise ValueError("UNSUPPORTED_SOURCE_FORMAT")
    receipt=verify(asset,manifest)
    receipt["asset_sha256"]=digest(model.read_bytes())
    Path(a.out).write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print(json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    main()
