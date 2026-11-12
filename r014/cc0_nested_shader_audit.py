"""R014 nested native material graph study, exact saved-source CC0 actor.
Records nested group PBR primitives and actually linked Blender output surface.
This is material-graph evidence only, not visual fidelity or anatomical coverage.
"""
import argparse,collections,hashlib,json,sys
from pathlib import Path
import bpy
p=argparse.ArgumentParser()
p.add_argument("--sex",required=True,choices=["female","male"])
p.add_argument("--out",required=True,type=Path)
p.add_argument("--expected",required=True,type=Path)
p.add_argument("--blend",required=True,type=Path)
a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
assert Path(bpy.data.filepath).resolve()==a.blend.resolve()
r=json.loads(a.expected.read_text())
assert r["actor"]==a.sex and r["status"]=="PASS_SOURCE_MATERIAL_FACE_ASSIGNMENT_AND_PACKED_IMAGE_AUDIT_ONLY"
body=bpy.data.objects["R014_"+a.sex+"_textured_body"]
assert len(body.data.vertices)==19158
result={
    "schema":"r014.cc0.grouped_native_shader_graph.v1",
    "source":"pinned official MPFB source saved-lookdev material",
    "source_actor":a.sex,
    "blender":bpy.app.version_string,
    "source_material_faces":len(body.data.polygons),
    "model_status":"RESEARCH_NATIVE_MATERIAL_GRAPH_ONLY",
    "visual_realism":"HOLD",
    "external_anatomy":"HOLD",
    "release":"HOLD",
    "materials":[]
}
def scan(tree,visited,depth):
    if tree is None:return {"missing":True}
    if depth>6:return {"depth_limit":True}
    if tree.as_pointer() in visited:return {"shared":True}
    visited.add(tree.as_pointer())
    cnt=collections.Counter(n.type for n in tree.nodes)
    packed=0;images=0;embedded=[]
    for node in tree.nodes:
        if node.type=="TEX_IMAGE" and node.image:
            images+=1
            packed+=int(bool(node.image.packed_file))
            embedded.append({
                "name_sha256_12":hashlib.sha256(node.image.name.encode()).hexdigest()[:12],
                "packed":bool(node.image.packed_file),
                "image_size":list(node.image.size)
            })
    nested=[]
    for node in tree.nodes:
        if node.type=="GROUP":
            nested.append({"node_name_hash":hashlib.sha256(node.name.encode()).hexdigest()[:12],
                           "tree":scan(node.node_tree,visited,depth+1)})
    return {"node_types":dict(cnt),"direct_image_textures":images,
            "direct_packed_image_textures":packed,"images":embedded,
            "groups":nested,
            "shader_outputs":[{"name":n.name,"surface_linked":bool(n.inputs.get("Surface") and n.inputs.get("Surface").is_linked)}
                              for n in tree.nodes if n.type=="OUTPUT_MATERIAL"],
            "links":len(tree.links)}
def totals(tree):
    output=collections.Counter();packed=0;images=0
    def collect(t):
        nonlocal packed,images
        output.update(t.get("node_types",{}))
        images+=t.get("direct_image_textures",0)
        packed+=t.get("direct_packed_image_textures",0)
        for grp in t.get("groups",[]):collect(grp["tree"])
    collect(tree)
    return dict(output),packed,images
for slot,material in enumerate(body.data.materials):
    faces=sum(1 for poly in body.data.polygons if poly.material_index==slot)
    graph=scan(material.node_tree,set(),0) if material and material.use_nodes else {"missing":True}
    counted,packed,images=totals(graph)
    entry={"slot":slot,"name":material.name if material else None,"assigned_faces":faces,
           "nested_node_counts":counted,"nested_packed_image_references":packed,
           "nested_image_references":images,
           "main_surface_linked":any(x["surface_linked"] for x in graph.get("shader_outputs",[])),
           "graph":graph}
    result["materials"].append(entry)
active=[x for x in result["materials"] if x["assigned_faces"]>0]
result["active_material_count"]=len(active)
result["active_materials_without_output_surface"]=sum(not x["main_surface_linked"] for x in active)
result["active_materials_with_nested_image_nodes"]=sum(x["nested_image_references"]>0 for x in active)
result["active_materials_with_pbr_principled"]=sum(x["nested_node_counts"].get("BSDF_PRINCIPLED",0)>0 for x in active)
result["active_materials_with_subsurface_scattering_node"]=sum(x["nested_node_counts"].get("BSDF_SUBSURFACE_SCATTERING",0)>0 for x in active)
result["unused_material_slots"]=[x["slot"] for x in result["materials"] if x["assigned_faces"]==0]
result["status"]="PASS_NATIVE_GROUPED_SHADER_STRUCTURE_DIAGNOSTIC_ONLY" if all(x["main_surface_linked"] for x in active) else "HOLD_BROKEN_OR_MISSING_SURFACE_CONNECTION"
result["limits"]=[
    "Nested node census is not a full material flow graph; unused nodes inside groups may be counted",
    "Subsurface scatter may be a principled input, not an independent SSS node",
    "Packed images plus PBR graphs cannot certify correct skin/hair/eye optical behavior",
    "No facial animation, anatomy, close view, ray-traced 4K realism or full-model motion acceptance"]
a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
print("R014_NESTED_PBR_GRAPH",json.dumps({k:v for k,v in result.items() if k!="materials"}|{"materials_compact":[{k:v for k,v in x.items() if k!="graph"} for x in result["materials"]]},sort_keys=True))
if result["status"].startswith("HOLD_BROKEN"):raise SystemExit(1)
