#!/usr/bin/env python3
"""Independent native Blender import witness for strict source-original mage wardrobe GLBs."""
import hashlib
import json
import sys
from pathlib import Path

import bpy

ACTORS=("AsterOriginal","JuniperOriginal")

def witness(source,receipt_path,expected_sha,choices_json):
    source=Path(source)
    actual_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    if actual_sha!=expected_sha:
        raise RuntimeError("STRICT_NATIVE_SHA_MISMATCH")
    choices=json.loads(choices_json)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))
    arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    if len(arms)!=2 or any(len(a.data.bones)!=35 for a in arms):
        raise RuntimeError("STRICT_NATIVE_RIG_MISMATCH")
    meshes=[o for o in bpy.data.objects if o.type=="MESH"
            and "_Wardrobe_" in o.name]
    labels={}
    for actor in ACTORS:
        slots=sorted(o.name.split("_Wardrobe_",1)[1].split(".")[0]
                     for o in meshes if o.name.startswith(actor+"_Wardrobe_"))
        labels[actor]=slots
    presets={
      "unclothed":{"body","hair"},
      "signature":{"body","hair","top","bottom","footwear","accessory"},
      "alternate":{"body","hair","alt_top","alt_bottom","footwear"},
      "adventure":{"body","hair","style_top","style_bottom","footwear","accessory"}
    }
    if set(choices)!=set(ACTORS):
        raise RuntimeError("STRICT_NATIVE_ACTOR_CHOICES")
    for actor in ACTORS:
        if choices[actor] not in presets:
            raise RuntimeError("STRICT_NATIVE_UNKNOWN_PRESET")
        expected=set(presets[choices[actor]])
        if actor=="JuniperOriginal":expected.discard("accessory")
        if set(labels[actor])!=expected:
            raise RuntimeError("STRICT_NATIVE_INACTIVE_LEAK:"+actor+
                               ":found="+repr(labels[actor])+
                               ":expected="+repr(sorted(expected)))
    if any("ARMATURE" not in [m.type for m in obj.modifiers] for obj in meshes):
        raise RuntimeError("STRICT_NATIVE_UNSKINNED")
    result={
      "schema":"scp.r009.strict_mage_blender_witness.v1",
      "source_sha256":actual_sha,
      "actors":labels,
      "expected_choices":choices,
      "native_blender_import":"PASS_STRICT_MESH_VISIBILITY_ONLY",
      "full_body_visual_accepted":False,
      "skin_collision_accepted":False,
      "animated_cloth_accepted":False,
      "armatures":{a.name:len(a.data.bones) for a in arms},
      "blender_version":bpy.app.version_string
    }
    Path(receipt_path).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    args=sys.argv[sys.argv.index("--")+1:]
    if len(args)!=4:raise SystemExit("USAGE GLB RECEIPT SHA CHOICES_JSON")
    witness(*args)
