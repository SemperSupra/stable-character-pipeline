"""R061 native Blender glTF import semantic fingerprint for original-synthetic scene.

Invoked by: blender -b --factory-startup --python this.py -- --glb PATH --out JSON.
No source assets, coordinates, images, rigs or binaries are written outside
disposable runner scratch. A JSON with SHA/count evidence only is emitted.
"""
import argparse
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path
import bpy

MESH_NAMES=("R036_AnatomyProxy_Left","R036_AnatomyProxy_Right","R043_EditableMask_MPFB_Body")
SAMPLES=(1,12,24)

def hold(s):
    raise RuntimeError("R061_NATIVE_IMPORT_HOLD "+s)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def quant(value):
    if not math.isfinite(float(value)):hold("nonfinite native imported geometry")
    # Convert to float32 as glTF importers operate on f32 buffers, then quantize
    # at one micrometre to avoid arbitrary Python repr of harmless float noise.
    return round(struct.unpack("<f",struct.pack("<f",float(value)))[0],6)

def vector(v):
    return tuple(quant(x) for x in v)

def hashed(obj):
    return digest(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode())

def rotations(tri):
    return min((tuple(tri),tuple(tri[1:]+tri[:1]),tuple(tri[2:]+tri[:2])))

def semantic(obj):
    if obj.type!="MESH":hold("target native node not a mesh: "+obj.name)
    mesh=obj.data
    if not mesh.vertices or not mesh.polygons:hold("empty native glTF mesh")
    uv=mesh.uv_layers.active
    corner=getattr(mesh,"corner_normals",None)
    use_corner=corner is not None and len(corner)==len(mesh.loops)
    groups={}
    for v in mesh.vertices:
        weights=sorted((obj.vertex_groups[g.group].name,quant(g.weight)) for g in v.groups)
        groups[v.index]=weights
    faces=[]
    partition={"position_uv":[],"position_uv_weights":[],"position_uv_normals":[],"normal_only":[]}
    normal_diagnostic=[]
    for poly in mesh.polygons:
        if len(poly.loop_indices)!=3:hold("native glTF import did not keep triangles")
        corners=[]
        for li in poly.loop_indices:
            vi=mesh.loops[li].vertex_index
            v=mesh.vertices[vi]
            xyz=vector(v.co)
            tex=vector(uv.data[li].uv) if uv else ()
            norm=vector(corner[li].vector if use_corner else v.normal)
            # Per-corner UV/normals and per-vertex weights remain bound to the face.
            corners.append((xyz,tex,norm,tuple(groups[vi])))
        material=int(poly.material_index)
        faces.append((material,rotations(corners)))
        partition["position_uv"].append((material,rotations([(c[0],c[1]) for c in corners])))
        partition["position_uv_weights"].append((material,rotations([(c[0],c[1],c[3]) for c in corners])))
        partition["position_uv_normals"].append((material,rotations([(c[0],c[1],c[2]) for c in corners])))
        partition["normal_only"].append((material,rotations([c[2] for c in corners])))
        if obj.name in MESH_NAMES[:2]:
            ids=[(c[0],c[1],c[3]) for c in corners]
            shift=min(range(3),key=lambda i:tuple(ids[i:]+ids[:i]))
            rid=ids[shift:]+ids[:shift]
            rn=[c[2] for c in corners][shift:]+[c[2] for c in corners][:shift]
            normal_diagnostic.append({"face_key_sha256":hashed((material,rid)),
                                      "corner_normals":rn})
    faces.sort()
    for values in partition.values():values.sort()
    normal_diagnostic.sort(key=lambda x:x["face_key_sha256"])
    morph=[]
    if mesh.shape_keys:
        keys=mesh.shape_keys.key_blocks
        basis=keys[0]
        for k in keys:
            if len(k.data)!=len(mesh.vertices):hold("shape key cardinality changed")
            deltas=[(vector(mesh.vertices[i].co),vector(k.data[i].co-basis.data[i].co))
                    for i in range(len(mesh.vertices))]
            morph.append({"name":k.name,"relative_sha256":hashed(sorted(deltas))})
    vertex_attrs=sorted((vector(v.co),tuple(groups[v.index])) for v in mesh.vertices)
    pose={}
    for frame in SAMPLES:
        bpy.context.scene.frame_set(frame)
        deps=bpy.context.evaluated_depsgraph_get()
        target=obj.evaluated_get(deps)
        evaluated=target.to_mesh()
        try:
            pose[str(frame)]=hashed(sorted(vector(v.co) for v in evaluated.vertices))
        finally:
            target.to_mesh_clear()
    return {
        "node":obj.name,
        "vertex_count":len(mesh.vertices),
        "triangle_count":len(faces),
        "vertex_group_count":len(obj.vertex_groups),
        "morph_count":len(morph),
        "material_slots":len(mesh.materials),
        "has_uv":bool(uv),
        "normal_source":"CORNER" if use_corner else "VERTEX_FALLBACK",
        "world_transform_sha256":hashed([vector(row) for row in obj.matrix_world]),
        "vertex_and_skin_weights_sha256":hashed(vertex_attrs),
        "face_position_uv_normal_skin_weight_oriented_sha256":hashed(faces),
        "face_component_sha256":{key:hashed(items) for key,items in sorted(partition.items())},
        "diagnostic_corner_normals":normal_diagnostic,
        "morph_relative_sha256":hashed(morph),
        "morph_names":[m["name"] for m in morph],
        "evaluated_frame_position_sha256":pose,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--glb",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    if not Path(args.glb).is_file():hold("original or derived source GLB missing")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(args.glb))
    records=[]
    for name in MESH_NAMES:
        candidates=[o for o in bpy.data.objects if o.type=="MESH" and o.name==name]
        if len(candidates)!=1:hold("expected one native imported named mesh "+name)
        records.append(semantic(candidates[0]))
    if [r["vertex_count"] for r in records]!=[420,420,14517] or [r["triangle_count"] for r in records]!=[196,196,26756]:
        hold("native imported original synthetic geometry count drift")
    if not any(o.type=="ARMATURE" for o in bpy.data.objects):
        hold("original glTF native armature missing")
    receipt={
        "schema":"r061.native.blender.gltf-derived-parity.v1",
        "status":"PASS_NARROW_BLENDER_GLTF_IMPORT_FINGERPRINT",
        "input_glb_sha256":digest(Path(args.glb).read_bytes()),
        "blender_version":".".join(str(v) for v in bpy.app.version),
        "imported_meshes":len(records),
        "records":records,
        "limits":"Native importer geometry/UV/normals/skin/morph and posed evaluated samples at 1/12/24 only, not pixel render, full material nodes, real anatomical organ or H.264/film acceptance",
    }
    Path(args.out).write_text(json.dumps(receipt,sort_keys=True)+"\n",encoding="utf-8")
    # Raw corner vectors stay in ephemeral runner scratch, never CI logs.
    public=dict(receipt)
    public["records"]=[{k:v for k,v in row.items() if k!="diagnostic_corner_normals"}
                       for row in records]
    print("R061_NATIVE_BLENDER_GLTF_IMPORT "+json.dumps(public,sort_keys=True))

if __name__=="__main__":main()
