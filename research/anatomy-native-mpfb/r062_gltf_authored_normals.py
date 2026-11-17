"""R062 source-authored glTF NORMAL provenance vs derived proxy face order.

Only SHA/count results leave the original-synthetic public runner. Does not
treat source normal identity as imported Blender shading equality. This
headless stdlib oracle keeps winding orientation (cyclic only).
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

from gltf_godot_morph_compare import parse_glb, accessor_xyz
from r055_triangle_topology import triangles_from_primitive, oriented
from r060_proxy_index_canonical import primitive_for

NAMES=("R036_AnatomyProxy_Left","R036_AnatomyProxy_Right")

def hold(msg): raise ValueError("R062_SOURCE_NORMAL_HOLD "+msg)

def hashed(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def face_normal_signature(faces,normals):
    # Keep the oriented face identity and each indexed per-vertex authored
    # normal together. Order of triangles and cyclic start may change safely.
    items=[]
    for f in faces:
        canonical=min((f,f[1:]+f[:1],f[2:]+f[:2]))
        items.append((canonical,tuple(normals[i] for i in canonical)))
    return hashed(sorted(items))

def source_receipt(glb_path):
    doc,blob=parse_glb(glb_path)
    rows=[]
    for name in NAMES:
        _,mesh,prim=primitive_for(doc,name)
        faces,info=triangles_from_primitive(doc,blob,prim)
        index=prim.get("attributes",{}).get("NORMAL")
        if not isinstance(index,int):hold("authored NORMAL missing "+name)
        vals=accessor_xyz(doc,blob,index)
        if len(vals)!=info["source_vertex_count"] or len(vals)!=420:
            hold("authored NORMAL cardinality mismatch "+name)
        if any(not all(math.isfinite(x) for x in n) for n in vals):
            hold("nonfinite source NORMAL")
        rows.append({
            "node":name,
            "normal_source":"gltf_accessor_float32_VEC3",
            "triangles":len(faces),
            "vertices":len(vals),
            "normal_per_vertex_sha256":hashed(vals),
            "oriented_face_normal_multiset_sha256":face_normal_signature(faces,vals),
            "nonzero_normals":sum(sum(v*v for v in n)>0 for n in vals)
        })
    return rows

def run(first,second):
    a=source_receipt(first)
    b=source_receipt(second)
    if a!=b:
        diffs=[(x["node"],[k for k in x if x[k]!=y[k]]) for x,y in zip(a,b)]
        hold("authored NORMAL altered by triangle ordering: "+str(diffs))
    # Reject an actual NORMAL association mutation; no model bytes changed.
    doc,blob=parse_glb(first)
    _,_,prim=primitive_for(doc,NAMES[0])
    faces,_=triangles_from_primitive(doc,blob,prim)
    vals=accessor_xyz(doc,blob,prim["attributes"]["NORMAL"])
    baseline=face_normal_signature(faces,vals)
    tampered=list(vals)
    tampered[faces[0][0]]=(tampered[faces[0][0]][0]+0.1,)+tampered[faces[0][0]][1:]
    if baseline==face_normal_signature(faces,tampered):
        hold("negative mutated authored source normal escaped")
    flipped=list(faces)
    flipped[0]=(flipped[0][0],flipped[0][2],flipped[0][1])
    if baseline==face_normal_signature(flipped,vals):
        hold("negative flipped winding escaped")
    return {
        "schema":"r062.original-synthetic-gltf-authored-normals.v1",
        "status":"PASS_NARROW_AUTHORED_NORMAL_ASSOCIATION_INVARIANT",
        "source_glb_sha256":hashlib.sha256(Path(first).read_bytes()).hexdigest(),
        "derived_glb_sha256":hashlib.sha256(Path(second).read_bytes()).hexdigest(),
        "records":a,
        "negatives":{"normal_mutation_rejected":True,"winding_inversion_rejected":True},
        "limits":"Authoring/source NORMAL association only; cannot establish native importer corner shading, rendered pixels or real anatomical acceptance."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True)
    p.add_argument("--derived",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    result=run(args.source,args.derived)
    Path(args.out).write_text(json.dumps(result,sort_keys=True)+"\n")
    print("R062_AUTHORED_NORMAL_RECEIPT "+json.dumps(result,sort_keys=True))

if __name__=="__main__":main()
