"""R015 independent, truly NEW native MPFB morphology OOD benchmark.

No relabeling of the historical 72 shapes as fresh holdouts: this worker
generates *new* official MPFB evaluated meshes for 24 untrained macro tuples.
Train/calibrate on disjoint 54/18 of the original 72 actual 3D shapes; evaluate
the new source geometry separately. Historical framework/mesh still pinned.
"""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import bpy
import addon_utils
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from mpfb_native_inverse_doe import service, measure, vertices, MACROS, SOURCE, radical_inverse

def digest(p):
    h=sha256()
    with open(p,"rb") as f:
        for part in iter(lambda:f.read(1<<20),b""): h.update(part)
    return h.hexdigest()

def new_cases():
    designs=[]
    # Deliberately outside the original 0.15..0.85 random grid.
    for axis in range(4):
        for v in (0.03,0.97):
            x=[0.50]*4
            x[axis]=v
            designs.append(("extreme_single",x))
    paired=[
        ((0,1),(0.03,0.97)),((0,1),(0.97,0.03)),
        ((2,3),(0.03,0.97)),((2,3),(0.97,0.03))
    ]
    for (a,b),(v0,v1) in paired:
        x=[0.50]*4;x[a]=v0;x[b]=v1
        designs.append(("extreme_interaction",x))
    # Interior interpolation cases distinct from Halton original 36 targets.
    for i in range(39,47):
        x=[round(0.32+0.36*radical_inverse(i,b),7) for b in (2,3,5,7)]
        designs.append(("interior_novel",x))
    assert len(designs)==20 and len({tuple(x) for _,x in designs})==20
    return designs

def original_train(root):
    rows=[]; hashes={}
    for sex in (0,1):
        path=Path(root)/f"shard{sex}"/f"native_inverse_doe_samples_{sex}.jsonl"
        report=path.with_name(f"native_inverse_doe_shard_{sex}.json")
        doc=json.loads(report.read_text())
        assert doc["source_mpfb_pin"]==SOURCE
        assert doc["actual_samples"]==36 and doc["distinct_actual_evaluated_shapes"]==36
        cohort=[json.loads(x) for x in path.read_text().splitlines() if x]
        assert len(cohort)==36 and all(r["gender_macro"]==sex for r in cohort)
        rows.extend(cohort)
        hashes[f"source_{sex}_jsonl_sha256"]=digest(path)
        hashes[f"source_{sex}_report_sha256"]=digest(report)
    assert len(rows)==72
    old={tuple(float(r["macros"][k]) for k in MACROS) for r in rows}
    assert len(old)==36
    return rows,old,hashes

