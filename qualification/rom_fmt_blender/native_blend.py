"""ROMFMT B: genuinely save and reopen original Blender rig with annotated joint.

Blender evaluated constraints/IK and metadata are separate. This validates only
serialization and numeric authored limit semantics, not anatomy/rig quality.
Run via bpy 4.5.0 in a fresh public source-clean CPU runner.
"""
import argparse
import hashlib
import json
from pathlib import Path
import bpy

SCHEMA="scp.rom.joint_annotation.v1"


def build(path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    arm=bpy.data.armatures.new("SyntheticRig")
    obj=bpy.data.objects.new("Original_Anatomy_Test_Rig",arm)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    upper=arm.edit_bones.new("OriginalUpper")
    upper.head=(0,0,0);upper.tail=(0,0,1)
    lower=arm.edit_bones.new("OriginalLower")
    lower.head=(0,0,1);lower.tail=(0,0,2);lower.parent=upper;lower.use_connect=True
    bpy.ops.object.mode_set(mode="POSE")
    pb=obj.pose.bones["OriginalLower"]
    limit=pb.constraints.new("LIMIT_ROTATION")
    limit.name="ROM_SOURCE_LOCAL_LIMIT"
    limit.owner_space="LOCAL"
    limit.use_limit_x=True;limit.min_x=-0.75;limit.max_x=0.75
    limit.use_limit_y=True;limit.min_y=0.0;limit.max_y=0.0
    limit.use_limit_z=False
    pb.use_ik_limit_x=True;pb.ik_min_x=-0.60;pb.ik_max_x=0.60
    pb.use_ik_limit_y=True;pb.ik_min_y=0.0;pb.ik_max_y=0.0
    doc={"schema":SCHEMA,"joint_id":"original-lower-joint",
         "authority":"SYNTHETIC_TEST_ONLY",
         "morphology":"synthetic_fixture","source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
         "frame":"PARENT_LOCAL_TEST_ONLY","unit":"rad",
         "axis":[1,0,0],"kind":"revolute",
         "hard_min":-0.75,"hard_max":0.75,
         "ik_min":-0.60,"ik_max":0.60,
         "export_enforcement":"UNKNOWN_OTHER_APPS_DO_NOT_INHERIT_BLENDER_CONSTRAINTS"}
    raw=json.dumps(doc,sort_keys=True,separators=(",",":"))
    obj["scp_rom_source_annotation"]=raw
    obj.pose.bones["OriginalLower"]["scp_rom_source_annotation"]=raw
    arm.bones["OriginalLower"]["scp_rom_source_annotation"]=raw
    obj["scp_rom_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.wm.save_as_mainfile(filepath=str(path.resolve()))
    return doc


def check(path,expected):
    bpy.ops.wm.open_mainfile(filepath=str(path.resolve()))
    obj=bpy.data.objects.get("Original_Anatomy_Test_Rig")
    if obj is None or obj.type!="ARMATURE":
        raise ValueError("RIG_MISSING_AFTER_REAL_BLEND_REOPEN")
    lower=obj.pose.bones.get("OriginalLower")
    if lower is None or lower.bone.parent is None or lower.bone.parent.name!="OriginalUpper":
        raise ValueError("BONE_PARENT_IDENTITY_MISSING")
    ann=lower.get("scp_rom_source_annotation")
    if not isinstance(ann,str) or json.loads(ann)!=expected:
        raise ValueError("POSE_BONE_METADATA_LOST_OR_CHANGED")
    if obj.get("scp_rom_source_annotation")!=ann or        lower.bone.get("scp_rom_source_annotation")!=ann:
        raise ValueError("MISMATCHED_RIG_VS_BONE_METADATA")
    if hashlib.sha256(ann.encode()).hexdigest()!=obj.get("scp_rom_sha256"):
        raise ValueError("ANNOTATION_TAMPERED")
    constraints=[c for c in lower.constraints if c.type=="LIMIT_ROTATION" and c.name=="ROM_SOURCE_LOCAL_LIMIT"]
    if len(constraints)!=1:
        raise ValueError("LIMIT_ROTATION_NOT_RESTORED")
    c=constraints[0]
    if (c.owner_space!="LOCAL" or not c.use_limit_x or not c.use_limit_y or c.use_limit_z or
        abs(c.min_x-expected["hard_min"])>1e-7 or abs(c.max_x-expected["hard_max"])>1e-7 or
        c.min_y!=0 or c.max_y!=0 or
        not lower.use_ik_limit_x or not lower.use_ik_limit_y or
        abs(lower.ik_min_x-expected["ik_min"])>1e-7 or
        abs(lower.ik_max_x-expected["ik_max"])>1e-7):
        raise ValueError("LIMIT_ROTATION_OR_IK_SOURCE_CHANGED")
    return obj,lower,c


def test_negative(obj,lower,c,doc):
    c.max_x=1.25
    try:
        check_limit_object(lower,c,doc)
    except ValueError as e:
        if str(e)!="HOSTILE_ROTATION_LIMIT_CHANGED":
            raise
    else:
        raise ValueError("HOSTILE_ROTATION_LIMIT_FALSE_PASS")
    c.max_x=doc["hard_max"]
    c.owner_space="WORLD"
    try:
        check_limit_object(lower,c,doc)
    except ValueError as e:
        if str(e)!="HOSTILE_ROTATION_LIMIT_CHANGED":
            raise
    else:
        raise ValueError("HOSTILE_WRONG_OWNER_SPACE_FALSE_PASS")
    c.owner_space="LOCAL"


def check_limit_object(lower,c,doc):
    if c.owner_space!="LOCAL" or abs(c.max_x-doc["hard_max"])>1e-7:
        raise ValueError("HOSTILE_ROTATION_LIMIT_CHANGED")


def run(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    blend=folder/"original_synthetic_joint_limits.blend"
    doc=build(blend)
    obj,pb,c=check(blend,doc)
    test_negative(obj,pb,c,doc)
    # Reload again so hostile in-memory mutations never pollute the authored file.
    obj,pb,c=check(blend,doc)
    h=hashlib.sha256(blend.read_bytes()).hexdigest()
    receipt={"schema":"scp.rom.blender_native.v1",
             "status":"PASS_BLEND_METADATA_AND_TWO_NATIVE_LIMIT_SETS_ONLY",
             "source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
             "blend_sha256":h,"joint":"original-lower-joint",
             "constraint_owner_space":c.owner_space,
             "rotation_bounds_rad":[c.min_x,c.max_x],
             "ik_bounds_rad":[pb.ik_min_x,pb.ik_max_x],
             "rig_hash":obj["scp_rom_sha256"],
             "hostile_changed_limit_and_wrong_space":"REJECTED_2_OF_2",
             "bio_anatomy":"UNKNOWN_TEST_ONLY","actual_ik_solution":"NOT_EVALUATED",
             "export_survival":"NOT_ASSUMED"}
    (folder/"native_blender_joint_receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("ROMFMT_BLEND_NATIVE_ROUNDTRIP",json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    run(p.parse_args().out)
