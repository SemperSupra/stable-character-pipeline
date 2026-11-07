#!/usr/bin/env python3
"""Fail-closed source admission for the official CC0 MakeHuman human base OBJ.

This observes topology/rights of the source; it does not assume its helper
meshes are body geometry or imply rig, scale, clothing or visual acceptance.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA="scp.r009.human_basemesh.source_admission.v1"
OFFICIAL_COMMIT="a8bc2d54ff0ac92e78ff71431b1023eda42bf482"
OFFICIAL_BLOB="d26635e9326e3cca30778fd7b9c00062b03cce09"
OFFICIAL_URL=("https://raw.githubusercontent.com/makehumancommunity/makehuman/"
              +OFFICIAL_COMMIT+"/makehuman/data/3dobjs/base.obj")
EXPECTED={"vertices":19158,"quads":18486,"body_quads":13378,
          "body_vertex_indices":13380,"groups":139}

class AdmissionError(ValueError):
    pass

def git_blob_sha1(data):
    if type(data) is not bytes:
        raise AdmissionError("EXPECTED_BYTES")
    return hashlib.sha1(("blob %d\0"%len(data)).encode()+data).hexdigest()

def inspect(data,expected_blob_sha1,expected_shape=None):
    if type(expected_blob_sha1) is not str or len(expected_blob_sha1)!=40:
        raise AdmissionError("MISSING_BLOB_PIN")
    observed=git_blob_sha1(data)
    if observed!=expected_blob_sha1:
        raise AdmissionError("SOURCE_BLOB_SHA_MISMATCH")
    try:
        lines=data.decode("utf-8").splitlines()
    except UnicodeDecodeError as e:
        raise AdmissionError("NOT_UTF8_OBJ") from e
    if not any("explicitly released as CC0" in line for line in lines[:24]):
        raise AdmissionError("SOURCE_LICENSE_HEADER_MISSING")
    points=[];groups={};body=set();group=None
    mins=[math.inf]*3;maxs=[-math.inf]*3
    for line in lines:
        if not line or line.startswith("#"):
            continue
        tok=line.split();op=tok[0]
        if op=="v":
            if len(tok)!=4:
                raise AdmissionError("BAD_VERTEX_ARITY")
            try: xyz=[float(t) for t in tok[1:]]
            except ValueError as e: raise AdmissionError("BAD_VERTEX") from e
            if not all(math.isfinite(v) for v in xyz):
                raise AdmissionError("NONFINITE_VERTEX")
            points.append(xyz)
            for i,v in enumerate(xyz):
                mins[i]=min(mins[i],v);maxs[i]=max(maxs[i],v)
        elif op=="g":
            if len(tok)!=2 or not tok[1]:
                raise AdmissionError("BAD_GROUP")
            group=tok[1]
            # Legal OBJ files can reopen a previously used group.
            # Preserve the earlier face count rather than zeroing it.
            groups.setdefault(group,0)
        elif op=="f":
            if group is None: raise AdmissionError("UNGROUPED_FACE")
            if len(tok)!=5: raise AdmissionError("NON_QUAD_FACE")
            try: ids=[int(t.split("/")[0]) for t in tok[1:]]
            except ValueError as e: raise AdmissionError("BAD_FACE_INDEX") from e
            if len(set(ids))!=4 or any(i<1 or i>len(points) for i in ids):
                raise AdmissionError("INVALID_FACE_INDEX")
            groups[group]+=1
            if group=="body":
                body.update(ids)
        elif op not in ("vt","vn","o","s","usemtl","mtllib"):
            raise AdmissionError("UNSUPPORTED_OBJ_RECORD:"+op)
    if not points or "body" not in groups:
        raise AdmissionError("MISSING_BODY")
    faces=sum(groups.values())
    quantities={"vertices":len(points),"quads":faces,"body_quads":groups["body"],
                "body_vertex_indices":len(body),"groups":len(groups)}
    if expected_shape and quantities!=expected_shape:
        raise AdmissionError("PINNED_TOPOLOGY_MISMATCH")
    return {"schema":SCHEMA,"admission":"SOURCE_GEOMETRY_ONLY",
            "source_commit":OFFICIAL_COMMIT,"source_git_blob_sha1":observed,
            "raw_sha256":hashlib.sha256(data).hexdigest(),
            "source_url":OFFICIAL_URL,"license":"CC0-1.0_CORE_ASSET",
            "quantities":quantities,"helper_quad_faces":faces-groups["body"],
            "min_native":mins,"max_native":maxs,
            "body_only_exported":False,"rig_transfer_qualified":False,
            "morphology_qualified":False,"cloth_fit_qualified":False,
            "native_blender_qualified":False,"human_realism_accepted":False,
            "release_approved":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--expected-blob",default=OFFICIAL_BLOB)
    a=p.parse_args()
    if a.out.exists() or a.out.resolve()==a.input.resolve():
        raise AdmissionError("NO_OVERWRITE")
    receipt=inspect(a.input.read_bytes(),a.expected_blob,EXPECTED)
    a.out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"admission":receipt["admission"],
                      "quantities":receipt["quantities"],
                      "sha256":receipt["raw_sha256"]},sort_keys=True))

if __name__=="__main__":
    main()
