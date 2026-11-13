"""Import candidate full source CC0 glTF into a new blank Blender process."""
import argparse
import json
import sys
from pathlib import Path
import bpy

p=argparse.ArgumentParser()
p.add_argument("--glb",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
args=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert bpy.data.filepath=="","NOT_EMPTY_IMPORT_ENVIRONMENT"
assert args.glb.exists()
bpy.ops.import_scene.gltf(filepath=str(args.glb))
arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
meshes=[o for o in bpy.data.objects if o.type=="MESH"]
assert arms and len(meshes)>=7
rig=max(arms,key=lambda o:len(o.data.bones))
assert len(rig.data.bones)>=100
assert any(any(m.type=="ARMATURE" and m.object==rig for m in o.modifiers) for o in meshes)
actions=list(bpy.data.actions)
assert actions
args.out.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(args.out))
print("R014_MASK_GLTF_COLD_IMPORT",json.dumps({
    "status":"PASS_COLD_IMPORT_STRUCTURAL_ONLY",
    "input":args.glb.name,
    "output":args.out.name,
    "meshes":len(meshes),"rig_bones":len(rig.data.bones),
    "actions":[[x.name,list(x.frame_range)] for x in actions]
},sort_keys=True))
