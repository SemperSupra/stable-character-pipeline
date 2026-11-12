"""Independent native Blender morphology diversity oracle on actual prior GHA .blend artifacts.

Source meshes are evaluated at rest *after* MPFB shape keys and rig modifiers;
basis vertex bounds are not sufficient because raw MPFB basis can be identical.
"""
import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
import bpy

p=argparse.ArgumentParser()
p.add_argument("--blend",type=Path,required=True)
p.add_argument("--generation",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve()
g=json.loads(a.generation.read_text())
assert g["status"]=="PASS_NATIVE_MORPH_RIG_ANIMATION_EXPORT_AND_STILLS_ONLY"
assert len(g["characters"])==3
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
dep=bpy.context.evaluated_depsgraph_get()

def coordinates(obj,evaluated):
    if evaluated:
        ev=obj.evaluated_get(dep);mesh=ev.to_mesh()
    else:
        mesh=obj.data
    try:return [tuple(float(v.co[i]) for i in range(3)) for v in mesh.vertices]
    finally:
        if evaluated:ev.to_mesh_clear()

def digest(positions):
    h=hashlib.sha256()
    for xyz in positions:
        h.update(struct.pack("<3f",*(round(x,6) for x in xyz)))
    return h.hexdigest()

def bounding(positions):
    return [round(max(p[i] for p in positions)-min(p[i] for p in positions),7) for i in range(3)]

out={"schema":"r014.six_morph.native_evaluated_geometry.v1",
     "status":"NOT_QUALIFIED","source":a.blend.name,
     "source_mpbf":"makehumancommunity/mpfb2@6ff1eb358f6c1959ced77e79e6dd2406d9a71f49",
     "shard":g["shard"],"characters":[],
     "qualification_scope":"evaluated full-source Blender geometry after source morph shape keys; local mesh coords; no metric body measurement and no photoreal qualification"}
for record in g["characters"]:
    obj=bpy.data.objects[record["case"]+"_clean_body"]
    assert obj.type=="MESH"
    assert any(m.type=="ARMATURE" and m.object for m in obj.modifiers)
    raw=coordinates(obj,False)
    evaluated=coordinates(obj,True)
    assert len(raw)==len(evaluated)==record["clean_vertices"]
    active_shape_keys=[]
    if obj.data.shape_keys:
        active_shape_keys=[{"name_sha":hashlib.sha256(k.name.encode()).hexdigest()[:16],
                            "weight":round(float(k.value),6)}
                           for k in obj.data.shape_keys.key_blocks if k.value>0.0001]
    out["characters"].append({
        "name":record["case"],"source_macros":record["source_macros"],
        "vertices":len(evaluated),
        "raw_basis_sha256":digest(raw),
        "evaluated_rest_pose_sha256":digest(evaluated),
        "raw_basis_extent_xyz_blender_units":bounding(raw),
        "evaluated_extent_xyz_blender_units":bounding(evaluated),
        "active_shape_key_count":len(active_shape_keys),
        "active_shape_key_weights":active_shape_keys,
    })
names=[x["name"] for x in out["characters"]]
raw_hashes={x["raw_basis_sha256"] for x in out["characters"]}
eval_hashes={x["evaluated_rest_pose_sha256"] for x in out["characters"]}
out["distinct_raw_basis_hashes"]=len(raw_hashes)
out["distinct_evaluated_mesh_hashes"]=len(eval_hashes)
out["expected_distinct_evaluated_hashes"]=3
out["status"]="PASS_THREE_INDEPENDENT_ACTUAL_EVALUATED_MORPHOLOGIES" if len(eval_hashes)==3 else "FAIL_NON_DISTINCT_NATIVE_EVALUATED_GEOMETRY"
a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print("R014_EVAL_MORPH_ORACLE",json.dumps(out,sort_keys=True))
if out["status"].startswith("FAIL"):sys.exit(1)
