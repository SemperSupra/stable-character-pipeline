"""Public-safe, independent Blender STL->GLB and fresh-process GLB->scene probe."""
import bpy
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

def args():
    return sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []

def report(mesh, marker):
    verts=[]
    # World-space positions: GLB export/import can change node axes but must preserve positions.
    for v in mesh.data.vertices:
        p=mesh.matrix_world @ v.co
        if not all(math.isfinite(float(t)) for t in p):
            raise RuntimeError("NONFINITE_COORDINATE")
        verts.append(tuple(round(float(t),6) for t in p))
    tri=len(mesh.data.polygons)
    bound=[[min(x[i] for x in verts) for i in range(3)],
           [max(x[i] for x in verts) for i in range(3)]]
    data={"stage":marker,"triangles":tri,"vertices":len(verts),"bounds":bound,
          "sorted_positions_sha256":hashlib.sha256(json.dumps(sorted(verts),sort_keys=True).encode()).hexdigest()}
    return data

a=args()
if len(a)!=4: raise RuntimeError("usage: phase source.stl output.glb report.json")
phase,src,glb,rec=a
bpy.ops.wm.read_factory_settings(use_empty=True)
if phase=="export":
    bpy.ops.wm.stl_import(filepath=src)
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    if len(meshes)!=1: raise RuntimeError(f"EXPECTED_ONE_STL_MESH got {len(meshes)}")
    source_mesh=meshes[0]
    before=report(source_mesh,"STL_IMPORTED")
    bpy.ops.object.select_all(action="DESELECT")
    source_mesh.select_set(True)
    bpy.context.view_layer.objects.active=source_mesh
    bpy.ops.export_scene.gltf(filepath=glb,export_format="GLB",use_selection=True,
                              export_yup=True)
    if not Path(glb).is_file() or Path(glb).stat().st_size<100:
        raise RuntimeError("GLB_MISSING")
    result={"phase":"export","source_stl_sha256":hashlib.sha256(Path(src).read_bytes()).hexdigest(),
            "source":before,"glb_sha256":hashlib.sha256(Path(glb).read_bytes()).hexdigest()}
elif phase=="reimport":
    if not Path(glb).is_file(): raise RuntimeError("GLB_NOT_FOUND")
    bpy.ops.import_scene.gltf(filepath=glb)
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    if len(meshes)!=1: raise RuntimeError(f"EXPECTED_ONE_GLTF_MESH got {len(meshes)}")
    result={"phase":"reimport","mesh":report(meshes[0],"FRESH_GLB_IMPORTED"),
            "glb_sha256":hashlib.sha256(Path(glb).read_bytes()).hexdigest()}
else: raise RuntimeError("UNSUPPORTED_PHASE")
Path(rec).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("BLENDER_STL_GLB_"+phase.upper()+"_PASS",json.dumps(result,sort_keys=True))
