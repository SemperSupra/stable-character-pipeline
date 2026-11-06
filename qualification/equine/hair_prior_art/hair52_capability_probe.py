#!/usr/bin/env python3
"""Read-only Blender 5.2.3 LTS XPBD / native hair primitive capability probe.

This establishes binary/API availability; it DOES NOT constitute full
strand dynamics or contact simulation qualification. Never promotes 4.5
source or claims the experimental physics backend is production-ready.
"""
import bpy
import hashlib
import json
import sys
from pathlib import Path

if "--" not in sys.argv or len(sys.argv[sys.argv.index("--")+1:])!=1:
    raise SystemExit("usage: blender -b --python hair52_capability_probe.py -- <receipt.json>")
out=Path(sys.argv[sys.argv.index("--")+1])
if out.exists():raise ValueError("refuse to replace prior capability receipt")
out.parent.mkdir(parents=True,exist_ok=True)
record={
    "schema":"equine.hair.blender52.capability.v1",
    "expected_binary_version":"5.2.3",
    "reported_version":bpy.app.version_string,
    "build_hash":str(bpy.app.build_hash),
    "source_probe_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "engine":"Blender Geometry Nodes XPBD",
    "feature_status":"EXPERIMENTAL",
    "simulation_executed":False,
    "crossing_contact_qualified":False,
    "production_version_4_5_15_untouched":True,
    "capability":{},
    "errors":[],
    "science_hold":"KEEP",
}
if bpy.app.version[:3]!=(5,2,3):
    record["errors"].append("unexpected_binary_version")
try:
    group=bpy.data.node_groups.new("ShetlandXPBDProbe","GeometryNodeTree")
    node=group.nodes.new("GeometryNodeXPBDSolver")
    record["capability"]["xpbd_solver_node"]={"bl_idname":node.bl_idname,
        "inputs":[s.name for s in node.inputs],
        "outputs":[s.name for s in node.outputs]}
except Exception as e:
    record["errors"].append("xpbd_node_creation:"+str(e)[:300])

try:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.5)
    scalp=bpy.context.object
    scalp.name="SafeOriginalSyntheticScalp"
    bpy.ops.object.curves_empty_hair_add()
    hair=bpy.context.object
    if hair is None or hair.type!="CURVES":
        raise ValueError("operator did not produce native CURVES")
    record["capability"]["native_hair_object"]={
        "type":hair.type, "name":hair.name,
        "source_surface_name":scalp.name,
        "object_modifiers":[{"name":m.name,"type":m.type} for m in hair.modifiers],
        "source_modifiers":[{"name":m.name,"type":m.type} for m in scalp.modifiers]}
except Exception as e:
    record["errors"].append("hair_curves_operator:"+str(e)[:300])

record["verdict"]="CAPABILITY_AVAILABLE_NOT_SIMULATION_PROOF" if not record["errors"] else "CAPABILITY_PROBE_FAIL_CLOSED"
out.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
print("BLENDER_52_EXPERIMENTAL_HAIR_CAPABILITY",json.dumps(record,sort_keys=True))
if record["errors"]:raise RuntimeError("; ".join(record["errors"]))
