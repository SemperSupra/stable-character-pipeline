"""Restore source-specified original-only Blender ROM constraint after GLB import.

This binds the specific imported joint to the exact SHA in an independent
source export receipt. A restored *configuration* is not universal anatomical
ROM acceptance, but we independently observe the evaluated bone rotation.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import bpy
from import_glb import run as original_import

def hard_check(doc, source_hash):
    if hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(",",":")).encode()).hexdigest()!=source_hash:
        raise ValueError("SOURCE_HASH_OR_DOCUMENT_CHANGED")
    exact=("schema","joint_id","authority","morphology","source_rights","frame","unit","axis","kind","hard_min","hard_max","ik_min","ik_max","export_enforcement")
    if set(doc)!=set(exact):
        raise ValueError("DOCUMENT_FIELDS_NOT_ADMITTED")
    if (doc["schema"]!="scp.rom.joint_annotation.v1" or doc["joint_id"]!="original-lower-joint" or
        doc["authority"]!="SYNTHETIC_TEST_ONLY" or doc["morphology"]!="synthetic_fixture" or
        doc["source_rights"]!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or
        doc["frame"]!="PARENT_LOCAL_TEST_ONLY" or doc["unit"]!="rad" or
        doc["axis"]!=[1,0,0] or doc["kind"]!="revolute"):
        raise ValueError("UNQUALIFIED_BIOLOGICAL_OR_AXIS_SEMANTICS")
    for k in ("hard_min","hard_max","ik_min","ik_max"):
        if type(doc[k]) not in (float,int) or not math.isfinite(doc[k]):
            raise ValueError("INVALID_NUMERIC_LIMIT")
    if not doc["hard_min"]<doc["ik_min"]<=0<=doc["ik_max"]<doc["hard_max"]:
        raise ValueError("INCOMPATIBLE_IK_VS_HARD_RANGE")

def evaluated_local_x(rig,bone):
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    ev=rig.evaluated_get(deps)
    p=ev.pose.bones[bone]
    parent=p.parent
    if parent is None:
        raise ValueError("PARENT_REQUIRED")
    rest=p.bone.matrix_local
    parent_rest=parent.bone.matrix_local
    rest_relative=parent_rest.inverted() @ rest
    posed_relative=parent.matrix.inverted() @ p.matrix
    local_delta=rest_relative.inverted() @ posed_relative
    return float(local_delta.to_euler("XYZ").x)

def restore(glb,source_receipt,out):
    glb,source_receipt,out=map(Path,(glb,source_receipt,out))
    out.mkdir(parents=True,exist_ok=True)
    receipt=json.loads(source_receipt.read_text())
    if receipt.get("schema")!="scp.rom.blender_to_gltf.v1" or receipt.get("source_rights")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("INVALID_EXPORT_RECEIPT")
    if hashlib.sha256(glb.read_bytes()).hexdigest()!=receipt.get("glb_sha256"):
        raise ValueError("EXACT_GLB_BYTE_SHA_MISMATCH")
    original_import(glb,source_receipt,out/"pre_restore_import_observation.json")
    rigs=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    if len(rigs)!=1 or "OriginalLower" not in rigs[0].pose.bones:
        raise ValueError("JOINT_MAPPING_NOT_UNIQUE")
    rig=rigs[0];bone=rig.pose.bones["OriginalLower"]
    if bone.parent is None or bone.parent.name!="OriginalUpper":
        raise ValueError("WRONG_PARENT_OR_JOINT_TOPOLOGY")
    raw=bone.get("scp_rom_source_annotation")
    if not isinstance(raw,str):
        raise ValueError("MISSING_JOINT_ANNOTATION")
    if hashlib.sha256(raw.encode()).hexdigest()!=receipt["mesh_source_annotation_sha256"]:
        raise ValueError("SOURCE_ANNOTATION_HASH_WRONG")
    doc=json.loads(raw)
    hard_check(doc,receipt["mesh_source_annotation_sha256"])
    # Baseline: metadata-only imported model has no operative ROM constraint.
    if any(c.type=="LIMIT_ROTATION" for c in bone.constraints) or bone.use_ik_limit_x:
        raise ValueError("EXPECTED_UNCONSTRAINED_IMPORTED_BASELINE")
    bone.rotation_mode="XYZ"
    bone.rotation_euler=(1.15,0,0)
    raw_angle=evaluated_local_x(rig,"OriginalLower")
    if abs(raw_angle)<=doc["hard_max"]+.10:
        raise ValueError("UNCONSTRAINED_MOTION_NOT_OBSERVED")
    c=bone.constraints.new("LIMIT_ROTATION")
    c.name="ROM_SOURCE_RESTORED"
    c.owner_space="LOCAL"
    c.use_limit_x=True;c.min_x=doc["hard_min"];c.max_x=doc["hard_max"]
    c.use_limit_y=True;c.min_y=0;c.max_y=0;c.use_limit_z=False
    bone.use_ik_limit_x=True;bone.ik_min_x=doc["ik_min"];bone.ik_max_x=doc["ik_max"]
    bone.use_ik_limit_y=True;bone.ik_min_y=0;bone.ik_max_y=0
    constrained=evaluated_local_x(rig,"OriginalLower")
    if abs(constrained)>doc["hard_max"]+0.02:
        raise ValueError("RESTORED_CONSTRAINT_NOT_EFFECTIVE_ON_EVALUATED_POSE")
    # Mutate one *numeric source value*, not a cosmetic label, while retaining
    # externally captured canonical digest. Independent verifier must refuse.
    changed=dict(doc);changed["hard_max"]=1.5
    try:
        hard_check(changed,receipt["mesh_source_annotation_sha256"])
    except ValueError as ex:
        if str(ex)!="SOURCE_HASH_OR_DOCUMENT_CHANGED":raise
    else:
        raise ValueError("TAMPERED_HARD_LIMIT_NOT_REJECTED")
    if (len([x for x in bone.constraints if x.type=="LIMIT_ROTATION"])!=1 or
        not bone.use_ik_limit_x or abs(c.max_x-doc["hard_max"])>1e-6):
        raise ValueError("RESTORED_CONSTRAINT_FIELDS_MISSING")
    source_glb_sha=hashlib.sha256(glb.read_bytes()).hexdigest()
    outblend=out/"original_imported_rebound_limits.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(outblend.resolve()))
    if hashlib.sha256(glb.read_bytes()).hexdigest()!=source_glb_sha:
        raise ValueError("ORIGINAL_GLB_MUTATED")
    report={"schema":"scp.rom.w4a_blender_rebound.v1",
            "status":"PASS_SOURCE_SYNTHETIC_RESTORED_EVALUATED_JOINT_ONLY",
            "glb_sha256":source_glb_sha,
            "restored_blend_sha256":hashlib.sha256(outblend.read_bytes()).hexdigest(),
            "source_annotation_sha256":receipt["mesh_source_annotation_sha256"],
            "joint":"OriginalLower",
            "unconstrained_evaluated_angle_rad":raw_angle,
            "constrained_evaluated_angle_rad":constrained,
            "hard_bound_rad":[doc["hard_min"],doc["hard_max"]],
            "ik_bound_rad":[doc["ik_min"],doc["ik_max"]],
            "tampered_source_bound":"REJECTED",
            "anatomy":"UNKNOWN_NO_APPROVED_ANATOMICAL_FRAME",
            "actual_ik_target_solution":"NOT_TESTED",
            "production_release":"HELD"}
    (out/"restoration_observation.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("ROM_W4A_RESTORATION",json.dumps(report,sort_keys=True))
    return report
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for field in ("glb","source-receipt","out"):
        p.add_argument("--"+field,required=True)
    a=p.parse_args()
    restore(a.glb,a.source_receipt,a.out)
