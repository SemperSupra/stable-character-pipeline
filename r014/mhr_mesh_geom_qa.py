"""MHR real skin mesh signed-morph topology-fidelity qualification.

Uses official glTF accessors (including sparse morph target accessors) to test
triangle face orientation and area preservation at opposite morph extremes
and their simultaneous combinations.

Does NOT claim incompressibility, local mass conservation, true tissue dynamics,
medical accuracy, skinned-pose collision, or photoreal video suitability.
"""
import argparse,json,struct,sys,unittest
from pathlib import Path
import numpy as np

TARGETS=(
    "R014_left_cheek_research_mask_positive",
    "R014_left_cheek_research_mask_negative",
    "R014_abdomen_research_mask_positive",
    "R014_abdomen_research_mask_negative",
)
def load(path):
    with path.open("rb") as f:
        magic,version,length=struct.unpack("<4sII",f.read(12))
        assert magic==b"glTF" and version==2 and length==path.stat().st_size
        n,typ=struct.unpack("<I4s",f.read(8))
        assert typ==b"JSON" and not n%4
        g=json.loads(f.read(n))
        byte_count,typ=struct.unpack("<I4s",f.read(8))
        assert typ==b"BIN\x00"
        raw=f.read(byte_count)
        assert len(raw)==byte_count and byte_count>=g["buffers"][0]["byteLength"]
        return g,raw

COMPONENT={5121:np.uint8,5123:np.uint16,5125:np.uint32,5126:np.float32}
WIDTH={"SCALAR":1,"VEC2":2,"VEC3":3,"VEC4":4}

def accessor(doc,raw,index):
    acc=doc["accessors"][index]
    dtype=COMPONENT[acc["componentType"]]
    width=WIDTH[acc["type"]]
    count=acc["count"]
    assert count>0 and width>0
    if "bufferView" in acc:
        view=doc["bufferViews"][acc["bufferView"]]
        off=view.get("byteOffset",0)+acc.get("byteOffset",0)
        step=view.get("byteStride",np.dtype(dtype).itemsize*width)
        arr=np.ndarray((count,width),dtype=dtype,buffer=raw,
                       offset=off,strides=(step,np.dtype(dtype).itemsize)).copy()
    else:
        arr=np.zeros((count,width),dtype=dtype)
    if "sparse" in acc:
        sparse=acc["sparse"]
        iv=sparse["indices"];vv=sparse["values"]
        index_view=doc["bufferViews"][iv["bufferView"]]
        value_view=doc["bufferViews"][vv["bufferView"]]
        ind=np.frombuffer(raw,dtype=COMPONENT[iv["componentType"]],
                 count=sparse["count"],
                 offset=index_view.get("byteOffset",0)+iv.get("byteOffset",0))
        vals=np.frombuffer(raw,dtype=dtype,count=sparse["count"]*width,
                 offset=value_view.get("byteOffset",0)+vv.get("byteOffset",0))
        assert np.all(ind<count),"sparse accessor index invalid"
        assert len(set(ind.tolist()))==len(ind),"duplicate sparse indices"
        arr[ind]=vals.reshape(-1,width)
    if not np.all(np.isfinite(arr)):
        raise ValueError("NaN or infinity in geometry accessor")
    return arr

def metrics(base,faces,delta):
    first=base[faces]
    second=(base+delta)[faces]
    ca=np.cross(first[:,1]-first[:,0],first[:,2]-first[:,0])
    cb=np.cross(second[:,1]-second[:,0],second[:,2]-second[:,0])
    norm_a=np.linalg.norm(ca,axis=1)
    norm_b=np.linalg.norm(cb,axis=1)
    assert np.all(norm_a>1e-12),"source mesh contains degenerate triangles"
    ratio=norm_b/norm_a
    dots=np.sum(ca*cb,axis=1)
    return {"orientation_flips":int(np.sum(dots<=0.)),
            "area_ratio_min":float(ratio.min()),
            "area_ratio_max":float(ratio.max()),
            "area_ratio_p01":float(np.percentile(ratio,1)),
            "area_ratio_p99":float(np.percentile(ratio,99)),
            "max_vertex_displacement_m":float(np.linalg.norm(delta,axis=1).max()),
            "active_vertices":int(np.count_nonzero(np.linalg.norm(delta,axis=1)>1e-7))}

