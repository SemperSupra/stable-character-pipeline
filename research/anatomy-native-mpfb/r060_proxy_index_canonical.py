"""R060 controlled normalization of two original-synthetic proxy index streams.

This is an experiment, not an accepted production exporter. Original source bytes
are immutable. Derived GLBs remain on disposable CI runners and are never uploaded.
Only a known-source two-proxy fixture is admitted; face-associated metadata fails
closed, and source-vs-candidate oriented topology must remain identical.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from gltf_godot_morph_compare import parse_glb
from r054_buffer_views import roles_for, audit
from r055_triangle_topology import triangles_from_primitive, oriented, run as topology
from r051_glb_repeatability import fingerprint

def hold(message):
    raise ValueError("R060_CANONICAL_PROXY_HOLD "+message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def primitive_for(glb, name):
    nodes=[n for n in glb.get("nodes",[]) if n.get("name")==name and "mesh" in n]
    if len(nodes)!=1:hold("synthetic proxy node missing/ambiguous: "+name)
    mesh_index=nodes[0]["mesh"]
    mesh=glb["meshes"][mesh_index]
    if len(mesh.get("primitives",[]))!=1:
        hold("proxy has multiple primitives")
    prim=mesh["primitives"][0]
    if prim.get("mode",4)!=4:
        hold("proxy not indexed triangles")
    return mesh_index,mesh,prim

def admit(glb,blob,name,expected_view):
    mi,mesh,prim=primitive_for(glb,name)
    if mesh.get("extras") or mesh.get("extensions") or prim.get("extras") or prim.get("extensions"):
        hold("opaque per-face/mesh annotations prohibit normalization")
    if "indices" not in prim:hold("proxy indices missing")
    acc=glb["accessors"][prim["indices"]]
    if acc.get("extras") or acc.get("extensions") or acc.get("sparse"):
        hold("opaque/sparse index metadata")
    faces,info=triangles_from_primitive(glb,blob,prim)
    if info["buffer_view"]!=expected_view or info["source_vertex_count"]!=420 or info["triangle_count"]!=196 or info["index_count"]!=588 or info["component_type"]!=5123:
        hold("synthetic proxy source revision/cardinality changed")
    view=glb["bufferViews"][expected_view]
    if "extras" in view or "extensions" in view or view.get("byteStride",2)!=2 or acc.get("byteOffset",0)!=0 or view["byteLength"]!=1176:
        hold("unexpected bufferView/offset/stride or extra metadata")
    roles=roles_for(glb).get(expected_view,set())
    if roles!={f"mesh:{mi}:prim:0:indices"}:
        hold("index view alias/reuse would change another consumer")
    if len({oriented(tri) for tri in faces})!=len(faces):
        hold("duplicate triangles need authoring review")
    if any(len(set(tri))!=3 for tri in faces):
        hold("degenerate triangle found")
    return mi,faces,view

def verify_semantics(source,candidate):
    a=topology(source)
    b=topology(candidate)
    if len(a["records"])!=len(b["records"]):
        hold("candidate changed mesh primitive count")
    for x,y in zip(a["records"],b["records"]):
        for k in ("mesh_index","primitive_index","mesh_name","node_names","triangle_count",
                  "source_vertex_count","oriented_face_multiset_sha256","unoriented_face_multiset_sha256"):
            if x[k]!=y[k]:hold("candidate changed mesh topology or winding: "+k)
    # Compare every non-target declared view as literal bytes; index view
    # canonicalization is the only allowed mutation under this experiment.
    x,_,_=audit(source);y,_,_=audit(candidate)
    if len(x["views"])!=len(y["views"]):hold("candidate changed view count")
    changed=[]
    for va,vb in zip(x["views"],y["views"]):
        if (va["index"],va["start"],va["bytes"])!=(vb["index"],vb["start"],vb["bytes"]):
            hold("bufferView offset/length unexpectedly changed")
        if va["sha256"]!=vb["sha256"]:
            if va["index"] not in (5,12):hold("non-proxy data mutated")
            changed.append(va["index"])
    if fingerprint(source)["source_body_positions_and_8_morphs_sha256"]!=fingerprint(candidate)["source_body_positions_and_8_morphs_sha256"]:
        hold("original body morph attributes changed")
    ga,_=parse_glb(source);gb,_=parse_glb(candidate)
    if ga!=gb:hold("glTF JSON mutated")
    return changed

def candidate(source_path,target_path):
    source=Path(source_path).read_bytes()
    glb,bin_chunk=parse_glb(source_path)
    original=sha(source)
    json_size,typ=struct.unpack_from("<II",source,12)
    bin_header=20+json_size
    bin_size,bin_type=struct.unpack_from("<II",source,bin_header)
    if typ!=0x4e4f534a or bin_type!=0x004e4942 or bin_size!=len(bin_chunk):
        hold("GLB layout unexpected")
    bin_start=bin_header+8
    mutation=bytearray(source)
    records=[]
    for name,view_id in [("R036_AnatomyProxy_Left",5),("R036_AnatomyProxy_Right",12)]:
        mi,faces,view=admit(glb,bin_chunk,name,view_id)
        canonical=sorted(oriented(face) for face in faces)
        out=b"".join(struct.pack("<HHH",*face) for face in canonical)
        if len(out)!=view["byteLength"]:hold("index canonical bytes mismatch")
        pos=bin_start+view["byteOffset"]
        before=source[pos:pos+len(out)]
        mutation[pos:pos+len(out)]=out
        records.append({"mesh":mi,"name":name,"view":view_id,"triangles":len(faces),
            "raw_index_sha256":sha(before),"canonical_index_sha256":sha(out),
            "representation_changed":before!=out})
    if sha(source)!=original or Path(source_path).read_bytes()!=source:
        hold("original source altered during candidate construction")
    target=Path(target_path)
    if target.resolve()==Path(source_path).resolve():
        hold("refuse in-place source mutation")
    target.write_bytes(mutation)
    changed=verify_semantics(source_path,target_path)
    result={
      "schema":"r060.synthetic-proxy-canonical.v1",
      "status":"PASS_NARROW_DERIVED_PROXY_TRIANGLE_ORDER",
      "source_whole_sha256":original,
      "derived_whole_sha256":sha(mutation),
      "source_immutable":sha(Path(source_path).read_bytes())==original,
      "changed_buffer_views":changed,
      "records":records,
      "limits":"Only two original-synthetic proxy indexed TRIANGLES in this pinned MPFB export. No per-face external annotation, production donor, guaranteed renderer/interchange equivalence, real anatomy, H.264 film or owner adoption.",
    }
    return result

def negative(source,candidate_path):
    data=bytearray(Path(candidate_path).read_bytes())
    glb,bin_chunk=parse_glb(candidate_path)
    _,_,prim=primitive_for(glb,"R036_AnatomyProxy_Left")
    faces,info=triangles_from_primitive(glb,bin_chunk,prim)
    v=glb["bufferViews"][info["buffer_view"]]
    json_size=struct.unpack_from("<I",data,12)[0]
    first=28+json_size+v["byteOffset"]
    x,y,z=struct.unpack_from("<HHH",data,first)
    struct.pack_into("<HHH",data,first,x,z,y)
    changed=Path(str(candidate_path)+".injected.glb")
    changed.write_bytes(data)
    try:
        try:verify_semantics(source,str(changed))
        except ValueError as err:
            if "R060_CANONICAL_PROXY_HOLD" not in str(err):raise
        else:hold("deliberate winding inversion not rejected")
        return {"reversed_winding_rejected":True,"fixture_original_unchanged":True}
    finally:changed.unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",required=True)
    p.add_argument("--derived",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    receipt=candidate(args.source,args.derived)
    receipt["negative_control"]=negative(args.source,args.derived)
    Path(args.out).write_text(json.dumps(receipt,sort_keys=True)+"\n")
    print("R060_PROXY_CANONICAL_RECEIPT "+json.dumps(receipt,sort_keys=True))

if __name__=="__main__":main()
