"""W6C: actual Blender FBX save/export/import, custom property and ROM semantics.

FBX DCC behavior varies by importer/version. A source metadata reference can
survive without a working Blender pose or IK limit. Never assume equivalence.
"""
import argparse,hashlib,json
from pathlib import Path
import bpy
from native_blend import build,check

RIGHTS="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
def admit(value,expected,hash_value):
    if not isinstance(value,str) or hashlib.sha256(value.encode()).hexdigest()!=hash_value:
        raise ValueError("FBX_SOURCE_IDENTITY_OR_SHA_LOST")
    parsed=json.loads(value)
    if parsed!=expected:
        raise ValueError("FBX_JOINT_SEMANTICS_TAMPERED")
    return True

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    sourceblend=out/"original_source_native_fbx.blend"
    original=build(sourceblend)
    obj,lower,c=check(sourceblend,original)
    original_raw=obj.get("scp_rom_source_annotation")
    digest=hashlib.sha256(original_raw.encode()).hexdigest()
    # Prepare actual skinned mesh to retain armature linkage across export.
    bpy.ops.mesh.primitive_cube_add(size=.25,location=(0,0,1.3))
    mesh=bpy.context.object;mesh.name="Original_FBX_SkinnedMesh"
    weights=mesh.vertex_groups.new(name="OriginalLower")
    weights.add(list(range(len(mesh.data.vertices))),1.0,"REPLACE")
    modifier=mesh.modifiers.new(name="OriginalSkin",type="ARMATURE")
    modifier.object=obj
    mesh.parent=obj
    mesh["scp_rom_source_annotation"]=original_raw
    fbx=out/"original_synthetic_joint_constraints.fbx"
    if not hasattr(bpy.ops.export_scene,"fbx"):
        raise ValueError("NATIVE_FBX_EXPORTER_NOT_AVAILABLE")
    res=bpy.ops.export_scene.fbx(filepath=str(fbx.resolve()),
             object_types={"ARMATURE","MESH"},use_custom_props=True,
             add_leaf_bones=False,bake_anim=False)
    if "FINISHED" not in res or fbx.stat().st_size<1024:
        raise ValueError("NATIVE_FBX_FILE_FAILURE")
    fbx_sha=hashlib.sha256(fbx.read_bytes()).hexdigest()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if not hasattr(bpy.ops.import_scene,"fbx"):
        raise ValueError("NATIVE_FBX_IMPORTER_NOT_AVAILABLE")
    result=bpy.ops.import_scene.fbx(filepath=str(fbx.resolve()),use_custom_props=True)
    if "FINISHED" not in result:
        raise ValueError("NATIVE_FBX_IMPORT_FAILED")
    arms=[o for o in bpy.data.objects if o.type=="ARMATURE"]
    if len(arms)!=1:
        raise ValueError("FBX_IMPORTED_ARMATURE_COUNT")
    arm=arms[0]
    bones=[p for p in arm.pose.bones if "OriginalLower" in p.name]
    if len(bones)!=1:
        raise ValueError("FBX_IMPORTED_BONE_ID_NOT_UNIQUE")
    bone=bones[0]
    flags={}
    candidates=[("armature_object",arm.get("scp_rom_source_annotation")),
                ("armature_data_bone",bone.bone.get("scp_rom_source_annotation")),
                ("pose_bone",bone.get("scp_rom_source_annotation"))]
    for kind,value in candidates:
        if value is None:
            flags[kind]="MISSING"
        else:
            try:
                admit(value,original,digest)
                flags[kind]="PRESERVED_SOURCE_SHA"
            except ValueError:
                flags[kind]="CHANGED_OR_UNQUALIFIED"
    imported_meshes=[o for o in bpy.data.objects if o.type=="MESH"]
    flags["mesh"]= "PRESERVED_SOURCE_SHA" if any(
       isinstance(m.get("scp_rom_source_annotation"),str) and
       m.get("scp_rom_source_annotation")==original_raw for m in imported_meshes) else "MISSING_OR_CHANGED"
    limit=[c for c in bone.constraints if c.type=="LIMIT_ROTATION"]
    valid_limit=any(c.owner_space=="LOCAL" and c.use_limit_x and
                    abs(c.min_x-original["hard_min"])<1e-7 and
                    abs(c.max_x-original["hard_max"])<1e-7 for c in limit)
    ik=(bone.use_ik_limit_x and
        abs(bone.ik_min_x-original["ik_min"])<1e-7 and
        abs(bone.ik_max_x-original["ik_max"])<1e-7)
    if flags["armature_object"]=="PRESERVED_SOURCE_SHA":
        admit(original_raw,original,digest)
        try:admit(original_raw.replace("original-lower-joint","changed-joint"),original,digest)
        except ValueError:hostile="REJECTED"
        else:raise ValueError("TAMPERED_CUSTOM_PROPERTY_ACCEPTED")
    else:
        hostile="NOT_TESTED_NO_ADMITTED_OBJECT_METADATA"
    if hashlib.sha256(fbx.read_bytes()).hexdigest()!=fbx_sha:
        raise ValueError("FBX_SOURCE_BINARY_MUTATED")
    observation={"schema":"scp.rom.w6c_native_fbx_reimport.v1",
                 "status":"OBSERVED_NATIVE_FBX_SEMANTICS_NOT_ANATOMICAL_PASS",
                 "rights":RIGHTS,"fbx_sha256":fbx_sha,
                 "original_blend_sha256":hashlib.sha256(sourceblend.read_bytes()).hexdigest(),
                 "authoritative_source_annotation_sha256":digest,
                 "specific_bone":bone.name,"metadata_survival":flags,
                 "operative_local_limit_rotation_preserved":bool(valid_limit),
                 "operative_ik_x_limit_preserved":bool(ik),
                 "limit_rotation_constraint_count":len(limit),
                 "hostile_source_metadata":hostile,
                 "rom_correctness":"UNKNOWN_NOT_CONFIRMED_FROM_FBX_EXPORT",
                 "joint_angle_frame_mapping":"UNKNOWN_FBX_EULER_ORDER",
                 "human_anatomy":"UNKNOWN_TEST_FIXTURE_ONLY"}
    (out/"fbx_native_roundtrip_receipt.json").write_text(json.dumps(observation,sort_keys=True,indent=2)+"\n")
    print("W6C_NATIVE_FBX_JOINT_SEMANTICS",json.dumps(observation,sort_keys=True))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True)
    run(p.parse_args().out)
