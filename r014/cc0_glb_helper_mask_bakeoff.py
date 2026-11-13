"""R014 SOURCE-NATIVE glTF export mask correctness bakeoff on CC0 full adults.

Two bounded, independently executable author-source strategies:
A: Blender glTF export_apply=True with original live Hide helpers mask;
B: official pinned MPFB ExportService helper-mask bake in disposable source
   scene, followed by ordinary skinned+animated glTF export.
Neither strategy modifies original saved author .blend or source repo.
"""
import argparse
from hashlib import sha256
import importlib
import json
from pathlib import Path
import struct
import sys
import bpy
import addon_utils

SOURCE="6ff1eb358f6c1959ced77e79e6dd2406d9a71f49"
def digest(path):
    h=sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def service(suffix,name):
    for module_name in tuple(sys.modules):
        if module_name.endswith(suffix):
            module=importlib.import_module(module_name)
            if hasattr(module,name):return getattr(module,name)
    raise RuntimeError("EXACT_PINNED_MPFB_BAKE_API_NOT_FOUND_"+suffix)

def glb_info(path):
    with path.open("rb") as f:
        magic,ver,n=struct.unpack("<4sII",f.read(12))
        assert magic==b"glTF" and ver==2 and n==path.stat().st_size
        size,kind=struct.unpack("<I4s",f.read(8))
        assert kind==b"JSON"
        j=json.loads(f.read(size))
    return {"animations":len(j.get("animations",[])),
            "meshes":len(j.get("meshes",[])),
            "skins":len(j.get("skins",[])),
            "morph_target_meshes":sum(bool(any(p.get("targets") for p in m.get("primitives",[]))) for m in j.get("meshes",[])),
            "sha256":digest(path),"bytes":path.stat().st_size}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--sex",choices=("female","male"),required=True)
    p.add_argument("--strategy",choices=("direct_apply","mpfb_mask_bake"),required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--source-receipt",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    a.out.mkdir(parents=True,exist_ok=True)
    assert Path(bpy.data.filepath).resolve()==a.source.resolve()
    original=json.loads(a.source_receipt.read_text())
    assert original["status"]=="PASS_BOUNDED_REAL_SOURCE_NATIVE_TEMPORAL_EVIDENCE_CAPTURE_ONLY"
    assert original["sex_macro"]==a.sex
    assert original["native_scene"]["sha256"]==digest(a.source)
    rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
    body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
    assert rig.type=="ARMATURE" and body.type=="MESH"
    assert len(rig.data.bones)==163 and len(body.data.vertices)==19158
    masks=[m for m in body.modifiers if m.type=="MASK"]
    assert len(masks)>=1 and any(m.name=="Hide helpers" for m in masks)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated=ev.to_mesh()
    try:
        before_evaluated=len(evaluated.vertices)
        assert before_evaluated==13380,("ORIGINAL_NOT_EXPECTED_VISIBLE_BODY",before_evaluated)
    finally:ev.to_mesh_clear()
    source_shape_keys=0 if body.data.shape_keys is None else len(body.data.shape_keys.key_blocks)
    report={
       "schema":"r014.source_CC0_glb_helper_mask_export_bakeoff.v1",
       "status":"NOT_QUALIFIED",
       "strategy":a.strategy,"sex":a.sex,"exact_source":"mpfb2@"+SOURCE,
       "source_scene_sha256":digest(a.source),
       "source_raw_body_vertices":len(body.data.vertices),
       "source_visible_body_evaluated_vertices":before_evaluated,
       "source_body_morph_keys":source_shape_keys,
       "exact_original_gltf_sha256":original["glb"]["sha256"],
       "source_is_public_synthetic_CC0":True,
       "cinematic_anatomical_acceptance":"HOLD",
       "model_eligibility":"NO_PRODUCTION_PROMOTION",
       "merge_release":"HOLD"
    }
    try:
        if a.strategy=="mpfb_mask_bake":
            extension="bl_ext.r014lab.mpfb"
            if extension not in bpy.context.preferences.addons:
                addon_utils.enable(extension,default_set=False)
            assert extension in bpy.context.preferences.addons,"OFFICIAL_MPFb_EXTENSION_MISSING"
            Export=service("mpfb.services.exportservice","ExportService")
            Export.bake_modifiers_remove_helpers(
                body,bake_masks=True,bake_subdiv=False,
                remove_helpers=True,also_proxy=False)
            bpy.context.view_layer.update()
            assert len(body.data.vertices)==13380,("BAKE_DID_NOT_REMOVE_HELPERS",len(body.data.vertices))
            assert not any(m.type=="MASK" for m in body.modifiers),"MASK_NOT_REMOVED"
        actors=[obj for obj in bpy.data.objects if obj.type=="MESH" and
                obj.name.startswith("R014_"+a.sex+"_textured_body")]
        assert len(actors)>=7
        original_body=body
        assert any(m.type=="ARMATURE" and m.object==rig for m in body.modifiers),"SKINNING_REMOVED"
        bpy.ops.object.select_all(action="DESELECT")
        for obj in actors+[rig]:obj.select_set(True)
        bpy.context.view_layer.objects.active=rig
        glb=a.out/("R014_"+a.sex+"_"+a.strategy+"_portable_human.glb")
        bpy.ops.export_scene.gltf(
            filepath=str(glb),export_format="GLB",use_selection=True,
            export_animations=True,export_morph=True,
            export_skins=True,export_yup=True,
            export_apply=(a.strategy=="direct_apply"))
        metadata=glb_info(glb)
        assert metadata["skins"]>=1 and metadata["animations"]>=1
        assert metadata["meshes"]>=7
        report["generated_portable_glb"]={"name":glb.name,**metadata}
        report["post_export_body_vertices"]=len(body.data.vertices)
        report["post_export_body_morph_keys"]=(
            0 if body.data.shape_keys is None else len(body.data.shape_keys.key_blocks))
        report["post_export_mask_modifiers"]=[
            m.name for m in body.modifiers if m.type=="MASK"]
        report["status"]="PASS_EXPERIMENTAL_GLTF_EXPORT_ONLY_NEEDS_INDEPENDENT_GEOMETRY_PARITY"
    except Exception as e:
        report["status"]="FAIL_SOURCE_EXPORT_PRECONDITION_OR_RUNTIME"
        report["failure"]={"type":type(e).__name__,"detail":str(e)[:1100]}
    receipt=a.out/"export_bakeoff_receipt.json"
    receipt.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("R014_MASK_GLTF_BAKEOFF",json.dumps(report,sort_keys=True))
    if not report["status"].startswith("PASS_"):raise SystemExit("FAIL_GLTF_EXPORT_STAGE")

if __name__=="__main__":main()
