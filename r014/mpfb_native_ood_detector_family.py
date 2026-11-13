"""R015 model-agnostic OOD detector bakeoff on actual native MPFB shape geometry.

Separate geometry generator (Blender) and detector family runner (public CPU).
The design-control labels disclose artificial boundary examples only; their
detection is not evidence of medically accurate morphology or real-world
out-of-distribution coverage.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import numpy as np
from sklearn.covariance import LedoitWolf
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA

SOURCE="6ff1eb358f6c1959ced77e79e6dd2406d9a71f49"
def hashfile(p):
    h=sha256()
    with Path(p).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):h.update(block)
    return h.hexdigest()

def read_old(root):
    rows=[];sha={}
    for sex in (0,1):
        p=Path(root)/f"shard{sex}"/f"native_inverse_doe_samples_{sex}.jsonl"
        meta=p.parent/f"native_inverse_doe_shard_{sex}.json"
        m=json.loads(meta.read_text())
        assert m["source_mpfb_pin"]==SOURCE and m["actual_samples"]==36
        data=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        assert len(data)==36
        rows.extend(data)
        sha[f"{sex}_jsonl_sha256"]=hashfile(p)
        sha[f"{sex}_meta_sha256"]=hashfile(meta)
    assert len(rows)==72
    oldhashes={r["measurement"]["evaluated_shape_sha256_rounded_7"] for r in rows}
    assert len(oldhashes)==72
    return rows,oldhashes,sha

def analyse(args):
    old,oldhashes,original_sha=read_old(args.original)
    new=json.loads(args.new.read_text())
    assert new["schema"]=="r015.native_mpfb_out_of_distribution.v1"
    assert new["status"]=="PASS_REAL_UNSEEN_SOURCE_NATIVE_MESH_STRESS_EVIDENCE_ONLY"
    assert new["source_sha"]==SOURCE and new["actual_new_shapes"]==20
    assert new["shard"]==args.shard
    cases=new["novel_genuine_mesh_test_cases"]
    assert len(cases)==20
    assert len({x["source_evaluated_mesh_digest"] for x in cases})==20
    assert not ({x["source_evaluated_mesh_digest"] for x in cases}&oldhashes)
    assert sorted(x["case"] for x in cases)==list(range(20))
    labels=np.array([x["group"]!="interior_novel" for x in cases])
    assert labels.sum()==12 and (~labels).sum()==8
    out={
        "schema":"r015.real_source_native_morphology_ood_family.v1",
        "status":"NOT_TESTED",
        "shard":args.shard,
        "geometry_source":"actual MPFB evaluated native meshes generated on disposable Blender, public synthetic adult designs",
        "original_72_shape_sha":original_sha,
        "fresh_20_shape_receipt_sha256":hashfile(args.new),
        "genuine_independent_new_native_shape_count":len(cases),
        "new_mesh_duplicate_count":0,
        "training_samples":54,"calibration_samples":18,
        "designed_extreme_native_macro_cases":12,
        "designed_interior_native_macro_cases":8,
        "decision_budget":"95th percentile of 18 heldout calibration score values (approx 1/18 empirical alerts)",
        "qualification_scope":"native geometric feature novelty versus intentionally out-of-original-control-range design, not adult body population OOD/identity/fairness/physical dimensions",
        "detectors":{},
        "acceptance":"HOLD_NO_REAL_DOMAIN_VALIDATION",
        "model_promotion":"HOLD",
        "merge_release":"HOLD",
    }
    for features in ("bbox","slices"):
        cols=[0,1,2,3] if features=="bbox" else list(range(14))
        X=np.asarray([[float(x["gender_macro"])]+list(x["measurement"]["measured_feature_vector"]) for x in old],dtype=np.float64)
        T=np.asarray([[float(args.shard)]+list(x["native_measured_features"]) for x in cases],dtype=np.float64)
        assert X.shape==(72,14) and T.shape==(20,14)
        train=[i for i in range(72) if i%36%4!=0]
        cal=[i for i in range(72) if i%36%4==0]
        train_controls={tuple(old[i]["macros"].values()) for i in train}
        cal_controls={tuple(old[i]["macros"].values()) for i in cal}
        assert not (train_controls&cal_controls)
        xa=X[train][:,cols];xc=X[cal][:,cols];xt=T[:,cols]
        mu=xa.mean(axis=0);sd=xa.std(axis=0);sd[sd<1e-8]=1.
        xa=(xa-mu)/sd;xc=(xc-mu)/sd;xt=(xt-mu)/sd
        # Four mechanistically distinct unsupervised detectors. All fit only on
        # train, threshold only on distinct calibration rows. No OOD labels fed.
        cov=LedoitWolf().fit(xa)
        iso=IsolationForest(n_estimators=200,random_state=1315,n_jobs=1,contamination="auto").fit(xa)
        nn=NearestNeighbors(n_neighbors=5).fit(xa)
        ncomp=min(3,len(cols)-1,len(xa)-1)
        pca=PCA(n_components=ncomp,svd_solver="full").fit(xa)
        def pca_residual(z):
            d=z-pca.inverse_transform(pca.transform(z))
            return np.linalg.norm(d,axis=1)
        scores={
            "shrinkage_mahalanobis":(cov.mahalanobis(xc),cov.mahalanobis(xt)),
            "isolation_forest":(-iso.score_samples(xc),-iso.score_samples(xt)),
            "fifth_nearest_feature":(nn.kneighbors(xc,return_distance=True)[0][:,-1],
                                     nn.kneighbors(xt,return_distance=True)[0][:,-1]),
            "pca_three_rank_reconstruction":(pca_residual(xc),pca_residual(xt)),
        }
        prof={}
        for name,(c,t) in scores.items():
            assert np.isfinite(c).all() and np.isfinite(t).all()
            threshold=float(np.quantile(c,0.95))
            alert=t>threshold
            calib_alert=c>threshold
            sensitivity=float(alert[labels].mean())
            falses=float(alert[~labels].mean())
            prof[name]={
               "calibration_threshold":round(threshold,8),
               "calibration_alerts":int(calib_alert.sum()),
               "new_20_alerts":int(alert.sum()),
               "new_12_designed_extremes_flagged":int(alert[labels].sum()),
               "new_8_interior_false_alerts":int(alert[~labels].sum()),
               "extreme_design_sensitivity":round(sensitivity,5),
               "interior_design_false_alarm_rate":round(falses,5),
               "empirical_false_positive_control_scope":"18 source-native heldout controls, not production population",
               "novelty_score_high_is_more_anomalous":True,
               "test_scores":[round(float(v),6) for v in t],
               "test_flagged":[bool(v) for v in alert],
            }
        out["detectors"][features]=prof
    out["status"]="PASS_TRUE_NATIVE_GEOMETRY_MODEL_OOD_COMPARISON_EVIDENCE_ONLY"
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("R015_REAL_OOD_FAMILY",json.dumps(out,sort_keys=True))
    print("PASS_NATIVE_FAMILY_4_DETECTORS_BBOX_SLICES",args.shard)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--shard",type=int,choices=(0,1),required=True)
    p.add_argument("--original",type=Path,required=True)
    p.add_argument("--new",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    analyse(p.parse_args())
if __name__=="__main__":main()
