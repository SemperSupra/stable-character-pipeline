"""R014 independent state-contract comparison of source and morphed accessory transfer.

No visual quality/fit promotion: only immutable material, topology, texture,
UV, rig grouping, and independently observed evaluated vertex differences.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

CONTRACT=[
  "parent","object_type","raw_vertices","raw_edges","raw_polygons","loops",
  "polygon_index_layout_sha256","material_index_layout_sha256","material_slots",
  "modifiers","vertex_group_names","weights_sha256_rounded_8",
  "uv_layers","shape_key_schema",
]

def compare(before,after):
    assert before["sex_macro"]==after["sex_macro"],"INCONSISTENT_SOURCE_COHORT"
    assert before["rig_bones"]==after["rig_bones"]==163
    assert before["source_body_raw_vertices"]==after["source_body_raw_vertices"]==19158
    assert before["frame"]==after["frame"]==1
    assert before["blender"]==after["blender"]
    assert before["packed_images"]==after["packed_images"],"PACKED_SOURCE_IMAGES_MUTATED_OR_LOST"
    a,b=before["meshes"],after["meshes"]
    assert set(a)==set(b),"ACTOR_MESH_INVENTORY_DIFFERENCE"
    changed=[]
    unchanged=[]
    for name in sorted(a):
        for k in CONTRACT:
            assert a[name][k]==b[name][k],("SOURCE_MESH_CONTRACT_DRIFT",name,k)
        old=a[name]["actual_evaluated_geometry"]
        new=b[name]["actual_evaluated_geometry"]
        assert old["vertices"]==new["vertices"] and old["faces"]==new["faces"],(
            "EVALUATED_TOPOLOGY_DRIFT",name)
        if old["actual_evaluated_world_vertex_hash"]==new["actual_evaluated_world_vertex_hash"]:
            unchanged.append(name)
        else:changed.append(name)
    body="R014_"+before["sex_macro"]+"_textured_body"
    assert body in a and a[body]["is_body"] and b[body]["is_body"]
    assert body in unchanged,"BODY_SHAPE_MUTATED_DURING_ACCESSORY_CORRECTIVE"
    accessory=[name for name in changed if name!=body]
    assert len(accessory)>=6,("INSUFFICIENT_ACTUAL_MESH_TRANSFER",accessory)
    return {
       "schema":"r014.cc0.transfer.source_geometry_uv_material_invariants.v1",
       "status":"PASS_SOURCE_NATIVE_UV_TOPOLOGY_MATERIAL_PRESERVATION_ONLY",
       "cohort":before["sex_macro"],
       "source_before_sha256":before["native_blend_sha256"],
       "source_after_sha256":after["native_blend_sha256"],
       "unchanged_packed_images":len(before["packed_images"]),
       "unchanged_rig_bones":before["rig_bones"],
       "source_actor_mesh_count":len(a),
       "changed_real_accessory_geometry_count":len(accessory),
       "changed_accessory_names":accessory,
       "unchanged_original_body_geometry":True,
       "per_mesh_structural_fields_compared":CONTRACT,
       "strict_surface_topology_hash_invariant":True,
       "strict_original_uv_loop_hash_invariant":True,
       "strict_material_slots_and_polygon_assignments_invariant":True,
       "strict_source_pack_hash_invariant":True,
       "actual_surface_fidelity":"NOT_EVALUATED",
       "inside_outside_and_contact_approval":"HOLD",
       "appearance_photoreal_and_anatomy":"HOLD",
       "motion":"NOT_TESTED_HERE",
       "merge_release":"HOLD"
    }

def selftest():
    before={"sex_macro":"female","rig_bones":163,"source_body_raw_vertices":19158,
      "frame":1,"blender":"4.5.16","packed_images":[{"name":"a","sha256":"X"}],
      "native_blend_sha256":"ORIGINAL",
      "meshes":{}}
    for name in ["R014_female_textured_body"]+["R014_female_accessory"+str(i) for i in range(6)]:
        row={k:"identity" for k in CONTRACT}
        row["is_body"]=name.endswith("_body")
        row["actual_evaluated_geometry"]={
          "vertices":100,"faces":100,"actual_evaluated_world_vertex_hash":"old"}
        before["meshes"][name]=row
    after=deepcopy(before);after["native_blend_sha256"]="CORRECTED"
    for name in list(after["meshes"])[1:]:
        after["meshes"][name]["actual_evaluated_geometry"]["actual_evaluated_world_vertex_hash"]="new"
    assert compare(before,after)["changed_real_accessory_geometry_count"]==6
    negative=deepcopy(after)
    negative["meshes"]["R014_female_accessory0"]["uv_layers"]="CHANGED"
    try:compare(before,negative)
    except AssertionError as e:assert "SOURCE_MESH_CONTRACT_DRIFT" in str(e)
    else:raise AssertionError("FAIL_NEGATIVE_UV_TEST")
    negative=deepcopy(after)
    negative["meshes"]["R014_female_textured_body"]["actual_evaluated_geometry"]["actual_evaluated_world_vertex_hash"]="new"
    try:compare(before,negative)
    except AssertionError as e:assert "BODY_SHAPE_MUTATED" in str(e)
    else:raise AssertionError("FAIL_NEGATIVE_BODY_TEST")
    return "PASS_SYNTHETIC_INVARIANT_POSITIVE_UV_MUTATION_AND_BODY_MUTATION_RED"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--before",type=Path,required=True)
    p.add_argument("--after",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    selftest()
    obj=compare(json.loads(args.before.read_text()),json.loads(args.after.read_text()))
    obj["selftest"]="PASS_SYNTHETIC_NEGATIVE_GUARDS"
    args.out.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
    print("R014_TOPOLOGY_MATERIAL_PARITY",json.dumps(obj,sort_keys=True))
if __name__=="__main__":main()
