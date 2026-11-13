"""Independent source-native CC0 morphology attachment transfer topology/UV/material audit.

Execute in two different clean Blender processes on pre-transfer and corrected
native .blend. Check source identities, packed source images and geometrical
data contract. This is not a claim of collision-free or photoreal asset quality.
"""
import argparse
from hashlib import sha256
import json
import math
import struct
import sys
from pathlib import Path
import bpy

def sha_file(path):
    h=sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def digest_coords(points,prec="!d"):
    h=sha256()
    for v in points:
        for x in v: h.update(struct.pack(prec,float(x)))
    return h.hexdigest()

def digest_ints(rows):
    h=sha256()
    for row in rows:
        for x in row:h.update(struct.pack("!q",int(x)))
        h.update(b";")
    return h.hexdigest()

def ancestry(obj,root):
    while obj is not None:
        if obj==root:return True
        obj=obj.parent
    return False

def evaluate(obj):
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    try:
        return {
            "vertices":len(mesh.vertices),
            "faces":len(mesh.polygons),
            "actual_evaluated_world_vertex_hash":digest_coords(
                 (evaluated.matrix_world@v.co for v in mesh.vertices),prec="!f")
        }
    finally:evaluated.to_mesh_clear()

def snapshot(scene_path,sex):
    if Path(bpy.data.filepath).resolve()!=scene_path.resolve():raise RuntimeError("SOURCE_SCENE_MISMATCH")
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    rig=bpy.data.objects["R014_"+sex+"_textured_rig"]
    body=bpy.data.objects["R014_"+sex+"_textured_body"]
    assert body.type=="MESH" and rig.type=="ARMATURE"
    assert len(rig.data.bones)==163 and len(body.data.vertices)==19158
    images=[]
    for img in bpy.data.images:
        if img.source!="FILE":continue
        packed=img.packed_file
        if packed is not None:
            data=bytes(packed.data)
            images.append({"name":img.name,"sha256":sha256(data).hexdigest(),"bytes":len(data)})
    assert len(images)>=10,"PACKED_CC0_MEDIA_MISSING"
    meshes={}
    for obj in sorted(bpy.data.objects,key=lambda o:o.name):
        if obj.type!="MESH":continue
        if not (obj==body or obj.name.startswith("R014_"+sex+"_") or ancestry(obj,rig)):continue
        mesh=obj.data
        verts=mesh.vertices
        polygon_vertex_counts=[len(f.vertices) for f in mesh.polygons]
        uv={}
        for layer in mesh.uv_layers:
            uv[layer.name]={"loops":len(layer.data),
                            "uv_data_sha256":digest_coords((corner.uv for corner in layer.data))}
        keynames=[]
        if mesh.shape_keys is not None:
            keynames=[{"name":key.name,"num_vertices":len(key.data)}
                      for key in mesh.shape_keys.key_blocks]
        material_names=[m.name if m else None for m in mesh.materials]
        modifiers=[{"type":m.type,"name":m.name,
                    "armature":m.object.name if m.type=="ARMATURE" and m.object else None}
                   for m in obj.modifiers]
        weights=[]
        for vertex in verts:
            weights.append([(g.group,round(float(g.weight),8)) for g in sorted(vertex.groups,key=lambda g:g.group)])
        weight_digest=sha256(json.dumps(weights,separators=(",",":")).encode()).hexdigest()
        meshes[obj.name]={
            "name":obj.name,"is_body":obj==body,
            "parent":obj.parent.name if obj.parent else None,
            "object_type":obj.type,
            "raw_vertices":len(verts),"raw_edges":len(mesh.edges),
            "raw_polygons":len(mesh.polygons),"loops":len(mesh.loops),
            "polygon_index_layout_sha256":digest_ints(f.vertices for f in mesh.polygons),
            "material_index_layout_sha256":digest_ints(([f.material_index] for f in mesh.polygons)),
            "material_slots":material_names,
            "modifiers":modifiers,
            "vertex_group_names":[g.name for g in obj.vertex_groups],
            "weights_sha256_rounded_8":weight_digest,
            "uv_layers":uv,
            "shape_key_schema":keynames,
            "actual_evaluated_geometry":evaluate(obj)
        }
    return {
        "source":"official original CC0 MPFB+MAKESKIN research",
        "native_blend_sha256":sha_file(scene_path),
        "source_scene_name":scene_path.name,
        "sex_macro":sex,"frame":1,
        "blender":bpy.app.version_string,
        "rig_bones":len(rig.data.bones),
        "source_body_raw_vertices":len(body.data.vertices),
        "packed_images":sorted(images,key=lambda x:x["name"]),
        "meshes":meshes,
        "quality_state":"HOLD_ANATOMY_AND_CINEMATIC"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--mode",choices=["snapshot"],required=True)
    p.add_argument("--sex",choices=["female","male"],required=True)
    p.add_argument("--scene",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    result=snapshot(args.scene,args.sex)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("R014_UV_MATERIAL_SNAPSHOT",json.dumps({"sex":args.sex,"source":result["source_scene_name"],"meshes":len(result["meshes"]),"packed":len(result["packed_images"]),"sha256":result["native_blend_sha256"]},sort_keys=True))
if __name__=="__main__":main()
