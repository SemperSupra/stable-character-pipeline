"""Compare original source Blender evaluated 3D geometry vs actual GLB cold import.

Native Blender body topology may split vertices at material/UV seams in GLB,
so compare spatial point clouds via symmetric nearest neighbor + actual
triangulated surface area; not raw vertex count or GLB channel count.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

def compare_points(a,b):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    assert a.ndim==b.ndim==2 and a.shape[1]==b.shape[1]==3
    assert np.isfinite(a).all() and np.isfinite(b).all()
    d_ab=cKDTree(b).query(a,k=1,workers=1)[0]
    d_ba=cKDTree(a).query(b,k=1,workers=1)[0]
    # Separate rigid/world placement drift from geometric shape drift.
    ac=a-a.mean(axis=0)
    bc=b-b.mean(axis=0)
    d_centered=np.concatenate([
        cKDTree(bc).query(ac,k=1,workers=1)[0],
        cKDTree(ac).query(bc,k=1,workers=1)[0]])
    combined=np.concatenate([d_ab,d_ba])
    return {
      "source_point_count":len(a),"glb_point_count":len(b),
      "symmetric_nn_mean_world_native":float(combined.mean()),
      "symmetric_nn_p95_world_native":float(np.quantile(combined,.95)),
      "symmetric_nn_max_world_native":float(combined.max()),
      "symmetric_nn_p95_centroid_normalized_native":float(np.quantile(d_centered,.95)),
      "symmetric_nn_max_centroid_normalized_native":float(d_centered.max()),
      "delta_point_centroid_world":(b.mean(axis=0)-a.mean(axis=0)).round(7).tolist()
    }

def evaluate(original,imported):
    assert original["sex"]==imported["sex"]
    assert original["stage"]=="source" and imported["stage"]=="import"
    assert original["source_armature_bones"]==imported["source_armature_bones"]==163
    assert len(original["frames"])==len(imported["frames"])==2
    actor_source=original["frames"][0]["objects"]
    actor_import=imported["frames"][0]["objects"]
    a_names=set(actor_source);b_names=set(actor_import)
    body="R014_"+original["sex"]+"_textured_body"
    assert body in a_names and body in b_names
    keys=sorted(a_names&b_names)
    assert len(keys)>=7,("MISSING_IMPORTED_SOURCE_ASSETS",sorted(a_names-b_names))
    records=[]
    for t in range(2):
        row=[]
        for name in keys:
            a=original["frames"][t]["objects"][name]
            b=imported["frames"][t]["objects"][name]
            spatial=compare_points(a["coords_world"],b["coords_world"])
            area_a=float(a["actual_world_surface_area_blender_squared"])
            area_b=float(b["actual_world_surface_area_blender_squared"])
            drift=abs(area_b-area_a)/max(area_a,1e-8)
            bbox_delta=np.max(np.abs(np.asarray(a["bounds_xyz_native"])-np.asarray(b["bounds_xyz_native"])))
            row.append({"name":name,"source_evaluated_vertices":a["evaluated_vertices"],
                        "imported_evaluated_vertices":b["evaluated_vertices"],
                        "source_surface_area_native_squared":area_a,
                        "import_surface_area_native_squared":area_b,
                        "relative_surface_area_drift":float(drift),
                        "max_absolute_body_extent_drift_native":float(bbox_delta),
                        "source_nonzero_morph_keys":a["nonzero_shape_keys"][:80],
                        "import_nonzero_morph_keys":b["nonzero_shape_keys"][:80],
                        "source_material_slots":a["material_count"],
                        "import_material_slots":b["material_count"],
                        **spatial})
        records.append({"source_frame":original["frames"][t]["frame"],
                        "import_frame":imported["frames"][t]["frame"],
                        "assets":row})
    body_results=[next(r for r in frame["assets"] if r["name"]==body) for frame in records]
    # Tight enough to find major shape/color-draping defects; this is a
    # registration/geometry diagnostic, not an anatomical quality judgement.
    gates={
       "body_area_relative_drift_lt_5pct":all(r["relative_surface_area_drift"]<0.05 for r in body_results),
       "body_symmetric_nn_p95_lt_0_01_native":all(r["symmetric_nn_p95_world_native"]<0.01 for r in body_results),
       "body_symmetric_nn_max_lt_0_05_native":all(r["symmetric_nn_max_world_native"]<0.05 for r in body_results),
       "body_world_extent_abs_drift_lt_0_05_native":all(r["max_absolute_body_extent_drift_native"]<0.05 for r in body_results),
       "source_actor_names_preserved":len(keys)>=7,
    }
    result={
      "schema":"r014.cc0.source_vs_GLTF_actual_mesh_spatial_parity.v1",
      "status":"PASS_SOURCE_GLTF_SPATIAL_EQUIVALENCE_ONLY" if all(gates.values()) else "FAIL_GLTF_SOURCE_MESH_GEOMETRY_FIDELITY",
      "sex_macro":original["sex"],"original_rig_bones":original["source_armature_bones"],
      "source_actor_count":len(a_names),"import_actor_count":len(b_names),
      "source_actor_names_missing":sorted(a_names-b_names),
      "source_actor_names_added":sorted(b_names-a_names),
      "observed_actors":keys,"tested_source_and_imported_frames":2,
      "method":"actual Blender evaluated world-space mesh; bidirectional nearest-neighbor, native triangle area, spatial bounds, imported glTF split vertices allowed",
      "body_checks":gates,
      "body_results":body_results,
      "per_frame_source_vs_GLTF":records,
      "model_deployment":"HOLD",
      "interoperable_anatomical_character":"HOLD",
      "cinematic_appearance":"HOLD",
      "CPE_semantics":"NOT_PROMOTED",
      "merge_release":"HOLD"
    }
    return result

def selftest():
    good={"sex":"female","stage":"source","source_armature_bones":163,
          "frames":[{"frame":1,"objects":{}},{"frame":8,"objects":{}}]}
    imported={"sex":"female","stage":"import","source_armature_bones":163,
              "frames":[{"frame":2,"objects":{}},{"frame":17,"objects":{}}]}
    for fr_a,fr_b in zip(good["frames"],imported["frames"]):
        for name in ["R014_female_textured_body"]+["R014_female_textured_body.accessory"+str(i) for i in range(6)]:
            obj={"coords_world":[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],
                 "actual_world_surface_area_blender_squared":1.,
                 "bounds_xyz_native":[1.,1.,1.],
                 "evaluated_vertices":4,"nonzero_shape_keys":[],"material_count":1}
            fr_a["objects"][name]=obj.copy();fr_b["objects"][name]=obj.copy()
    assert evaluate(good,imported)["status"].startswith("PASS")
    for f in imported["frames"]:
        f["objects"]["R014_female_textured_body"]=dict(f["objects"]["R014_female_textured_body"],
            coords_world=[[0,0,0],[2,0,0],[0,1,0],[0,0,1]])
    assert evaluate(good,imported)["status"].startswith("FAIL"),"FAILED_NEGATIVE_MESH_DISTORTION"
    return "PASS_COLD_GLTF_SPATIAL_POSITIVE_AND_DISTORTION_NEGATIVE"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--imported",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    negative=selftest()
    a=json.loads(args.source.read_text())
    b=json.loads(args.imported.read_text())
    result=evaluate(a,b)
    result["synthetic_negative_selftest"]=negative
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("R014_GLTF_SOURCE_GEOMETRY",json.dumps({
       "status":result["status"],
       "sex":result["sex_macro"],
       "body_checks":result["body_checks"],
       "body_p95": [r["symmetric_nn_p95_world_native"] for r in result["body_results"]],
       "body_area_ratio": [r["relative_surface_area_drift"] for r in result["body_results"]],
       "body_bbox_drift":[r["max_absolute_body_extent_drift_native"] for r in result["body_results"]],
       "missing":result["source_actor_names_missing"]
    },sort_keys=True))
    # The host records the evidence, then it fails closed for promotion
    # instead of treating a valid animation channel as valid character mesh.
    if not result["status"].startswith("PASS"):raise SystemExit("FAIL_CLOSED_GLTF_SOURCE_SPATIAL_PARITY")
if __name__=="__main__":main()
