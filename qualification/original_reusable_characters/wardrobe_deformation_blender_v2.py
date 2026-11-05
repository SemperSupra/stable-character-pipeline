#!/usr/bin/env python3
"""Blender-native R009 all72 skinned garment deformation witness (research).

Structural failures are fatal; measured stretch and unmeasured penetration
remain explicit FAIL/UNKNOWN and never produce human-quality acceptance.
No private models, plugins, or cloud credentials are needed.
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
import bpy

ACTORS=("AsterOriginal","JuniperOriginal")
GARMENTS=("top","bottom","alt_top","alt_bottom")

def obj_index():
    found={}
    for obj in bpy.data.objects:
        if obj.type!="MESH":continue
        ident=obj.name if "_Wardrobe_" in obj.name else obj.data.name
        if "_Wardrobe_" not in ident:continue
        actor,slot=ident.split("_Wardrobe_",1)
        slot=slot.split(".")[0]
        if actor not in ACTORS:raise ValueError("UNKNOWN_WARDROBE_ACTOR")
        if (actor,slot) in found:raise ValueError("DUPLICATE_WARDROBE_OBJECT")
        found[(actor,slot)]=obj
    for actor in ACTORS:
        for slot in ("body","top","bottom","alt_top","alt_bottom"):
            if (actor,slot) not in found:
                raise ValueError("MISSING_REQUIRED_SLOT:"+actor+":"+slot)
    return found

def evaluated_vertices(obj, graph):
    ev=obj.evaluated_get(graph)
    mesh=ev.to_mesh()
    try:
        matrix=ev.matrix_world
        points=[tuple(matrix @ v.co) for v in mesh.vertices]
    finally:
        ev.to_mesh_clear()
    if not all(math.isfinite(k) for p in points for k in p):
        raise ValueError("NONFINITE_SKIN_DEFORMATION")
    return points

def audit(path,receipt,frames=72):
    path=Path(path).resolve();receipt=Path(receipt).resolve()
    if path==receipt:raise ValueError("SOURCE_OVERWRITE_REFUSED")
    if not path.is_file():raise ValueError("INPUT_GLB_MISSING")
    bpy.ops.import_scene.gltf(filepath=str(path))
    meshes=obj_index()
    for (actor,slot),obj in meshes.items():
        mods=[m for m in obj.modifiers if m.type=="ARMATURE"]
        if len(mods)!=1 or mods[0].object is None:
            raise ValueError("SLOT_MISSING_SKIN_MODIFIER:"+actor+":"+slot)
        if len(mods[0].object.data.bones)!=35:
            raise ValueError("EXPECTED_35_JOINT_ARMATURE")
        if slot in GARMENTS:
            if not obj.data.vertices or not obj.data.polygons:
                raise ValueError("GARMENT_EMPTY_GEOMETRY")
            for v in obj.data.vertices:
                assignments=[g.weight for g in v.groups]
                if not assignments or not all(math.isfinite(x) and x>=0 for x in assignments):
                    raise ValueError("MISSING_OR_BAD_SKIN_WEIGHT")
                if abs(sum(assignments)-1)>2e-3:
                    raise ValueError("NONNORMALIZED_SKIN_WEIGHT")
    sample={}
    for actor in ACTORS:
        for slot in GARMENTS:
            obj=meshes[(actor,slot)]
            # Evaluated coordinate indices preserve topology for Armature deforms.
            edges=[(e.vertices[0],e.vertices[1]) for e in obj.data.edges]
            if not edges:raise ValueError("GARMENT_NO_EDGES")
            stride=max(1,len(edges)//750)
            sample[(actor,slot)]=(obj,edges[::stride])
    byrole={actor:{} for actor in ACTORS}
    strain_samples={key:[] for key in sample}
    largest={key:0. for key in sample}
    baseline={}
    for frame in range(1,frames+1):
        bpy.context.scene.frame_set(frame)
        graph=bpy.context.evaluated_depsgraph_get()
        for key,(obj,edges) in sample.items():
            vertices=evaluated_vertices(obj,graph)
            if frame==1:
                baseline[key]=[math.dist(vertices[a],vertices[b]) for a,b in edges]
                if any(x<=1e-8 for x in baseline[key]):
                    raise ValueError("DEGENERATE_GARMENT_EDGE")
            if len(vertices)!=len(obj.data.vertices):
                raise ValueError("DEFORMATION_TOPOLOGY_CHANGED")
            for (a,b),rest in zip(edges,baseline[key]):
                ratio=math.dist(vertices[a],vertices[b])/rest
                if not math.isfinite(ratio):
                    raise ValueError("NONFINITE_EDGE_STRAIN")
                excess=abs(ratio-1.)
                strain_samples[key].append(excess)
                largest[key]=max(largest[key],excess)
    for actor in ACTORS:
        for slot in GARMENTS:
            values=sorted(strain_samples[(actor,slot)])
            p99=values[min(len(values)-1,math.ceil(.99*len(values))-1)]
            byrole[actor][slot]={
                "frames_evaluated":frames,
                "observed_edge_samples":len(values),
                "p99_absolute_relative_edge_strain":round(p99,5),
                "max_absolute_relative_edge_strain":round(largest[(actor,slot)],5),
                "skin_vertex_count":len(sample[(actor,slot)][0].data.vertices),
                "scientific_verdict":"FAIL_PROXY_STRETCH_OVER_25PCT"
                   if p99>.25 else "UNKNOWN_PROXY_ONLY"}
    report={
      "schema":"scp.r009.original_wardrobe_native_deformation.v2",
      "source_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
      "frames_sampled":frames,
      "all_slots_shared_35_joint_rig":True,
      "results":byrole,
      "garment_body_penetration":"UNKNOWN_NOT_MEASURED",
      "human_motion_and_cloth_fit_accepted":False,
      "native_blender_structural_verdict":"PASS",
      "rights_release_merge_cpe_held":True}
    receipt.parent.mkdir(parents=True,exist_ok=True)
    receipt.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--receipt",required=True)
    opts=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    output=audit(opts.input,opts.receipt)
    print(json.dumps({"schema":output["schema"],"verdict":
        output["native_blender_structural_verdict"],
        "human_accepted":False},sort_keys=True))
