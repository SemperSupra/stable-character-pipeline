#!/usr/bin/env python3
"""BodyShapeGPT published corpus: prompt/shape connected-component leakage audit.
Research-only, hash-only receipts. No native Llama inference or 3D meshes.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from bakeoff import extract_description,extract_vector,sha256

PIN="758bf5a1b3dbd12984de6f68ad4d3bf8c95ef409"
def digest_text(s):
    return hashlib.sha256(s.encode("utf8")).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    root=Path(a.source)
    got=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if got!=PIN:raise SystemExit("FAIL_SOURCE_SHA_DRIFT")
    path=root/"BodyShapeGPT_dataset.jsonl"
    rows=[]
    parse_errors=0
    for line in path.open(encoding="utf8"):
        if not line.strip():continue
        item=json.loads(line)
        desc=extract_description(item)
        vector=extract_vector(item)
        if not desc or vector is None or len(vector)!=10 or not all(math.isfinite(x) for x in vector):
            parse_errors+=1
            continue
        pkey=" ".join(desc.casefold().split())
        # Quantize solely for leakage grouping. 1e-5 native-coefficient resolution.
        skey=",".join(f"{v:.5f}" for v in vector)
        rows.append((desc,vector,pkey,skey))
    n=len(rows)
    parent=list(range(n));size=[1]*n
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:
            if size[a]<size[b]:a,b=b,a
            parent[b]=a;size[a]+=size[b]
    prompt_seen={};shape_seen={}
    for i,(desc,vec,pk,sk) in enumerate(rows):
        if pk in prompt_seen:union(i,prompt_seen[pk])
        else:prompt_seen[pk]=i
        if sk in shape_seen:union(i,shape_seen[sk])
        else:shape_seen[sk]=i
    components=defaultdict(list)
    for i in range(n):components[find(i)].append(i)
    component_keys={c:digest_text("".join(sorted(rows[i][3] for i in ix)[:4])) for c,ix in components.items()}
    all_prompt_shapes=defaultdict(set)
    all_shape_prompts=defaultdict(set)
    for desc,vec,pk,sk in rows:
        all_prompt_shapes[pk].add(sk)
        all_shape_prompts[sk].add(pk)
    receipt={
        "schema":"r015.bodyshapegpt.group_holdout.v1",
        "scope":"published public text+SMPL-X betas only; no original LoRA inference or 3D body mesh",
        "source_pin":got,
        "dataset_sha256":sha256(path),
        "source_rows":n,
        "parse_errors":parse_errors,
        "unique_normalized_prompts":len(all_prompt_shapes),
        "unique_rounded_1e-5_shape_vectors":len(all_shape_prompts),
        "prompts_with_conflicting_shape_vectors":sum(len(v)>1 for v in all_prompt_shapes.values()),
        "shape_vectors_with_multiple_prompts":sum(len(v)>1 for v in all_shape_prompts.values()),
        "connected_component_count":len(components),
        "largest_component_rows":max(map(len,components.values())) if components else 0,
        "multiple_prompts_and_shapes_protected_by_components":True,
        "metric":"mean absolute error in 10 native SMPL-X betas (not mesh metric)",
        "merge_release_gate":"HOLD",
        "evaluation":[],
        "benchmark_warnings":[]
    }
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import Ridge
    import numpy as np
    for protocol in ("prompt_holdout","shape_holdout","component_holdout"):
        for seed in (20261112,20261113):
            if protocol=="component_holdout":
                ids=[component_keys[find(i)] for i in range(n)]
            elif protocol=="shape_holdout":ids=[x[3] for x in rows]
            else:ids=[x[2] for x in rows]
            # Stable hashed IDs before any bounding, with common 20% target.
            ix_train=[];ix_test=[]
            for i,key in enumerate(ids):
                b=int(digest_text(str(seed)+":"+key)[:8],16)%5
                (ix_test if b==0 else ix_train).append(i)
            if len(ix_train)<500 or len(ix_test)<100:
                receipt["benchmark_warnings"].append({"protocol":protocol,"seed":seed,"problem":"component imbalance or insufficient split","train":len(ix_train),"test":len(ix_test)})
                continue
            # Stable sampling over unique source records. Raw descriptions never logged.
            def choose(ix,count):
                return sorted(ix,key=lambda i:digest_text(str(seed)+":"+str(i)+":"+rows[i][2]))[:count]
            tr=choose(ix_train,6500)
            te=choose(ix_test,1000)
            x=[rows[i][0] for i in tr]
            y=np.asarray([rows[i][1] for i in tr],dtype=np.float64)
            xt=[rows[i][0] for i in te]
            yt=np.asarray([rows[i][1] for i in te],dtype=np.float64)
            seen_prompt={rows[i][2] for i in tr}
            seen_shape={rows[i][3] for i in tr}
            leakage={
                "test_prompt_overlap_count":sum(rows[i][2] in seen_prompt for i in te),
                "test_shape_overlap_count":sum(rows[i][3] in seen_shape for i in te)
            }
            t0=time.monotonic()
            mean=y.mean(axis=0)
            evals={"train_mean":float(np.mean(np.abs(yt-mean)))}
            for label,options in [
                ("tfidf_word_ridge",{"analyzer":"word","ngram_range":(1,2),"min_df":2,"max_features":8000}),
                ("tfidf_char_ridge",{"analyzer":"char","ngram_range":(3,5),"min_df":3,"max_features":14000}),
            ]:
                enc=TfidfVectorizer(**options)
                mat=enc.fit_transform(x)
                testmat=enc.transform(xt)
                m=Ridge(alpha=10.0,solver="lsqr").fit(mat,y)
                estimate=m.predict(testmat)
                err=np.abs(estimate-yt)
                evals[label]=float(np.mean(err))
                evals[label+"_p90_sample_mean_error"]=float(np.percentile(err.mean(axis=1),90))
            elapsed=time.monotonic()-t0
            receipt["evaluation"].append({
                "protocol":protocol,
                "seed":seed,
                "train":len(tr),
                "test":len(te),
                "leakage":leakage,
                "mae":{k:round(v,6) for k,v in evals.items()},
                "relative_word_vs_mean":round(evals["tfidf_word_ridge"]/evals["train_mean"],5),
                "relative_char_vs_mean":round(evals["tfidf_char_ridge"]/evals["train_mean"],5),
                "fitting_elapsed_seconds":round(elapsed,3),
            })
    receipt["status"]="PASS_GROUP_AWARE_PROXY_ONLY" if len(receipt["evaluation"])>=2 else "BLOCKED_GROUP_DATA"
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(out.read_text())
    if receipt["status"].startswith("BLOCKED"):raise SystemExit(1)

if __name__=="__main__":main()
