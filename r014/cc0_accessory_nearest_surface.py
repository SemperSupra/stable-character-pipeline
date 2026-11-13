"""R014 source-matched CC0 attachment geometry / body-surface proximity audit.

This is a diagnostic based on *actual* evaluated Blender meshes and nearest
body surface. It is NOT a watertight signed collision/intersection oracle; the
normal-side flag is explicitly provisional. Compare actual baseline and
shape-morphed packed scenes with independent fresh Blender processes.
"""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils.bvhtree import BVHTree
from mathutils import Vector

def hash_file(f):
    s=sha256()
    with open(f,"rb") as handle:
        for part in iter(lambda:handle.read(1<<20),b""):s.update(part)
    return s.hexdigest()

def anc(obj,root):
    seen=set()
    while obj and obj.name not in seen:
        if obj is root:return True
        seen.add(obj.name)
        obj=obj.parent
    return False

def co_world(obj, mesh, limit=512):
    verts=mesh.vertices
    if not verts:return []
    idx=sorted({int(i*(len(verts)-1)/(min(len(verts),limit)-1)) for i in range(min(len(verts),limit))}) if len(verts)>1 else [0]
    return [obj.matrix_world@verts[i].co for i in idx]

def material_provenance(obj):
    return [{"name":m.name if m else None,"use_nodes":bool(m and m.use_nodes)}
            for m in obj.data.materials]

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--scene",type=Path,required=True)
    pa.add_argument("--sex",choices=("female","male"),required=True)
    pa.add_argument("--stage",choices=("original","morphed"),required=True)
    pa.add_argument("--out",type=Path,required=True)
    args=pa.parse_args(sys.argv[sys.argv.index("--")+1:])
    assert Path(bpy.data.filepath).resolve()==args.scene.resolve(),"INCORRECT_SOURCE_SCENE"
    sex=args.sex
    src_name="R014_"+sex+"_textured_body"
    rig_name="R014_"+sex+"_textured_rig"
    body=bpy.data.objects[src_name];rig=bpy.data.objects[rig_name]
    assert body.type=="MESH" and rig.type=="ARMATURE"
    assert len(body.data.vertices)==19158 and len(rig.data.bones)==163
    assert len([m for m in body.modifiers if m.type=="ARMATURE" and m.object==rig])==1
    scene=bpy.context.scene
    scene.frame_set(1);bpy.context.view_layer.update()
    dep=bpy.context.evaluated_depsgraph_get()
    body_obj=body.evaluated_get(dep)
    body_mesh=body_obj.to_mesh()
    try:
        assert len(body_mesh.vertices)>10000
        tree=BVHTree.FromPolygons([v.co[:] for v in body_mesh.vertices],
                    [[int(x) for x in p.vertices] for p in body_mesh.polygons],
                    all_triangles=False,epsilon=1e-7)
        inverse=body.matrix_world.inverted_safe()
        report={
          "schema":"r014.cc0.attachment_native_proximity.v1",
          "status":"EVIDENCE_UNDECIDED",
          "source_scene":args.scene.name,"source_scene_sha256":hash_file(args.scene),
          "stage":args.stage,"sex_macro":sex,"body_evaluated_vertices":len(body_mesh.vertices),
          "body_raw_vertices":len(body.data.vertices),"rig_bones":len(rig.data.bones),
          "evaluated_frame":1,"method":"Bvhtree nearest original evaluated body polygon; each attachment sampled in world coordinates then converted to body local. Normal-side is NOT a robust inside/outside volume test",
          "attached_meshes":[],"inventory":[],"material_count":len(body.data.materials),
          "unvalidated":["no watertight volume test","no deforming hair cards to scalp test",
                         "not a comprehensive collision solver","no verified cinematic appearance",
                         "no physical body cm calibration","no functional eyes/teeth/lashes QA"],
          "merge_release":"HOLD",
        }
        for obj in sorted(bpy.data.objects,key=lambda x:x.name):
            if obj.type not in {"MESH","CURVE","CURVES"}:
                continue
            is_related=bool(obj is body or obj.name.startswith("R014_"+sex+"_")
                            or anc(obj,rig) or anc(obj,body))
            report["inventory"].append({"name":obj.name,"type":obj.type,
                "related_to_actor":is_related,"parent":obj.parent.name if obj.parent else None})
            if obj is body or obj.type!="MESH" or not is_related:continue
            eval_obj=obj.evaluated_get(dep)
            evaluated=eval_obj.to_mesh()
            try:
                if len(evaluated.vertices)==0:continue
                pts=co_world(eval_obj,evaluated,limit=512)
                distances=[];side=[]
                for v in pts:
                    closest=tree.find_nearest(inverse@v)
                    if closest[0] is None:continue
                    pos,normal,_,distance=closest
                    distances.append(float(distance))
                    side.append(float((inverse@v-pos).dot(normal)))
                assert distances,"RELATED_ASSET_EMPTY_OR_INVALID_BODY_BVH"
                report["attached_meshes"].append({
                   "name":obj.name,"parent":obj.parent.name if obj.parent else None,
                   "sampled_evaluated_vertices":len(distances),
                   "total_evaluated_vertices":len(evaluated.vertices),
                   "evaluated_world_centroid":[round(float(sum(p[i] for p in pts)/len(pts)),6) for i in range(3)],
                   "mean_nearest_body_distance_native":round(float(sum(distances)/len(distances)),7),
                   "minimum_nearest_body_distance_native":round(float(min(distances)),7),
                   "count_surface_distance_below_0_005_native":sum(d<0.005 for d in distances),
                   "count_normal_side_negative_provisional":sum(x<0 for x in side),
                   "material_provenance":material_provenance(obj)
                })
            finally:eval_obj.to_mesh_clear()
        report["related_candidate_meshes"]=len(report["attached_meshes"])
        report["status"]="PASS_SOURCE_NATIVE_ATTACHED_MESH_GEOMETRY_DIAGNOSTIC_ONLY" if report["attached_meshes"] else "UNKNOWN_NO_MESH_ACCESSORIES_MATCHED"
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        print("R014_ACCESSORY_GEOMETRY",json.dumps({
           "stage":args.stage,"sex_macro":sex,"status":report["status"],
           "related_candidate_meshes":report["related_candidate_meshes"],
           "names":[v["name"] for v in report["attached_meshes"]],
           "body_faces":len(body_mesh.polygons)},sort_keys=True))
    finally:body_obj.to_mesh_clear()

if __name__=="__main__":main()
