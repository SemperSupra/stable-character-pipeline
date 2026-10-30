"""Import the exact independently exported original-only GLB in fresh Blender.

Never claim restored Blender LIMIT_ROTATION/IK constraints when only source custom
metadata is imported. A schema+joint ID is data, not an actuator.
"""
import argparse
import hashlib
import json
from pathlib import Path
import bpy

def run(glb,source_receipt,output):
    glb=Path(glb);source_receipt=Path(source_receipt);output=Path(output)
    expected=json.loads(source_receipt.read_text())
    if expected.get("schema")!="scp.rom.blender_to_gltf.v1" or expected.get("source_rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("EXPORT_SOURCE_RIGHTS_OR_SCHEMA")
    if hashlib.sha256(glb.read_bytes()).hexdigest()!=expected.get("glb_sha256"):
        raise ValueError("NATIVE_GLB_BINARY_SHA_MISMATCH")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not hasattr(bpy.ops.import_scene,"gltf"):
        raise ValueError("NATIVE_GLB_IMPORTER_NOT_AVAILABLE")
    outcome=bpy.ops.import_scene.gltf(filepath=str(glb.resolve()))
    if "FINISHED" not in outcome:
        raise ValueError("NATIVE_GLB_IMPORT_FAILED")
    metadata=[]
    for obj in bpy.data.objects:
        value=obj.get("scp_rom_source_annotation")
        if isinstance(value,str):
            metadata.append(("object",obj.name,value))
        if obj.type=="ARMATURE":
            for bone in obj.data.bones:
                value=bone.get("scp_rom_source_annotation")
                if isinstance(value,str):
                    metadata.append(("bone",bone.name,value))
            for pose in obj.pose.bones:
                value=pose.get("scp_rom_source_annotation")
                if isinstance(value,str):
                    metadata.append(("pose_bone",pose.name,value))
    if not metadata:
        raise ValueError("IMPORTER_LOST_ALL_CUSTOM_SOURCE_ANNOTATIONS")
    originals=[(where,name,value) for where,name,value in metadata if name=="OriginalLower"]
    sourcehash=expected["mesh_source_annotation_sha256"]
    for where,name,raw in metadata:
        if hashlib.sha256(raw.encode()).hexdigest()!=sourcehash:
            raise ValueError("IMPORTER_CHANGED_JSON_SOURCE_ANNOTATION")
        doc=json.loads(raw)
        if doc.get("schema")!="scp.rom.joint_annotation.v1" or doc.get("joint_id")!="original-lower-joint":
            raise ValueError("IMPORTER_CHANGED_JOINT_ID")
    if not originals:
        raise ValueError("IMPORTER_LOST_JOINT_ID_ANCHOR")
    rig=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    if len(rig)!=1 or "OriginalLower" not in rig[0].pose.bones:
        raise ValueError("ACTUAL_IMPORT_SKIN_JOINT_MISSING")
    lower=rig[0].pose.bones["OriginalLower"]
    nlimit=sum(c.type=="LIMIT_ROTATION" for c in lower.constraints)
    iklim=bool(lower.use_ik_limit_x)
    result={"schema":"scp.rom.blender_gltf_reimport.v1",
            "status":"PASS_ACTUAL_NATIVE_GLB_IMPORT_METADATA_ONLY",
            "glb_sha256":expected["glb_sha256"],
            "metadata_nodes":[{"kind":k,"name":n} for k,n,_ in metadata],
            "specific_lower_joint_metadata_survived":bool(originals),
            "native_limit_rotation_count":nlimit,"native_ik_limit_x":iklim,
            "runtime_constraint_equivalence":"NOT_PROVEN",
            "human_anatomy":"UNKNOWN_NOT_MODELLED"}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("ROMFMT_GLB_ACTUAL_REIMPORT",json.dumps(result,sort_keys=True))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--glb",required=True)
    p.add_argument("--source-receipt",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    run(a.glb,a.source_receipt,a.out)
