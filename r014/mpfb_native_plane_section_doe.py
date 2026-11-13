"""R014/R015 exact native mesh plane-section versus vertex-band proxy DoE.

Replays the original 36 public MPFB shapes/cohort; checks exact evaluated
mesh hashes against their original immutable 72-shape dataset. Measures
triangle-plane *closed loops* rather than treating sampled widths as girth.
No anatomical landmark labels or SI calibration are inferred.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import addon_utils
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from mpfb_native_inverse_doe import SOURCE, MACROS, cases, service, fingerprint, measure
from mpfb_mesh_plane_section import plane_section,test_synthetic

FRACTIONS=(0.35,0.48,0.58,0.69,0.80)

def evaluated(obj):
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=ev.to_mesh()
    try:
        verts=np.asarray([tuple(float(v) for v in p.co) for p in mesh.vertices],dtype=np.float64)
        faces=np.asarray([t for polygon in mesh.polygons for t in
                     ((int(polygon.vertices[0]),int(polygon.vertices[k]),int(polygon.vertices[k+1]))
                      for k in range(1,len(polygon.vertices)-1))],dtype=np.int64)
        assert faces.max()<len(verts) and len(verts)>10000 and len(faces)>10000
        return verts,faces
    finally:ev.to_mesh_clear()

def ridge(x,y,train,test):
    x_train=x[train];x_test=x[test];y_train=y[train];y_test=y[test]
    avg=x_train.mean(axis=0);scale=x_train.std(axis=0)
    scale[scale<1e-8]=1.
    z=(x_train-avg)/scale
    zt=(x_test-avg)/scale
    a=np.column_stack([np.ones(len(train)),z])
    b=np.column_stack([np.ones(len(test)),zt])
    reg=np.eye(a.shape[1]);reg[0,0]=0
    w=np.linalg.solve(a.T@a+0.35*reg,a.T@y_train)
    pred=np.clip(b@w,0,1)
    mean=np.broadcast_to(y_train.mean(axis=0),y_test.shape)
    return {
        "features":int(x.shape[1]),
        "mae":round(float(np.abs(pred-y_test).mean()),8),
        "constant_mean_mae":round(float(np.abs(mean-y_test).mean()),8),
        "per_macro_mae":{k:round(float(np.abs(pred[:,i]-y_test[:,i]).mean()),8)
                         for i,k in enumerate(MACROS)}
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard",choices=(0,1),type=int,required=True)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--self-test",action="store_true")
    aa=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    selftest=test_synthetic()
    if aa.self_test:
        print("R014_PLANE_EXACT_SELFTEST",json.dumps(selftest,sort_keys=True))
        return
    # --out is an output JSON *file*, not a directory. Earlier public batch
    # created a directory at this file path and failed only on final receipt.
    assert aa.out.suffix==".json","REQUIRE_EXPLICIT_JSON_OUTPUT_PATH"
    aa.out.parent.mkdir(parents=True,exist_ok=True)
    assert not aa.out.is_dir(),"REJECT_OUTPUT_FILE_DIRECTORY_COLLISION"
    orig=aa.original/f"native_inverse_doe_samples_{aa.shard}.jsonl"
    old=[json.loads(s) for s in orig.read_text().splitlines() if s]
    assert len(old)==36
    original_report=json.loads((aa.original/f"native_inverse_doe_shard_{aa.shard}.json").read_text())
    assert original_report["source_mpfb_pin"]==SOURCE
    assert original_report["actual_samples"]==36
    addon="bl_ext.r014lab.mpfb"
    if addon not in bpy.context.preferences.addons:addon_utils.enable(addon,default_set=False)
    assert addon in bpy.context.preferences.addons
    H=service("mpfb.services.humanservice","HumanService")
    Props=service("mpfb.entities.objectproperties","HumanObjectProperties")
    Target=service("mpfb.services.targetservice","TargetService")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    body=H.create_human()
    assert len(body.data.vertices)>10000
    gathered=[]
    for i,cfg in enumerate(cases(aa.shard)):
        assert old[i]["case_id"]==f"source_mpbf_{aa.shard}_{i:03d}"
        assert all(float(old[i]["macros"][k])==float(cfg["macros"][k]) for k in MACROS)
        Props.set_value("gender",cfg["gender"],entity_reference=body)
        Props.set_value("age",0.65,entity_reference=body)
        for key in MACROS:Props.set_value(key,cfg["macros"][key],entity_reference=body)
        Target.reapply_macro_details(body)
        bpy.context.view_layer.update()
        coords,faces=evaluated(body)
        actual_hash=fingerprint(coords)
        assert actual_hash==old[i]["measurement"]["evaluated_shape_sha256_rounded_7"],(
            "NEW_MESH_DRIFT_FROM_IMMUTABLE_OLD_MPFB",i)
        inherited=measure(coords)
        assert np.max(np.abs(np.array(inherited["measured_feature_vector"])-
                  np.array(old[i]["measurement"]["measured_feature_vector"])))<1e-6
        lo=np.min(coords,axis=0);hi=np.max(coords,axis=0)
        fractions=[]
        for fraction in FRACTIONS:
            z=float(lo[2]+fraction*(hi[2]-lo[2]))
            calc=plane_section(coords,faces,z)
            calc["fraction_of_evaluated_z_extent"]=fraction
            fractions.append(calc)
        gathered.append({"id":old[i]["case_id"],"macros":cfg["macros"],
                         "geometry_hash":actual_hash,
                         "old_band_features":inherited["measured_feature_vector"],
                         "real_triangle_section_profiles":fractions})
    assert len({r["geometry_hash"] for r in gathered})==36
    full_closed=sum(p["closed_loops"]>=1 for r in gathered for p in r["real_triangle_section_profiles"])
    missing=sum(p["closed_loops"]==0 for r in gathered for p in r["real_triangle_section_profiles"])
    open_components=sum(p["open_components"] for r in gathered for p in r["real_triangle_section_profiles"])
    # All sample controls are a priori fixed, original 27 train/9 heldout.
    train=np.asarray([i for i in range(36) if i%4!=0])
    test=np.asarray([i for i in range(36) if i%4==0])
    y=np.asarray([[r["macros"][k] for k in MACROS] for r in gathered],dtype=float)
    original_x=np.asarray([r["old_band_features"] for r in gathered],dtype=float)
    true_loops=np.asarray([[0 if p["largest_closed_perimeter_native_units"] is None
                              else p["largest_closed_perimeter_native_units"]
                              for p in r["real_triangle_section_profiles"]] for r in gathered],dtype=float)
    observed=np.asarray([[float(p["largest_closed_perimeter_native_units"] is not None)
                          for p in r["real_triangle_section_profiles"]] for r in gathered],dtype=float)
    # Missing section is explicit (five validity masks), not silently imputed.
    shape_features=np.column_stack([original_x[:,:3],true_loops,observed])
    compared={
        "legacy_vertex_band_ridge":ridge(original_x,y,train,test),
        "true_triangle_section_ridge_with_missing_masks":ridge(shape_features,y,train,test),
        "bbox_only_ridge":ridge(original_x[:,:3],y,train,test)
    }
    out={
        "schema":"r014.mpfb.actual_closed_mesh_section_morphometry.v1",
        "status":"PASS_NATIVE_SECTION_MEASUREMENT_EVIDENCE_ONLY",
        "source_mpbf_commit":SOURCE,
        "original_generator_run":43289442194,
        "shard":aa.shard,
        "source_actual_shapes":len(gathered),
        "old_36_shape_hashes_replayed_exactly":True,
        "selftest":selftest,
        "section_count":len(gathered)*len(FRACTIONS),
        "with_any_closed_loop":full_closed,
        "without_closed_loop":missing,
        "open_or_ambiguous_components":open_components,
        "native_section_method":"triangle/plane edge interpolation, quantized graph, closed polygons only; no bounding-ellipse substitute",
        "measurement_units":"source Blender native coordinates NOT meters, centimeters or anatomical girths",
        "fractions":list(FRACTIONS),
        "regressors":compared,
        "train_samples":len(train),"heldout_samples":len(test),
        "accessory_surface_qualified":False,
        "semantic_morphological_labels":"NOT_MAPPED",
        "native_3d_rig_and_mesh_acceptance":"HOLD",
        "shape_fidelity_uncertainty":"NOT_CALIBRATED",
        "merge_release":"HOLD",
        "cases":gathered
    }
    aa.out.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print("R014_REAL_PLANE_SECTION_SUMMARY",json.dumps({
       k:v for k,v in out.items() if k!="cases"},sort_keys=True))
    # Abort promotion if topology too incomplete; keep all JSON for diagnosis.
    if full_closed<30:
        raise RuntimeError("TOO_FEW_CLOSED_NATIVE_SECTIONS_FAIL_CLOSED")

if __name__=="__main__":main()
