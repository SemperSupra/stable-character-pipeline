"""R014 public independently saved native PBR material-assignment census.

No fabricated skin/face/eye/hair completeness: diagnoses exact existing sources,
per-face Blender material selection, UV allocation and packed texture custody.
"""
import argparse
from collections import Counter
from pathlib import Path
import hashlib
import json
import sys

import bpy

p=argparse.ArgumentParser()
p.add_argument("--sex",required=True,choices=("female","male"))
p.add_argument("--blend",required=True,type=Path)
p.add_argument("--receipt",required=True,type=Path)
p.add_argument("--out",required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve()
evidence=json.loads(a.receipt.read_text())
assert evidence["sex_macro_label"]==a.sex
assert evidence["status"]=="PASS_SOURCE_NATIVE_CC0_MORPH_MOTION_RENDER_STRUCTURAL_ONLY"
body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
rig=bpy.data.objects["R014_"+a.sex+"_textured_rig"]
assert body.type=="MESH" and len(body.data.vertices)==19158
assert len(rig.data.bones)==163
assert len([m for m in body.modifiers if m.type=="ARMATURE" and m.object==rig])==1
packed=[{"name":im.name,"size":list(im.size),"packed_bytes":im.packed_file.size}
        for im in bpy.data.images if im.source=="FILE" and im.packed_file]
unpacked=[im.name for im in bpy.data.images if im.source=="FILE" and not im.packed_file]
meshes=[obj for obj in bpy.data.objects if obj.type=="MESH" and not obj.hide_render]
out={"schema":"r014.cc0.native_material_coverage_audit.v1",
     "status":"DIAGNOSTIC_ONLY","actor":a.sex,
     "source_run":evidence.get("source_github_actions_run"),
     "source_mpbf":evidence["source_mpbf"],
     "source_archive_sha256":evidence["source_official_pack_sha256"],
     "blender":bpy.app.version_string,
     "body_vertices":len(body.data.vertices),
     "body_faces":len(body.data.polygons),
     "body_uv_map_count":len(body.data.uv_layers),
     "baked_source_textures":[{"name_sha":hashlib.sha256(x["name"].encode()).hexdigest()[:14],"image_resolution":x["size"],"packed_bytes":x["packed_bytes"]} for x in packed],
     "unpacked_source_images":unpacked,
     "body_material_slots":[],
     "visible_mesh_materials":[],
     "rig_deform_groups":len(body.vertex_groups),
     "photoreal_visual_acceptance":"HOLD_NOT_RUN",
     "external_reproductive_topology":"UNQUALIFIED",
     "material_assignment":"EVIDENCE_ONLY_NO_VISUAL_PROOF",
     "cinematic_4k":"HOLD",
     "merge_release":"HOLD"}
def material_info(mat):
    if not mat:return {"status":"MISSING_MATERIAL"}
    nts=mat.node_tree.nodes if mat.use_nodes and mat.node_tree else []
    return {
        "name":mat.name,
        "uses_nodes":bool(mat.use_nodes and mat.node_tree),
        "node_types":dict(Counter(n.type for n in nts)),
        "image_node_images":[{"name_sha":hashlib.sha256(n.image.name.encode()).hexdigest()[:14],
                              "is_packed":bool(n.image.packed_file)}
                             for n in nts if n.type=="TEX_IMAGE" and n.image],
        "has_material_output":any(n.type=="OUTPUT_MATERIAL" for n in nts),
        "has_principled":any(n.type=="BSDF_PRINCIPLED" for n in nts),
        "has_node_group":any(n.type=="GROUP" for n in nts),
    }

assignments=Counter(face.material_index for face in body.data.polygons)
for idx,mat in enumerate(body.data.materials):
    out["body_material_slots"].append({
        "slot":idx,"polygon_count":assignments.get(idx,0),
        "polygon_share":round(assignments.get(idx,0)/len(body.data.polygons),6),
        "material":material_info(mat)})
unmapped=sum(n for idx,n in assignments.items() if idx>=len(body.data.materials) or body.data.materials[idx] is None)
out["unmapped_body_faces"]=unmapped
for obj in meshes:
    out["visible_mesh_materials"].append({
        "name":obj.name,"vertices":len(obj.data.vertices),
        "faces":len(obj.data.polygons),
        "skin_modifier":any(m.type=="ARMATURE" and m.object for m in obj.modifiers),
        "uv_layers":len(obj.data.uv_layers),
        "material_slots":[x.name if x else None for x in obj.data.materials],
        "missing_material_slots":sum(1 for mat in obj.data.materials if mat is None)
    })
if len(packed)>=1 and unmapped==0 and any(row["polygon_count"]>0 and row["material"].get("uses_nodes") for row in out["body_material_slots"]):
    out["status"]="PASS_SOURCE_MATERIAL_FACE_ASSIGNMENT_AND_PACKED_IMAGE_AUDIT_ONLY"
else:
    out["status"]="FAIL_SOURCE_MATERIAL_ASSIGNMENTS_OR_PACKED_TEXTURES"
out["audit_limits"]=[
    "No visual skin texture realism, color, anatomical correctness or photographic quality conclusion",
    "Having one material slot name ending in 'genitals' does not prove external genital mesh or realistic skin; count polygons and effective shader graph",
    "Hair, eyes, lashes, brows and tooth assets require independent geometry/collision/visual region gates",
    "UV existence and packed image links do not establish proper UV topology, shading normals or nonpenetration",
    "Source mesh eyes/MHCLo metadata not independently region-tagged",
    "Prior upstream pack said CC0; verify each asset license on release"
]
a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print("R014_CC0_MATERIAL_COVERAGE",json.dumps({k:v for k,v in out.items() if k!="visible_mesh_materials"},sort_keys=True))
if out["status"].startswith("FAIL"):sys.exit(1)
