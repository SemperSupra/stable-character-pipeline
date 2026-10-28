#!/usr/bin/env python3
"""R7 source-bound numeric cross-reader glTF skin ↔ real bpy depsgraph parity.

Source glTF Y_UP coordinates are remapped on Blender import to Z_UP via
Xb=Xg, Yb=-Zg, Zb=Yg. Both positions originate from the same procedural
camera-plane GLB. This comparison does not measure anatomy or real motion.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA="stable-character/r7-vertex-world/1"
PREDECLARED_TOLERANCE=0.0005  # arbitrary source rig units, not meters
SOURCE_SHA="69a9869e21542dcdaade37f290c29b6d7217ae0e392f450aeb40efe00611ac6a"

def transform(p):
    return (p[0],-p[2],p[1])

def read(path,reader):
    b=Path(path).read_bytes()
    r=json.loads(b)
    if (r.get("schema")!=SCHEMA or r.get("reader")!=reader or
        r.get("input_glb_sha256")!=SOURCE_SHA or
        r.get("source_camera_plane_only") is not True or
        r.get("anatomical_accuracy")!="NOT_TESTED"):
        raise ValueError("R7 source/reader/semantics mismatch")
    f=r.get("frames")
    if not isinstance(f,list) or len(f)!=10:raise ValueError("requires exactly 10 frames")
    for i,item in enumerate(f):
        if item.get("sample")!=i or item.get("source_second")!=13+i:
            raise ValueError("source second or sampled frame mismatch")
        verts=item.get("vertices")
        if not isinstance(verts,list) or len(verts)!=192:
            raise ValueError("requires exactly 192 sampled vertices")
        for p in verts:
            if not isinstance(p,list) or len(p)!=3 or any(
                    not isinstance(x,(int,float)) or isinstance(x,bool) or
                    not math.isfinite(x) for x in p):
                raise ValueError("nonfinite or bad coordinate")
    return r,hashlib.sha256(b).hexdigest()

def matches_bijective(a,b,tol):
    # First source-matched geometry oracle: unique point-set matching within tol
    # is distinct from source vertex *index* parity. No duplicate can satisfy
    # two targets merely by sharing one nearest point.
    adj=[]
    for p in a:
        adj.append([j for j,q in enumerate(b) if math.dist(p,q)<=tol])
    assigned=[-1]*len(b)
    def augment(i,seen):
        for j in adj[i]:
            if j in seen:continue
            seen.add(j)
            if assigned[j]<0 or augment(assigned[j],seen):
                assigned[j]=i
                return True
        return False
    return all(augment(i,set()) for i in range(len(a)))

def compare(gltf,blender,tol=PREDECLARED_TOLERANCE):
    if not 0<tol<=0.0005:raise ValueError("unreviewed tolerance widening")
    if len(gltf["frames"])!=len(blender["frames"]):
        raise ValueError("count mismatch")
    samples=[]
    for gf,bf in zip(gltf["frames"],blender["frames"]):
        if gf["source_second"]!=bf["source_second"]:
            raise ValueError("timestamp mismatch")
        g=[transform(p) for p in gf["vertices"]]
        b=[tuple(p) for p in bf["vertices"]]
        errs=[math.dist(x,y) for x,y in zip(g,b)]
        multisets_ok=matches_bijective(g,b,tol)
        samples.append({
            "source_second":gf["source_second"],
            "indexed_max_error_camera_plane_units":max(errs),
            "indexed_rms_error_camera_plane_units":math.sqrt(sum(x*x for x in errs)/len(errs)),
            "indexed_error_within_tolerance":max(errs)<=tol,
            "unique_bijective_point_set_within_tolerance":multisets_ok,
            "vertex_count":len(errs)
        })
    direct=all(f["indexed_error_within_tolerance"] for f in samples)
    setwise=all(f["unique_bijective_point_set_within_tolerance"] for f in samples)
    status=("PASS_INDEXED_VERTEX_PARITY" if direct else
            "PASS_POINT_SET_PARITY_INDEX_MAP_UNPROVEN" if setwise else
            "FAIL_NUMERIC_VERTEX_PARITY")
    return {
        "schema":"stable-character/r7-vertex-parity/1",
        "status":status,
        "classification":"ACTUAL_BLENDER_BPY_VS_INDEPENDENT_GLTF_MATH_CAMERA_PLANE_NOT_ANATOMICAL_TRUTH",
        "source_glb_sha256":SOURCE_SHA,
        "predeclared_tolerance_arbitrary_units":tol,
        "coordinate_map":"glTF(X,Y,Z) -> Blender(X,-Z,Y)",
        "sample_count":len(samples),
        "vertices_per_sample":192,
        "all_indexed":direct,
        "all_bijective_point_sets":setwise,
        "max_indexed_error_camera_plane_units":max(f["indexed_max_error_camera_plane_units"] for f in samples),
        "source_person_identity_accuracy":"NOT_TESTED",
        "real_body_anatomy_accuracy":"NOT_TESTED",
        "independent_source_truth_oracle":False,
        "samples":samples
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--gltf",required=True)
    p.add_argument("--blender",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    g,gh=read(a.gltf,"independent_glTF_source_XYZ")
    b,bh=read(a.blender,"bpy_evaluated_mesh_world_XYZ")
    result=compare(g,b)
    result["glTF_readback_sha256"]=gh
    result["blender_readback_sha256"]=bh
    out=Path(a.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("R7_NUMERIC_VERTEX_PARITY",json.dumps({k:v for k,v in result.items() if k!="samples"},sort_keys=True))
    if result["status"]=="FAIL_NUMERIC_VERTEX_PARITY":
        raise SystemExit("R7 strict glTF/Blender numeric parity falsifier triggered")

if __name__=="__main__":main()
