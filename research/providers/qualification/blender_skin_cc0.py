"""Real Blender CC0 two-joint skin and animation round-trip; no character identity."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

import bpy

def source_times(g, root):
    a = g["accessors"][g["animations"][0]["samplers"][0]["input"]]
    view = g["bufferViews"][a["bufferView"]]
    assert a["componentType"] == 5126 and a["type"] == "SCALAR"
    raw = (root / g["buffers"][view["buffer"]]["uri"]).read_bytes()
    times = struct.unpack_from("<" + str(a["count"]) + "f", raw, view.get("byteOffset", 0) + a.get("byteOffset", 0))
    assert len(times) == 12 and all(math.isfinite(x) for x in times)
    return min(times), max(times)

def snapshot(frame):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    meshes = sorted((obj for obj in bpy.data.objects if obj.type == "MESH"), key=lambda x:x.name)
    rigs = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    print("SIMPLE_SKIN_DIAGNOSTIC", json.dumps({
        "object_types": [{"name":obj.name,"type":obj.type} for obj in bpy.data.objects],
        "mesh_count":len(meshes),
        "armatures":[{"name":obj.name,"bones":[bone.name for bone in obj.data.bones]} for obj in rigs],
        "mesh_modifiers":[{"name":obj.name,"mods":[mod.type for mod in obj.modifiers],
                          "vertex_groups":[group.name for group in obj.vertex_groups]} for obj in meshes],
        "action_count":len(bpy.data.actions)
    }),flush=True)
    assert len(meshes)==1 and len(rigs)==1 and len(rigs[0].data.bones)>=2, "genuine joint skin not imported"
    dep = bpy.context.evaluated_depsgraph_get()
    obj = meshes[0].evaluated_get(dep)
    mesh = obj.to_mesh()
    try:
        points = [tuple(float(v) for v in obj.matrix_world @ vertex.co) for vertex in mesh.vertices]
    finally:
        obj.to_mesh_clear()
    assert len(points)==10
    return points

def max_delta(a,b):
    assert len(a)==len(b)
    return max(max(abs(x-y) for x,y in zip(av,bv)) for av,bv in zip(a,b))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    src=Path(args.source).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    assert bpy.app.version>=(4,5,0)
    assert "Creative Commons Zero v1.0 Universal" in (src/"README.md").read_text()
    gltf=src/"SimpleSkin.gltf"
    g=json.loads(gltf.read_text())
    assert g["asset"]["version"]=="2.0" and len(g["skins"])==1 and len(g["skins"][0]["joints"])==2
    assert len(g["animations"])==1
    for b in g["buffers"]:
        assert (src/b["uri"]).stat().st_size==b["byteLength"]
    start,end=source_times(g,src)
    frames=sorted(set(int(round(24*t)) for t in [start,(start+end)/2,end]))
    assert len(frames)==3

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=24
    assert "FINISHED" in bpy.ops.import_scene.gltf(filepath=str(gltf))
    assert len(bpy.data.actions)>=1
    original=[snapshot(f) for f in frames]
    assert max_delta(original[0],original[1])>0.0001 or max_delta(original[1],original[2])>0.0001, "skin not deforming"
    blend=out/"SimpleSkin.blend"
    glb=out/"SimpleSkin.glb"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    assert "FINISHED" in bpy.ops.export_scene.gltf(filepath=str(glb),export_format="GLB",export_animations=True)
    raw=glb.read_bytes()
    assert raw[:4]==b"glTF" and struct.unpack_from("<I",raw,8)[0]==len(raw)
    n=struct.unpack_from("<I",raw,12)[0]
    exported=json.loads(raw[20:20+n])
    assert len(exported.get("skins",[]))==1 and len(exported.get("animations",[]))>=1 and len(exported.get("meshes",[]))==1

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=24
    assert "FINISHED" in bpy.ops.import_scene.gltf(filepath=str(glb))
    assert len(bpy.data.actions)>=1
    replay=[snapshot(f) for f in frames]
    errors=[max_delta(a,b) for a,b in zip(original,replay)]
    assert max(errors)<0.01, f"skinned mesh deform parity exceeded 0.01 units: {errors}"
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    receipt={
     "schema":"scp.real_cc0_skinned_roundtrip.v1",
     "blender":bpy.app.version_string,
     "source":"Khronos glTF-Sample-Assets SimpleSkin CC0 by Marco Hutter",
     "upstream_commit":"8f492390ddc7a2ae221a1369ef560589cf8c70fb",
     "source_sha256":sha(gltf),"blend_sha256":sha(blend),"glb_sha256":sha(glb),
     "source_skin_joint_count":2,
     "reimported_skin_count":len(exported["skins"]),
     "reimported_animations":len(exported["animations"]),
     "frames":frames,
     "source_motion_delta":max_delta(original[0],original[1]),
     "reimported_max_vertex_coordinate_error":max(errors),
     "limitations":"2-bone original CC0 geometry, not a person, full-body rig, VMD/PMX, BVH or MMD parity"
    }
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