def fit_ridge(X,y,train,cal,profile):
    mask=np.asarray([0,1,2,3] if profile=="bbox" else list(range(14)),dtype=int)
    x=X[:,mask]
    mu=x[train].mean(axis=0)
    sd=x[train].std(axis=0)
    sd[sd<1e-8]=1.
    normalized=(x-mu)/sd
    A=np.column_stack([np.ones(len(train)),normalized[train]])
    eye=np.eye(A.shape[1]);eye[0,0]=0
    W=np.linalg.solve(A.T@A+0.35*eye,A.T@y[train])
    def pred(newx):
        norm=(np.asarray(newx)[:,mask]-mu)/sd
        return np.clip(np.column_stack([np.ones(len(norm)),norm])@W,0,1)
    calib=pred(X[cal])
    abs_err=np.abs(calib-y[cal])
    # Symmetric marginal interval, finite-sample conformal quantile:
    # n=18, 90% ceil((n+1)*.90)=18; deliberately conservative.
    def quantile(a):
        v=np.sort(a)
        return float(v[min(len(v),int(math.ceil((len(v)+1)*.90)))-1])
    radii=np.asarray([quantile(abs_err[:,i]) for i in range(4)])
    z=normalized[train];zc=normalized[cal]
    cal_nnd=np.sqrt(((zc[:,None,:]-z[None,:,:])**2).sum(axis=2)).min(axis=1)
    threshold=float(np.quantile(cal_nnd,0.95))
    return pred,radii,mu,sd,z,threshold,{
      "calibration_samples":len(cal),"train_samples":len(train),
      "feature_count":len(mask),"calibration_mae":round(float(abs_err.mean()),7),
      "calibration_90pct_symmetric_native_control_radii":[round(float(v),7) for v in radii],
      "calibration_nnd_95pct_threshold":round(threshold,7),
      "calibration_90pct_marginal_empirical_coverage":[round(float(np.mean(abs_err[:,i]<=radii[i])),5) for i in range(4)]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard",required=True,type=int,choices=(0,1))
    p.add_argument("--original",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args(sys.argv[sys.argv.index("--")+1:])
    a.out.mkdir(parents=True,exist_ok=True)
    old,source_controls,hashes=original_train(a.original)
    design=new_cases()
    assert not any(tuple(x) in source_controls for _,x in design),"TRAIN_TEST_CONTROL_LEAK"
    addon="bl_ext.r014lab.mpfb"
    if addon not in bpy.context.preferences.addons:
        addon_utils.enable(addon,default_set=False)
    assert addon in bpy.context.preferences.addons
    Human=service("mpfb.services.humanservice","HumanService")
    Props=service("mpfb.entities.objectproperties","HumanObjectProperties")
    Target=service("mpfb.services.targetservice","TargetService")
    bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
    obj=Human.create_human()
    def assign(x):
        Props.set_value("gender",float(a.shard),entity_reference=obj)
        Props.set_value("age",0.65,entity_reference=obj)
        for k,v in zip(MACROS,x):
            assert 0<=v<=1 and math.isfinite(v)
            Props.set_value(k,v,entity_reference=obj)
        Target.reapply_macro_details(obj)
        bpy.context.view_layer.update()
    cases=[]
    for i,(group,x) in enumerate(design):
        assign(x)
        measured=measure(vertices(obj))
        cases.append({"case":i,"group":group,
             "source_controls":dict(zip(MACROS,x)),
             "native_measured_features":measured["measured_feature_vector"],
             "source_evaluated_mesh_digest":measured["evaluated_shape_sha256_rounded_7"],
             "evaluated_vertex_count":measured["evaluated_vertices"],
             "xspan":measured["native_xspan"],"zspan":measured["native_zspan"]})
    assign(design[0][1])
    replay=measure(vertices(obj))
    assert replay["evaluated_shape_sha256_rounded_7"]==cases[0]["source_evaluated_mesh_digest"],"MACRO_REPLAY_FAIL"
    assert len({x["source_evaluated_mesh_digest"] for x in cases})==20,"NON_DISTINCT_NEW_GEOMETRY"
    assert not ({x["source_evaluated_mesh_digest"] for x in cases} &
                {r["measurement"]["evaluated_shape_sha256_rounded_7"] for r in old}),"ORIGINAL_GEOMETRY_LEAK"
    X=np.asarray([[float(r["gender_macro"])] +
       list(r["measurement"]["measured_feature_vector"]) for r in old],dtype=float)
    y=np.asarray([[r["macros"][k] for k in MACROS] for r in old],dtype=float)
    testX=np.asarray([[float(a.shard)]+r["native_measured_features"] for r in cases],dtype=float)
    testY=np.asarray([[r["source_controls"][k] for k in MACROS] for r in cases],dtype=float)
    # Preserve original paired-shard macro holdout grouping by matching local index.
    train=np.asarray([i for i in range(72) if (i%36)%4!=0])
    cal=np.asarray([i for i in range(72) if (i%36)%4==0])
    assert len(train)==54 and len(cal)==18
    assert not ({tuple(y[i]) for i in train}&{tuple(y[i]) for i in cal})
    models={}
    for prof in ("bbox","slices"):
        predictor,radii,mu,sd,z,threshold,calibr=fit_ridge(X,y,train,cal,prof)
        estimate=predictor(testX)
        errors=np.abs(estimate-testY)
        mask=np.asarray([0,1,2,3] if prof=="bbox" else list(range(14)))
        normalized=(testX[:,mask]-mu)/sd
        nnd=np.sqrt(((normalized[:,None,:]-z[None,:,:])**2).sum(axis=2)).min(axis=1)
        fail_distance=nnd>threshold
        coverage=((testY>=np.clip(estimate-radii,0,1))&(testY<=np.clip(estimate+radii,0,1)))
        # No significance claim from these 20 chosen examples.
        models[prof]={
            "train_and_calibration":calibr,
            "ood_distance_flags":int(fail_distance.sum()),
            "ood_distance_flags_by_design":{group:int(sum(bool(fail_distance[i]) for i,v in enumerate(cases) if v["group"]==group)) for group in sorted({r["group"] for r in cases})},
            "test_mae_all":round(float(errors.mean()),7),
            "test_mae_by_design":{group:round(float(errors[[i for i,r in enumerate(cases) if r["group"]==group]].mean()),7) for group in sorted({r["group"] for r in cases})},
            "test_90pct_interval_coverage_all":round(float(coverage.mean()),5),
            "test_90pct_interval_coverage_by_design":{group:round(float(coverage[[i for i,r in enumerate(cases) if r["group"]==group]].mean()),5) for group in sorted({r["group"] for r in cases})},
            "per_macro_mae":{k:round(float(errors[:,j].mean()),7) for j,k in enumerate(MACROS)},
            "test_predictions":[{"case":r["case"],"group":r["group"],"yhat":[round(float(v),7) for v in estimate[i]],
                                 "nearest_train_feature_distance":round(float(nnd[i]),6),
                                 "abstain_ood":bool(fail_distance[i])} for i,r in enumerate(cases)],
        }
    receipt={
       "schema":"r015.native_mpfb_out_of_distribution.v1",
       "status":"PASS_REAL_UNSEEN_SOURCE_NATIVE_MESH_STRESS_EVIDENCE_ONLY",
       "source_sha":SOURCE,"original_72_shape_generation_run":43289442194,
       "original_training_digests":hashes,
       "shard":a.shard,"actual_new_shapes":len(cases),
       "novel_interior_cases":sum(r["group"]=="interior_novel" for r in cases),
       "novel_extreme_cases":sum(r["group"]!="interior_novel" for r in cases),
       "actual_shape_duplicate_count":0,"source_macro_overlap_count":0,
       "baseline_replay_exact_mesh_hash":True,
       "models":models,
       "novel_genuine_mesh_test_cases":cases, # public synthetic full geometry features; no private images
       "native_body_units":"unscaled Blender units, NOT cm",
       "age_macro":"0.65 not proof of chronological adulthood",
       "recognized_CPE_concepts_or_generation_policy":"NOT_EXECUTED",
       "real_3D_human_photorealism":"NOT_QUALIFIED",
       "merge_release":"HOLD"
    }
    (a.out/f"native_ood_{a.shard}.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print("R015_REAL_NATIVE_OOD",json.dumps(receipt,sort_keys=True))
    print("PASS_REAL_UNSEEN_NATIVE_MESH_OOD_TEST",a.shard)
if __name__=="__main__":
    main()
