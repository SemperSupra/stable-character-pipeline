"""Independent fresh-Blender-process verification of real pinned MPFB six-morph research.

Source geometry and animation, not anatomy correctness or photoreal acceptance.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy

p=argparse.ArgumentParser()
p.add_argument("--blend",type=Path,required=True)
p.add_argument("--generation",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve(),"source scene not freshly reopened"
generation=json.loads(a.generation.read_text())
assert generation["schema"]=="r014.mpfb.actual_six_body_kinematic_doe.v1"
assert len(generation["characters"])==3
report={"schema":"r014.six_morph.fresh_reopen.v1",
        "status":"INCOMPLETE","source_blend":a.blend.name,
        "source_reference":generation["mpfb_source_revision"],
        "shard":generation["shard"],"results":[],
        "photoreal_accepted":False,"native_mesh_metric":"Blender source-space delta; not anatomical cm"}
def pts(obj):
    dep=bpy.context.evaluated_depsgraph_get()
    ev=obj.evaluated_get(dep)
    mesh=ev.to_mesh()
    try:
        return [tuple(ev.matrix_world@v.co) for v in mesh.vertices]
    finally:ev.to_mesh_clear()
for sample in generation["characters"]:
    name=sample["case"]
    mesh=bpy.data.objects[name+"_clean_body"]
    rig=bpy.data.objects[name+"_clean_rig"]
    assert mesh.type=="MESH" and rig.type=="ARMATURE"
    assert len(mesh.data.vertices)==sample["clean_vertices"]
    assert len(rig.data.bones)==sample["bone_count"]
    arms=[x.object for x in mesh.modifiers if x.type=="ARMATURE" and x.object is not None]
    assert len(arms)==1 and arms[0]==rig
    names=set(g.name for g in mesh.vertex_groups)
    valid=sum(1 for bone in rig.data.bones if bone.use_deform and bone.name in names)
    assert valid>20,("unweighted rig",name,valid)
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    initial=pts(mesh)
    bpy.context.scene.frame_set(8);bpy.context.view_layer.update()
    posed=pts(mesh)
    d=max(math.dist(x,y) for x,y in zip(initial,posed))
    assert d>1e-4,("no animated mesh after reopen",name)
    bpy.context.scene.frame_set(16);bpy.context.view_layer.update()
    restored=pts(mesh)
    residual=max(math.dist(x,y) for x,y in zip(initial,restored))
    assert residual<1e-4,("nonreversible source rig",name)
    report["results"].append({"case":name,"reopened_native_vertices":len(initial),
                              "reopened_rig_bones":len(rig.data.bones),
                              "matched_weighted_deform_bones":valid,
                              "frame8_max_animated_delta_blender_units":round(d,7),
                              "frame16_return_residual_blender_units":round(residual,9),
                              "glb_export_present_in_generation":bool(sample.get("portable_animated_glb"))})
report["status"]="PASS_FRESH_REOPEN_REAL_SKINNED_MOTION_STRUCTURAL_ONLY"
a.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
print("R014_SIX_MORPH_REOPEN",json.dumps(report,sort_keys=True))
