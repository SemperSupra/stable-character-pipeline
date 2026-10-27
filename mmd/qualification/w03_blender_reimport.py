#!/usr/bin/env python3
"""W03 true Blender 4.5 glTF reimport, separate from MMD Tools GLB exporter.

No PMX parser/solver is involved. Each sample is from ORIGINAL self-authored
G7/G9 GLB bytes; inspect actual imported mesh/skinning/morph/action/eval state.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--g7",type=Path,required=True)
    ap.add_argument("--g9",type=Path,required=True)
    ap.add_argument("--reference",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    a=ap.parse_args()
    import bpy
    assert bpy.app.version >= (4,5,0),bpy.app.version_string
    a.out.mkdir(parents=True,exist_ok=True)
    origin=json.loads(a.reference.read_text())
    assets={x["file"]:x for x in origin["assets"]}
    allrows=[]
    for kind,source in (("g7",a.g7),("g9",a.g9)):
        raw=source.read_bytes()
        name=source.name
        assert name in assets and sha(raw)==assets[name]["sha256"]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        outcome=bpy.ops.import_scene.gltf(filepath=str(source.resolve()),bone_heuristic="BLENDER")
        assert "FINISHED" in outcome,outcome
        objects=list(bpy.context.scene.objects)
        meshes=[o for o in objects if o.type=="MESH"]
        rigs=[o for o in objects if o.type=="ARMATURE"]
        assert meshes and rigs,(kind,[o.type for o in objects])
        for rig in rigs:
            assert len(rig.data.bones)>0,"empty imported armature"
        skinned=[o for o in meshes if any(m.type=="ARMATURE" for m in o.modifiers)]
        shape_targets=sum(max(0,len(o.data.shape_keys.key_blocks)-1)
             for o in meshes if o.data.shape_keys is not None)
        actual_animation_count=len(bpy.data.actions)
        if not skinned or not actual_animation_count:
            raise AssertionError(f"{kind}: independent Blender import lost ARMATURE skin modifier or animation")
        if kind=="g9" and shape_targets<2:
            raise AssertionError(f"{kind}: glTF morph targets absent after real Blender reimport: {shape_targets}")
        # Observe *actual evaluated mesh positions* at source samples. This
        # avoids claiming that glTF animation merely exists because a file loaded.
        scene=bpy.context.scene
        scene.render.fps=30
        frames={}
        for frame in (0,15,30):
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            deps=bpy.context.evaluated_depsgraph_get()
            positions=[]
            for obj in meshes:
                evaluated=obj.evaluated_get(deps)
                mesh=evaluated.to_mesh()
                try:
                    world=evaluated.matrix_world
                    for v in mesh.vertices:
                        p=world @ v.co
                        positions.append([float(p.x),float(p.y),float(p.z)])
                finally:
                    evaluated.to_mesh_clear()
            assert positions and all(math.isfinite(x) for p in positions for x in p)
            frames[str(frame)]={"vertex_positions":len(positions),
                "bounds_min":[min(p[d] for p in positions) for d in range(3)],
                "bounds_max":[max(p[d] for p in positions) for d in range(3)],
                "checksum_sha256":sha(json.dumps(positions,sort_keys=True).encode())}
        # Tight vertex-order registration may change across engines; report
        # observed positions/counters only, do not fake world-space equality.
        row={"kind":kind,"file":name,"source_sha256":sha(raw),
             "reader":"Blender bpy.ops.import_scene.gltf",
             "reader_version":bpy.app.version_string,
             "mesh_objects":len(meshes),"armatures":len(rigs),
             "skinned_mesh_objects":len(skinned),
             "bone_counts":[len(r.data.bones) for r in rigs],
             "morph_targets":shape_targets,"actions":actual_animation_count,
             "evaluated_frame_meshes":frames,
             "status":"PASS_REIMPORTED_STRUCTURAL_AND_EVALUATION_OBSERVED",
             "not_qualified":["pixel/rig space direct parity against source",
                 "independent renderer presentation","native MMD CCD or Bullet contact"]}
        allrows.append(row)
        bpy.ops.wm.save_as_mainfile(filepath=str((a.out/(kind+"_reimport.blend")).resolve()))
        print("W03_BLENDER_REIMPORT",json.dumps(row,sort_keys=True),flush=True)
    report={"schema":"scp.mmd.w03-blender-gltf.v1","status":"PASS_BLENDER_REIMPORT_ONLY",
            "inputs":allrows}
    (a.out/"blender_reimport.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")

if __name__=="__main__":
    try: main()
    except BaseException:
        import traceback
        traceback.print_exc()
        sys.stdout.flush();sys.stderr.flush();os._exit(1)
    sys.stdout.flush();sys.stderr.flush();os._exit(0)
