"""R055 original-synthetic glTF triangle index order/winding/topology fingerprint.

Pass requires real GLB with bounded 2.0 JSON/BIN chunks; independent public
runners print digests and mesh names only. The original model is untouched.
Permutation-equivalent triangle sets are not assumed to be visually equivalent.
"""
import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from gltf_godot_morph_compare import parse_glb

def fail(message):
    raise ValueError("R055_TRIANGLE_HOLD "+message)

def triangles_from_primitive(glb, blob, primitive):
    accs=glb.get("accessors",[])
    views=glb.get("bufferViews",[])
    if "indices" not in primitive or "POSITION" not in primitive.get("attributes",{}):
        fail("glTF triangle primitive missing indices or POSITION")
    index=primitive["indices"]
    if not isinstance(index,int) or not 0<=index<len(accs):fail("invalid index accessor")
    acc=accs[index]
    if acc.get("type")!="SCALAR" or "sparse" in acc:
        fail("unsupported sparse/non-scalar index accessor")
    fmt_size={5121:("<B",1),5123:("<H",2),5125:("<I",4)}
    if acc.get("componentType") not in fmt_size:fail("unsupported triangle index type")
    fmt,size=fmt_size[acc["componentType"]]
    count=acc.get("count")
    if not isinstance(count,int) or not 0<count<=10000000 or count%3:
        fail("invalid indexed triangle cardinality")
    vi=acc.get("bufferView")
    if not isinstance(vi,int) or not 0<=vi<len(views):
        fail("missing or invalid triangle index buffer view")
    view=views[vi]
    off=view.get("byteOffset",0)+acc.get("byteOffset",0)
    stride=view.get("byteStride",size)
    declared_start=view.get("byteOffset",0)
    declared_end=declared_start+view["byteLength"]
    if stride<size or off<declared_start or off+(count-1)*stride+size>declared_end or declared_end>len(blob):
        fail("triangle index accessor escapes glTF view or binary")
    p=primitive["attributes"]["POSITION"]
    if not isinstance(p,int) or not 0<=p<len(accs):fail("invalid POSITION accessor")
    verts=accs[p].get("count")
    if not isinstance(verts,int) or verts<=0:fail("invalid POSITION count")
    idx=[struct.unpack_from(fmt,blob,off+i*stride)[0] for i in range(count)]
    if max(idx)>=verts:fail("triangle index exceeds vertex POSITION count")
    faces=[tuple(idx[i:i+3]) for i in range(0,len(idx),3)]
    return faces,{"buffer_view":vi,"source_vertex_count":verts,"index_count":count,
                  "triangle_count":len(faces),"component_type":acc["componentType"]}

def oriented(face):
    a,b,c=face
    return min((a,b,c),(b,c,a),(c,a,b))

def face_hash(faces,normalizer):
    h=hashlib.sha256()
    h.update(struct.pack("<I",len(faces)))
    for tri in sorted(normalizer(x) for x in faces):
        h.update(struct.pack("<III",*tri))
    return h.hexdigest()

def summarize(faces,structure):
    if not faces:fail("empty indexed triangle set")
    if any(len(set(face))!=3 for face in faces):fail("degenerate repeated vertex indices")
    src=structure.copy()
    src.update({
      "oriented_face_multiset_sha256":face_hash(faces,oriented),
      "unoriented_face_multiset_sha256":face_hash(faces,lambda x:tuple(sorted(x))),
      "unique_unoriented_faces":len({tuple(sorted(f)) for f in faces}),
      "unique_oriented_faces":len({oriented(f) for f in faces}),
      "order_invariant_only":True,
    })
    return src

def negative_controls():
    fixture=[(0,1,2),(2,3,4)]
    reordered=[(2,3,4),(0,1,2)]
    cyclic=[(1,2,0),(3,4,2)]
    reversed_one=[(0,2,1),(2,3,4)]
    topology_changed=[(0,1,3),(2,3,4)]
    keep=face_hash(fixture,oriented)
    un=face_hash(fixture,lambda x:tuple(sorted(x)))
    if face_hash(reordered,oriented)!=keep or face_hash(cyclic,oriented)!=keep:
        fail("triangle order/cyclic rotation negative failed")
    if face_hash(reversed_one,oriented)==keep:
        fail("flipped winding was falsely treated as equivalent")
    if face_hash(reversed_one,lambda x:tuple(sorted(x)))!=un:
        fail("unoriented winding equivalence oracle failed")
    if face_hash(topology_changed,lambda x:tuple(sorted(x)))==un:
        fail("changed triangle connectivity went undetected")
    return {"reordered_and_cyclic_pass":True,"winding_flip_detected":True,
            "topology_mutation_detected":True,"original_source_unmodified":True}

def run(path):
    glb,blob=parse_glb(path)
    meshes=glb.get("meshes",[])
    if not meshes or len(meshes)>10000:fail("unexpected mesh cardinality")
    labels={}
    for node in glb.get("nodes",[]):
        if "mesh" in node:
            labels.setdefault(node["mesh"],set()).add(node.get("name","UNNAMED"))
    records=[]
    for mi,mesh in enumerate(meshes):
        for pi,prim in enumerate(mesh.get("primitives",[])):
            if prim.get("mode",4)!=4:fail("non-TRIANGLES glTF mode unsupported")
            faces,structure=triangles_from_primitive(glb,blob,prim)
            record=summarize(faces,structure)
            record.update({
                "mesh_index":mi,"primitive_index":pi,
                "mesh_name":mesh.get("name","UNNAMED"),
                "node_names":sorted(labels.get(mi,set()))[:8],
            })
            records.append(record)
    if not records:fail("no triangle mesh primitives")
    return {"schema":"r055.gltf.triangle-topology-receipt.v1",
       "status":"PASS_NARROW_ORIGINAL_TRIANGLE_TOPOLOGY_FINGERPRINT",
       "meshes":len(meshes),"mesh_primitives":len(records),
       "adversarial_control":negative_controls(),
       "records":records,
       "limits":"Same source vertex index identity assumed only when independent POSITION/attributes match. Multiset/winding signatures cannot prove physical organ morphology, surface appearance, skinned pose, or authoring intent."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--glb",required=True)
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    record=run(args.glb)
    Path(args.out).write_text(json.dumps(record,sort_keys=True)+"\n",encoding="utf-8")
    print("R055_TRIANGLE_TOPOLOGY "+json.dumps(record,sort_keys=True))

if __name__=="__main__":main()
