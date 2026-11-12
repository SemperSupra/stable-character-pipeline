"""R015 native MPFB inverse-model family bakeoff on real 72-body mesh DoE.
No SMPL-X substitution, no source media, no synthetic measurements substituted
for the original evaluated body geometry. Fail closed on leakage and source drift.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import time
import warnings

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neural_network import MLPRegressor

SOURCE="6ff1eb358f6c1959ced77e79e6dd2406d9a71f49"
NATIVE_MACROS=("height","weight","muscle","proportions")
def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def load(root,shard):
    folder=Path(root)/("shard"+str(shard))
    summary=folder/("native_inverse_doe_shard_"+str(shard)+".json")
    dataset=folder/("native_inverse_doe_samples_"+str(shard)+".jsonl")
    report=json.loads(summary.read_text())
    assert report["source_mpfb_pin"]==SOURCE and report["shard"]==shard
    assert report["status"]=="PASS_REAL_NATIVE_GEOMETRY_DOE_AND_INVERSE_CPU_BASELINES"
    assert report["actual_samples"]==36 and report["distinct_actual_evaluated_shapes"]==36
    rows=[json.loads(x) for x in dataset.read_text().splitlines() if x.strip()]
    assert len(rows)==36
    for i,r in enumerate(rows):
        assert r["case_id"]==f"source_mpbf_{shard}_{i:03d}"
        assert r["gender_macro"]==shard
        assert set(r["macros"])==set(NATIVE_MACROS)
        assert all(math.isfinite(float(r["macros"][k])) and 0<=float(r["macros"][k])<=1 for k in NATIVE_MACROS)
        m=r["measurement"]
        assert len(m["measured_feature_vector"])==13
        assert m["evaluated_vertices"]>1000
        assert all(math.isfinite(float(v)) for v in m["measured_feature_vector"])
    return rows,{"summary_sha256":sha(summary),"sample_dataset_sha256":sha(dataset)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",type=Path,required=True)
    p.add_argument("--profile",choices=("bbox","slices"),required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    f,hash0=load(args.dataset,0)
    m,hash1=load(args.dataset,1)
    rows=f+m
    hashes=[x["measurement"]["evaluated_shape_sha256_rounded_7"] for x in rows]
    assert len(set(hashes))==72, "COLLIDING_GENERATED_GEOMETRY"
    # Same macro tuples across cohorts: grouped index split. Holding out one
    # cohort's row and training the other would leak the target settings.
    original_targets=[tuple(r["macros"][k] for k in NATIVE_MACROS) for r in rows]
    assert all(original_targets[i]==original_targets[36+i] for i in range(36))
    macro_target_hashes=[hashlib.sha256(repr(q).encode()).hexdigest() for q in original_targets]
    X=[]
    for r in rows:
        measures=r["measurement"]["measured_feature_vector"]
        X.append([float(r["gender_macro"])] + list(measures[:3] if args.profile=="bbox" else measures))
    X=np.asarray(X,dtype=np.float64)
    y=np.asarray(original_targets,dtype=np.float64)
    record={
        "schema":"r015.real_mpfb_native_inverse_bakeoff.v1",
        "source_mpfb_sha":SOURCE,
        "generation_run_id":43289442194,
        "original_evaluated_samples":72,
        "gender_group_count":2,
        "source_artifact_digests":{"shard0":hash0,"shard1":hash1},
        "scope":"actual MPFB normalized body controls predicted from original evaluated mesh widths/depths + known phenotype macro class; not prompt or physical-cm error",
        "test_profile":args.profile,
        "input_count":X.shape[1],
        "output_targets":list(NATIVE_MACROS),
        "source_images_present":False,
        "commercial_rights_or_deployment_acceptance":"NOT_TESTED",
        "full_anatomy_or_photorealism":"NOT_TESTED",
        "merge_release":"HOLD",
        "splits":[]
    }
    for seed_shift in (0,1):
        # 27 distinct source macro configurations in train, nine in test,
        # represented twice as separate real geometry variants per cohort.
        train_index=np.asarray([i for i in range(72) if ((i%36+seed_shift)%4)!=0],dtype=int)
        test_index=np.asarray([i for i in range(72) if ((i%36+seed_shift)%4)==0],dtype=int)
        assert len(train_index)==54 and len(test_index)==18
        assert not ({macro_target_hashes[i] for i in train_index} & {macro_target_hashes[i] for i in test_index}),"LEAKED_MACRO_TUPLE"
        assert not ({hashes[i] for i in train_index} & {hashes[i] for i in test_index}),"LEAKED_MESH"
        a=X[train_index];t=X[test_index]
        train_y=y[train_index];test_y=y[test_index]
        mu=a.mean(axis=0);sd=a.std(axis=0)
        sd[sd<1e-8]=1.
        a=(a-mu)/sd
        t=(t-mu)/sd
        models={
            "ridge":Ridge(alpha=0.35,solver="svd"),
            "knn5_distance":KNeighborsRegressor(n_neighbors=5,weights="distance"),
            "random_forest":RandomForestRegressor(n_estimators=100,max_depth=8,min_samples_leaf=2,random_state=seed_shift,n_jobs=1),
            "extra_trees":ExtraTreesRegressor(n_estimators=100,max_depth=8,min_samples_leaf=2,random_state=seed_shift,n_jobs=1),
            "small_mlp":MLPRegressor(hidden_layer_sizes=(24,12),activation="relu",alpha=0.1,
                                     max_iter=350,early_stopping=True,random_state=100+seed_shift,
                                     n_iter_no_change=20),
        }
        means=train_y.mean(axis=0)
        comparisons={"constant_mean":{
            "mae":float(np.mean(np.abs(means-test_y))),
            "fit_seconds":0.0,
            "sample_p90_mean_abs_error":float(np.percentile(np.mean(np.abs(means-test_y),axis=1),90)),
            "per_macro_mae":{k:float(np.mean(np.abs(means[j]-test_y[:,j]))) for j,k in enumerate(NATIVE_MACROS)}
        }}
        for name,model in models.items():
            start=time.perf_counter()
            with warnings.catch_warnings(record=True) as msgs:
                warnings.simplefilter("always")
                model.fit(a,train_y)
            fit_seconds=time.perf_counter()-start
            pred=np.clip(np.asarray(model.predict(t),dtype=np.float64),0.,1.)
            assert pred.shape==test_y.shape and np.isfinite(pred).all()
            abs_err=np.abs(pred-test_y)
            comparisons[name]={
                "mae":float(abs_err.mean()),
                "sample_p90_mean_abs_error":float(np.percentile(abs_err.mean(axis=1),90)),
                "per_macro_mae":{k:float(abs_err[:,j].mean()) for j,k in enumerate(NATIVE_MACROS)},
                "fit_seconds":round(fit_seconds,5),
                "warning_categories":sorted(set(type(msg.message).__name__ for msg in msgs)),
            }
        record["splits"].append({
            "split":seed_shift,"train_samples":len(train_index),"test_samples":len(test_index),
            "train_macro_groups":len({macro_target_hashes[i] for i in train_index}),
            "test_macro_groups":len({macro_target_hashes[i] for i in test_index}),
            "macro_leakage_count":0,"mesh_leakage_count":0,
            "models":{k:{m:(round(v,7) if isinstance(v,float) else {q:round(z,7) for q,z in v.items()} if isinstance(v,dict) else v)
                         for m,v in values.items()} for k,values in comparisons.items()},
        })
    record["status"]="PASS_REAL_NATIVE_MPFB_FAMILY_BAKEOFF_SMALL_HOLDOUT_ONLY"
    record["maxrss_kib_linux"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(record,sort_keys=True,indent=2)+"\n")
    print("R015_NATIVE_MODEL_BAKEOFF",json.dumps(record,sort_keys=True))
if __name__=="__main__":
    main()
