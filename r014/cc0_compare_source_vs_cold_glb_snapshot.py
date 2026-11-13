"""Dump actual native Blender evaluated human meshes for source↔GLB parity.

Runs in two separate fresh Blender processes: author source .blend vs
reimported GLB's new independent .blend. Never substitutes GLB JSON or author
metadata for actual evaluated body/attachment surfaces.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--sex",choices=("male","female"),required=True)
    p.add_argument("--mode",choices=("source","import"),required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    assert Path(bpy.data.filepath).resolve()==a.source.resolve()
    body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
    rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
    assert body.type=="MESH" and rig.type=="ARMATURE"
    assert len(rig.data.bones)==163
    actor_names=[o.name for o in bpy.data.objects if o.type=="MESH" and
                 o.name.startswith("R014_"+a.sex+"_textured_body")]
    assert len(actor_names)>=7
    def measured(obj,limit=None):
        deps=bpy.context.evaluated_depsgraph_get()
        ev=obj.evaluated_get(deps)
        mesh=ev.to_mesh()
        try:
            world=ev.matrix_world
            verts=[world@v.co for v in mesh.vertices]
            chosen=verts
            if limit is not None and len(verts)>limit:
                indices=sorted({int(round(i*(len(verts)-1)/(limit-1))) for i in range(limit)})
                chosen=[verts[i] for i in indices]
            # Triangulated actual world-space face area, no proxy bbox circumference.
            area=0.0
            for poly in mesh.polygons:
                ids=[int(i) for i in poly.vertices]
                for j in range(1,len(ids)-1):
                    area+=((verts[ids[j]]-verts[ids[0]]).cross(verts[ids[j+1]]-verts[ids[0]])).length/2
            return {
              "sample_count":len(chosen),"evaluated_vertices":len(verts),
              "evaluated_faces":len(mesh.polygons),
              "actual_world_surface_area_blender_squared":round(area,9),
              "bounds_xyz_native": [round(max(float(v[k]) for v in verts)-min(float(v[k]) for v in verts),9) for k in range(3)],
              "coords_world":[[round(float(x),9) for x in v] for v in chosen],
              "material_count":len(mesh.materials),
              "nonzero_shape_keys":[{"name":key.name,"weight":round(float(key.value),7)}
                   for key in obj.data.shape_keys.key_blocks if abs(float(key.value))>1e-7]
                   if obj.data.shape_keys else []
            }
        finally:ev.to_mesh_clear()
    if a.mode=="source":
        frames=[1,8]
    else:
        frames=[2,17]
    records=[]
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        objects={}
        for name in sorted(actor_names):
            obj=bpy.data.objects[name]
            objects[name]=measured(obj,limit=None if obj==body else 512)
        records.append({"frame":frame,"objects":objects})
    result={"schema":"r014.source_to_portable_glb_actual_spatial_mesh.v1",
            "source_path":a.source.name,"sex":a.sex,"stage":a.mode,
            "source_blender_version":bpy.app.version_string,
            "source_armature_bones":len(rig.data.bones),
            "actors":len(actor_names),"frames":records,
            "scope":"actual native Blender evaluated spatial mesh, source vs GLB imported, still not anatomical or cinematic acceptance",
            "merge_release":"HOLD"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,separators=(",",":"),sort_keys=True)+"\n",encoding="utf8")
    print("R014_SOURCE_VS_GLTF_GEOMETRY",json.dumps({"sex":a.sex,"stage":a.mode,"actors":len(actor_names),"body_vertices":[r["objects"][body.name]["evaluated_vertices"] for r in records],"body_surface":[r["objects"][body.name]["actual_world_surface_area_blender_squared"] for r in records]},sort_keys=True))
if __name__=="__main__":main()