def assess(doc,raw):
    meshes=doc["meshes"]
    match=[(mesh,prim) for mesh in meshes for prim in mesh["primitives"]
           if set(TARGETS).issubset(mesh.get("extras",{}).get("targetNames",[]))]
    assert len(match)==1,"expected one MHR source mesh with four signed region targets"
    mesh,prim=match[0]
    names=mesh["extras"]["targetNames"]
    base=accessor(doc,raw,prim["attributes"]["POSITION"]).astype(np.float64)
    faces=accessor(doc,raw,prim["indices"]).astype(np.int64).ravel().reshape(-1,3)
    assert len(base)>10000 and len(faces)>20000
    deltas={}
    for name in TARGETS:
        i=names.index(name)
        delta=accessor(doc,raw,prim["targets"][i]["POSITION"]).astype(np.float64)
        assert len(delta)==len(base)
        deltas[name]=delta
    # Blender's source morph deltas undergo float32/vertex weld rounding.
    errors={}
    for prefix in ("R014_left_cheek_research_mask_","R014_abdomen_research_mask_"):
        p=deltas[prefix+"positive"];n=deltas[prefix+"negative"]
        err=float(np.linalg.norm(p+n,axis=1).max())
        errors[prefix.rstrip("_")]=err
        assert err<1e-5,("asymmetric signed pair",prefix,err)
    probes={name:delta for name,delta in deltas.items()}
    for side_cheek in ("positive","negative"):
        for side_abd in ("positive","negative"):
            key="combined_cheek_"+side_cheek+"_abdomen_"+side_abd
            probes[key]=deltas["R014_left_cheek_research_mask_"+side_cheek]+deltas["R014_abdomen_research_mask_"+side_abd]
    measurements={name:metrics(base,faces,delta) for name,delta in probes.items()}
    failures=[]
    for name,m in measurements.items():
        if m["orientation_flips"]!=0:failures.append(name+":INVERTED_TRIANGLE")
        if m["area_ratio_min"]<0.65:failures.append(name+":AREA_COLLAPSE")
        if m["area_ratio_max"]>2.0:failures.append(name+":EXCESSIVE_AREA_STRETCH")
        if not 40<=m["active_vertices"]<=5000:failures.append(name+":MASK_COVERAGE")
        if m["max_vertex_displacement_m"]>0.025:failures.append(name+":OUT_OF_BOUNDS")
    return {"status":"PASS_SURFACE_ORIENTATION_AND_AREA_ONLY" if not failures else "HOLD_DEFORMED_SURFACE_GEOMETRY",
            "failures":failures,"input_vertices":len(base),
            "triangles":len(faces),"source_watertight_not_claimed":True,
            "signed_morph_pair_max_sum_norm":errors,
            "measurements":measurements,
            "limitations":["Triangle winding/area is not physiological soft-tissue simulation",
                           "No skin-layer incompressibility, per-region volume, collisions or contacts",
                           "Only four static signed extremes and four simultaneous extreme pairs checked",
                           "Rigged motion, material quality and photoreal video remain unqualified"]}

class Controls(unittest.TestCase):
    def test_triangle_identity(self):
        v=np.array([(0,0,0),(1,0,0),(0,1,0)],np.float64)
        face=np.array([(0,1,2)],np.int64)
        m=metrics(v,face,np.zeros_like(v))
        self.assertEqual(m["orientation_flips"],0)
        self.assertEqual(m["area_ratio_min"],1)
    def test_triangle_flip_detected(self):
        v=np.array([(0,0,0),(1,0,0),(0,1,0)],np.float64)
        face=np.array([(0,1,2)],np.int64)
        delta=np.array([(0,0,0),(-2,0,0),(0,0,0)],np.float64)
        self.assertEqual(metrics(v,face,delta)["orientation_flips"],1)
    def test_triangle_area_loss_detectable(self):
        v=np.array([(0,0,0),(1,0,0),(0,1,0)],np.float64)
        face=np.array([(0,1,2)],np.int64)
        d=np.array([(0,0,0),(-.8,0,0),(0,0,0)],np.float64)
        self.assertLess(metrics(v,face,d)["area_ratio_min"],.65)

if __name__=="__main__":
    if "--self-test" in sys.argv:
        unittest.main(argv=[sys.argv[0]],verbosity=2)
    else:
        p=argparse.ArgumentParser()
        p.add_argument("--glb",required=True,type=Path)
        p.add_argument("--receipt",required=True,type=Path)
        args=p.parse_args()
        output=assess(*load(args.glb))
        args.receipt.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
        print("R014_MHR_GEOMETRY_GATE",json.dumps({k:v for k,v in output.items() if k!="measurements"},sort_keys=True))
        raise SystemExit(output["status"]!="PASS_SURFACE_ORIENTATION_AND_AREA_ONLY")
