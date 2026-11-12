"""Independent stdlib GLB structural and Blender round-trip oracle."""
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

SOURCES={
 "sdfx-octree":"c13eadbac14f1da7645f5f683f3e9b7d019f6ce95c430b51cd043531dae437ca",
 "gsdf-welded":"f53f2ed1c52c1e89cb44cd2292a075053e8de18e0a3cc9c088ec6a05e1aae97a",
}
COUNTS={"sdfx-octree":8266,"gsdf-welded":6348}
TYPE_SIZE={5120:1,5121:1,5122:2,5123:2,5125:4,5126:4}
FMT={5121:"B",5123:"H",5125:"I",5126:"f"}
def read_accessor(gltf,binary,index):
    a=gltf["accessors"][index]
    if "sparse" in a: raise ValueError("SPARSE_UNEXPECTED")
    ctype=a["componentType"]
    n={"SCALAR":1,"VEC3":3}.get(a["type"])
    if n is None or ctype not in FMT:raise ValueError("ACCESSOR_NOT_SUPPORTED")
    view=gltf["bufferViews"][a["bufferView"]]
    stride=view.get("byteStride",TYPE_SIZE[ctype]*n)
    offset=view.get("byteOffset",0)+a.get("byteOffset",0)
    out=[]
    for i in range(a["count"]):
        vals=struct.unpack_from("<"+FMT[ctype]*n,binary,offset+i*stride)
        out.append(vals[0] if n==1 else vals)
    return out

def inspect(path):
    blob=path.read_bytes()
    if len(blob)<20 or blob[:4]!=b"glTF":raise ValueError("INVALID_GLB_MAGIC")
    version,length=struct.unpack_from("<II",blob,4)
    if version!=2 or length!=len(blob):raise ValueError("INVALID_GLB_LENGTH_VERSION")
    pos=12;chunks={}
    while pos<len(blob):
        size,kind=struct.unpack_from("<I4s",blob,pos)
        pos+=8
        if size<0 or pos+size>len(blob) or kind in chunks:raise ValueError("INVALID_CHUNK")
        chunks[kind]=blob[pos:pos+size]
        pos+=size
    gltf=json.loads(chunks[b"JSON"].rstrip(b" "))
    binary=chunks.get(b"BIN"+bytes([0]),b"")
    if not binary:binary=chunks.get(b"BIN"+bytes([0]),b"")
    if not binary:raise ValueError("MISSING_BINARY_CHUNK")
    meshes=gltf.get("meshes",[])
    if len(meshes)!=1:raise ValueError("EXPECTED_ONE_MESH")
    primitives=meshes[0].get("primitives",[])
    if not primitives:raise ValueError("MISSING_PRIMITIVE")
    vertices=faces=0;errors=[]
    for prim in primitives:
        if prim.get("mode",4)!=4:raise ValueError("NOT_TRIANGLES")
        if "POSITION" not in prim.get("attributes",{}):raise ValueError("MISSING_POSITION")
        points=read_accessor(gltf,binary,prim["attributes"]["POSITION"])
        if not all(all(math.isfinite(float(x)) for x in p) for p in points):raise ValueError("NONFINITE")
        indices=read_accessor(gltf,binary,prim["indices"]) if "indices" in prim else list(range(len(points)))
        if len(indices)%3 or any(i>=len(points) or i<0 for i in indices):raise ValueError("INVALID_INDEX")
        vertices+=len(points);faces+=len(indices)//3
    return {"glb_sha256":hashlib.sha256(blob).hexdigest(),"triangles":faces,
            "vertices":vertices,"meshes":len(meshes),"primitives":len(primitives),
            "note":"STL carries no rig, material semantics or procedural edit graph"}

def main():
    root=Path(sys.argv[1])
    output={"schema":"sdf-stl-glb-interchange/v1","models":{}}
    fails=[]
    for name,wanted in SOURCES.items():
        sample=root/(name+".stl")
        exp=json.loads((root/(name+"-export.json")).read_text())
        imp=json.loads((root/(name+"-reimport.json")).read_text())
        raw=sample.read_bytes()
        actual=hashlib.sha256(raw).hexdigest()
        parsed=inspect(root/(name+".glb"))
        b0=exp["source"]["bounds"];b1=imp["mesh"]["bounds"]
        bounds_error=max(abs(b0[side][axis]-b1[side][axis]) for side in range(2) for axis in range(3))
        triangle_parity=exp["source"]["triangles"]==imp["mesh"]["triangles"]==parsed["triangles"]==COUNTS[name]
        hash_parity=exp["glb_sha256"]==imp["glb_sha256"]==parsed["glb_sha256"]
        source_match=actual==wanted==exp["source_stl_sha256"]
        ok=source_match and triangle_parity and hash_parity and bounds_error<=1e-5
        output["models"][name]={"status":"PASS" if ok else "FAIL","source_sha256":actual,
             "triangle_parity":triangle_parity,"glb_hash_parity":hash_parity,
             "source_hash_match":source_match,"max_bounds_error":bounds_error,"glb":parsed}
        if not ok:fails.append(name)
    output["status"]="PASS" if not fails else "FAIL"
    (root/"interchange-receipt.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print(json.dumps(output,sort_keys=True))
    if fails:sys.exit(1)
if __name__=="__main__":main()
