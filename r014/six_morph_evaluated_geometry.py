"""R014 independent actual-evaluated MPFB morphology audit; no new generation.

The original six-body research receipts logged *base* vertices/bounds, which
are identical by construction for MakeHuman morph targets. This checks whether
the independent reopened Blender dependency graph produces distinct *actual*
human surfaces. Fails closed instead of counting distinct control values.
"""
import argparse
from hashlib import sha256
import json
import math
import sys
from pathlib import Path

import bpy

EXPECTED_SOURCE="6ff1eb358f6c1959ced77e79e6dd2406d9a71f49"

def mesh_evaluated_local(obj):
    dep=bpy.context.evaluated_depsgraph_get()
    actual=obj.evaluated_get(dep)
    m=actual.to_mesh()
    try:
        return [tuple(float(c) for c in v.co) for v in m.vertices]
    finally:
        actual.to_mesh_clear()

def numeric_vector_hash(points):
    digest=sha256()
    for point in points:
        digest.update(",".join(f"{x:.8f}" for x in point).encode("ascii"))
        digest.update(b";")
    return digest.hexdigest()

def bounds(points):
    return [round(max(p[i] for p in points)-min(p[i] for p in points),7) for i in range(3)]

def stats_between(a,b):
    assert len(a)==len(b)>1000
    squared=[sum((ai-bi)**2 for ai,bi in zip(u,v)) for u,v in zip(a,b)]
    return {"rms_euclidean_local_blender_units":round(math.sqrt(sum(squared)/len(squared)),9),
            "max_euclidean_local_blender_units":round(math.sqrt(max(squared)),9),
            "changed_vertex_count_gt_1e_minus_6":sum(x>1e-12 for x in squared),
            "source_vertex_count":len(a)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--blend",type=Path,required=True)
    parser.add_argument("--generation",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    a=parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    assert Path(bpy.data.filepath).resolve()==a.blend.resolve(), "NOT_FRESHLY_REOPENED"
    generation=json.loads(a.generation.read_text(encoding="utf8"))
    assert generation["mpfb_source_revision"]==EXPECTED_SOURCE
    assert generation["status"]=="PASS_NATIVE_MORPH_RIG_ANIMATION_EXPORT_AND_STILLS_ONLY"
    assert len(generation["characters"])==3
    scene=bpy.context.scene
    scene.frame_set(1)
    bpy.context.view_layer.update()
    report={
        "schema":"r014.mpfb.true_evaluated_morphology_doe.v1",
        "shard":generation["shard"],"status":"FAIL_NOT_YET_QUALIFIED",
        "source_blend":a.blend.name,"pinned_mpfb":EXPECTED_SOURCE,
        "basis":"local *evaluated dependency graph* vertices at rest-pose frame 1, not raw mesh vertex coordinates; exact vertex correspondence within one topology",
        "geometry_units":"unscaled Blender model units, NOT anatomical centimeters",
        "source_generation_status":generation["status"],
        "source_actor_count":len(generation["characters"]),
        "actors":[],"pairwise":[],"limits":[
           "Only six manually authored normalized macro presets, not entire human morphology distribution",
           "Local evaluated mesh differences are not metric body-calibration evidence",
           "Hair/skin/material fit and anatomical completeness require separate qualification",
           "Does not generate from untrusted natural language or promote CPE concepts",
           "No real-person attributes or identity measured",
           "No photorealism or realistic contact/gait claim"
        ],"merge_release":"HOLD"}
    frames=[(1,8,16)]
    surfaces={"source":{},"clean":{}}
    for row in generation["characters"]:
        case=row["case"]
        props=row["source_macros"]
        expected_gender=0.0 if generation["shard"]==0 else 1.0
        assert props["gender"]==expected_gender,"SOURCE_GENDER_INVERSION"
        source=bpy.data.objects[case+"_source_body"]
        clean=bpy.data.objects[case+"_clean_body"]
        assert source.type==clean.type=="MESH"
        assert len(source.data.vertices)==row["source_vertices"]
        assert len(clean.data.vertices)==row["clean_vertices"]
        actor={"case":case,"source_macros":props,"mesh":{}}
        for name,obj in [("source",source),("clean",clean)]:
            evaluated=mesh_evaluated_local(obj)
            raw=[tuple(float(c) for c in v.co) for v in obj.data.vertices]
            shapekeys=obj.data.shape_keys
            keys=[] if shapekeys is None else [
                {"name":key.name,"weight":round(float(key.value),8)}
                for key in shapekeys.key_blocks if abs(float(key.value))>1e-7
            ]
            surfaces[name][case]=evaluated
            body_result={
               "raw_local_bounds_xyz":bounds(raw),
               "evaluated_local_bounds_xyz":bounds(evaluated),
               "raw_to_evaluated_rms":(
                   stats_between(raw,evaluated)["rms_euclidean_local_blender_units"]
                   if len(raw)==len(evaluated) else None),
               "raw_vertex_count":len(raw),
               "raw_and_evaluated_topology_matches":len(raw)==len(evaluated),
               "evaluated_mesh_hash_sha256_rounded_8_places":numeric_vector_hash(evaluated),
               "evaluated_vertex_count":len(evaluated),
               "nonzero_shape_key_weights":keys[:40]
            }
            actor["mesh"][name]=body_result
        report["actors"].append(actor)
    # Real native mesh correspondence within a homogeneous topology: do NOT
    # normalize away geometry differences. World actor translation excluded.
    cases=[r["case"] for r in generation["characters"]]
    for i in range(len(cases)):
        for j in range(i+1,len(cases)):
            a_name,b_name=cases[i],cases[j]
            pairs={}
            for which in ("source","clean"):
                pairs[which]=stats_between(surfaces[which][a_name],surfaces[which][b_name])
            report["pairwise"].append({"a":a_name,"b":b_name,"actual_evaluated_surface_difference":pairs})
    # Evidence gates: SOURCE and CLEAN must respond. Allow tiny variation but
    # refuse a false "full morphology coverage" based on macros alone.
    source_distinct=all(p["actual_evaluated_surface_difference"]["source"]["rms_euclidean_local_blender_units"]>1e-5 for p in report["pairwise"])
    clean_distinct=all(p["actual_evaluated_surface_difference"]["clean"]["rms_euclidean_local_blender_units"]>1e-5 for p in report["pairwise"])
    report["all_source_pairs_distinct"]=source_distinct
    report["all_clean_pairs_distinct"]=clean_distinct
    report["status"]="PASS_ACTUAL_EVALUATED_MORPHOLOGY_DISTINCT_STRUCTURAL_ONLY" if (source_distinct and clean_distinct) else "FAIL_MACRO_VALUES_DO_NOT_GENERATE_DISTINCT_EVALUATED_GEOMETRY"
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print("R014_EVALUATED_MORPH",json.dumps(report,sort_keys=True))
    if not report["status"].startswith("PASS_"):
        raise SystemExit("FAIL_CLOSED_TRUE_MESH_VARIATION")

if __name__=="__main__":
    main()
