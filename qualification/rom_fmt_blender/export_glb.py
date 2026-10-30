"""ROMFMT D: actual native Blender GLB exporter roundtrip, no assumed joint ROM enforcement.

Source original two-bone armature + skinned mesh. Export included custom
properties. Independently decode GLB JSON, inspect real skin hierarchy and
specific notes lost or retained. Does NOT transfer Blender solver constraints.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import bpy
from native_blend import build,check

MAX_BINARY=8*1024*1024

def decode_glb(p):
    raw=Path(p).read_bytes()
    if len(raw)<20 or len(raw)>MAX_BINARY or raw[:4]!=b"glTF":
        raise ValueError("GLB_BINARY_NOT_ADMITTED")
    version,total=struct.unpack_from("<II",raw,4)
    sz,kind=struct.unpack_from("<II",raw,12)
    if version!=2 or total!=len(raw) or kind!=0x4e4f534a or sz%4 or 20+sz>len(raw):
        raise ValueError("GLB_JSON_HEADER_MISMATCH")
    return json.loads(raw[20:20+sz].decode("utf-8"))

def verify_export(blob,expected):
    nodes=blob.get("nodes",[])
    skins=blob.get("skins",[])
    if not skins:
        raise ValueError("ACTUAL_GLTF_SKIN_NOT_EXPORTED")
    names={n.get("name"):i for i,n in enumerate(nodes)}
    skin_indices={i for skin in skins for i in skin.get("joints",[])}
    bones=[(i,n) for i,n in enumerate(nodes) if i in skin_indices and
           "OriginalLower" in str(n.get("name",""))]
    if not bones:
        raise ValueError("ACTUAL_GLTF_SKIN_JOINT_LOST_OR_RENAMED")
    found=[]
    for node in nodes:
        value=node.get("extras",{}).get("scp_rom_source_annotation")
        if value is None:
            continue
        if not isinstance(value,str) or json.loads(value)!=expected:
            raise ValueError("ACTUAL_GLTF_ANNOTATION_CHANGED")
        found.append(node.get("name",""))
    if not found:
        raise ValueError("ACTUAL_GLTF_EXTRAS_DROPPED")
    joint_has_annotation=bool(bones[0][1].get("extras",{}).get("scp_rom_source_annotation"))
    return {"joints":len(skin_indices),"metadata_nodes":found,
            "lower_joint_extra_survives":joint_has_annotation,
            "source_mesh_or_armature_annotation_survives":True,
            "native_blender_constraint_export":"NOT_ASSUMED",
            "source_authoritative_joint_mapping":"NEEDS_EXTERNAL_JOIN_IF_BONE_EXTRAS_MISSING"}

def run(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    blend=folder/"romfmt_gltf_original_source.blend"
    source=build(blend)
    arm,lower,c=check(blend,source)
    # Make an actual skinned mesh so glTF exports the real armature hierarchy.
    bpy.ops.mesh.primitive_cube_add(size=.25,location=(0,0,1.25))
    mesh=bpy.context.object
    mesh.name="Original_Source_Mesh"
    group=mesh.vertex_groups.new(name="OriginalLower")
    group.add(list(range(len(mesh.data.vertices))),1.0,"REPLACE")
    mod=mesh.modifiers.new(name="OriginalArmatureSkin",type="ARMATURE")
    mod.object=arm
    mesh.parent=arm
    source_json=json.dumps(source,sort_keys=True,separators=(",",":"))
    mesh["scp_rom_source_annotation"]=source_json
    mesh["scp_rom_sha256"]=hashlib.sha256(source_json.encode()).hexdigest()
    glb=folder/"original_annotated_skin.glb"
    if not hasattr(bpy.ops.export_scene,"gltf"):
        raise ValueError("NATIVE_GLTF_EXPORTER_NOT_AVAILABLE")
    outcome=bpy.ops.export_scene.gltf(filepath=str(glb.resolve()),export_format="GLB",
                                     export_extras=True,export_animations=False)
    if "FINISHED" not in outcome:
        raise ValueError("NATIVE_GLTF_EXPORTER_FAILED")
    blob=decode_glb(glb)
    witness=verify_export(blob,source)
    # Hostile negative check of decoded asset, not just a self-reported receipt.
    tampered=json.loads(json.dumps(blob))
    for node in tampered.get("nodes",[]):
        if "scp_rom_source_annotation" in node.get("extras",{}):
            node["extras"].pop("scp_rom_source_annotation")
    try:
        verify_export(tampered,source)
    except ValueError as err:
        if str(err)!="ACTUAL_GLTF_EXTRAS_DROPPED":
            raise
    else:
        raise ValueError("EXTRAS_LOSS_FALSE_PASS")
    result={"schema":"scp.rom.blender_to_gltf.v1",
            "status":"PASS_ACTUAL_NATIVE_GLTF_ASSET_METADATA_ONLY",
            "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "glb_sha256":hashlib.sha256(glb.read_bytes()).hexdigest(),
            "blend_original_before_mesh_sha256":hashlib.sha256(blend.read_bytes()).hexdigest(),
            "mesh_source_annotation_sha256":hashlib.sha256(source_json.encode()).hexdigest(),
            "witness":witness,"hostile_extras_loss":"REJECTED",
            "biological_anatomy":"UNKNOWN_NOT_A_HUMAN",
            "runtime_joint_constraint_enforcement":"NOT_PROVEN"}
    (folder/"blender_glb_export_receipt.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("ROMFMT_ACTUAL_GLTF_EXPORT",json.dumps(result,sort_keys=True))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    run(p.parse_args().out)
