"""R014 compare original and morphed native CC0 attachment fit; evidence not approval."""
import argparse,json,math
from pathlib import Path

p=argparse.ArgumentParser()
for k in ("original","morphed","receipt","out"):p.add_argument("--"+k,required=True,type=Path)
a=p.parse_args()
old=json.loads(a.original.read_text())
new=json.loads(a.morphed.read_text())
source=json.loads(a.receipt.read_text())
assert old["stage"]=="original" and new["stage"]=="morphed"
assert old["sex_macro"]==new["sex_macro"]==source["sex_macro_label"]
assert source["status"]=="PASS_SOURCE_NATIVE_CC0_MORPH_MOTION_RENDER_STRUCTURAL_ONLY"
assert new["source_scene_sha256"]==source["editable_blend"]["sha256"]
assert old["body_evaluated_vertices"]>1000 and new["body_evaluated_vertices"]>1000
oc={v["name"]:v for v in old["attached_meshes"]}
nc={v["name"]:v for v in new["attached_meshes"]}
common=sorted(set(oc)&set(nc))
items=[]
for name in common:
    before,after=oc[name],nc[name]
    if before["total_evaluated_vertices"]!=after["total_evaluated_vertices"]:
        topo="CHANGED_TOPOLOGY"
    else:
        topo="SAME_EVALUATED_VERTEX_COUNT"
    movement=math.dist(before["evaluated_world_centroid"],after["evaluated_world_centroid"])
    if not math.isfinite(movement):raise AssertionError("NONFINITE_MOVEMENT")
    items.append({
        "object_name":name,"topology_comparison":topo,
        "centroid_move_native":round(movement,7),
        "native_mean_surface_distance_before":before["mean_nearest_body_distance_native"],
        "native_mean_surface_distance_after":after["mean_nearest_body_distance_native"],
        "native_mean_surface_distance_change":round(after["mean_nearest_body_distance_native"]-before["mean_nearest_body_distance_native"],7),
        "provisional_normal_side_negative_before":before["count_normal_side_negative_provisional"],
        "provisional_normal_side_negative_after":after["count_normal_side_negative_provisional"],
        "original_sampled_vertices":before["sampled_evaluated_vertices"],
        "morphed_sampled_vertices":after["sampled_evaluated_vertices"]
    })
out={
 "schema":"r014.cc0.original_to_morphed_attachment_comparison.v1",
 "sex_macro":source["sex_macro_label"],
 "original_source_scene_sha256":old["source_scene_sha256"],
 "morphed_source_scene_sha256":new["source_scene_sha256"],
 "morph_native_body_vertex_delta":source["real_morph_max_vertex_delta_blender_units"],
 "original_related_meshes":old["related_candidate_meshes"],
 "morphed_related_meshes":new["related_candidate_meshes"],
 "common_meshes":len(common),
 "original_only_meshes":sorted(set(oc)-set(nc)),
 "morphed_only_meshes":sorted(set(nc)-set(oc)),
 "items":items,
 "policy":"PASS means evidence instrumentation, NOT accessory fit, watertight intersection, eye realism, or garment clearance",
 "geometry_approval":"HOLD",
 "admission":"SOURCE_PUBLIC_LICENSED_SYNTHETIC_ONLY",
 "merge_release":"HOLD",
}
out["status"]="PASS_SOURCE_NATIVE_ACCESSORY_COMPARISON_DIAGNOSTIC_ONLY" if common else "UNKNOWN_NO_COMMON_ATTACHED_MESHES"
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
print("R014_ACCESSORY_COMPARISON",json.dumps({
 "sex_macro":out["sex_macro"],"status":out["status"],
 "common_meshes":len(common),"object_names":common,
 "max_mean_surface_distance_change":max([abs(x["native_mean_surface_distance_change"]) for x in items],default=None),
 "max_centroid_move_native":max([x["centroid_move_native"] for x in items],default=None)
},sort_keys=True))
