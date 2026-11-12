#!/usr/bin/env python3
"""R015 public, adult-synthetic prior-art bakeoff. No private assets or real-person data.
Source-native tests are distinguished from data-derived baselines and synthetic smoke.
Nothing here validates photoreal geometry or grants a production acceptance gate.
"""
import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import traceback

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def git_sha(root):
    return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()

def nested_values(o, depth=0):
    if depth>4: return
    if isinstance(o,dict):
        for k,v in o.items():
            yield str(k),v
            yield from nested_values(v,depth+1)
    elif isinstance(o,list):
        for v in o[:15]:
            yield from nested_values(v,depth+1)

def extract_description(o):
    if isinstance(o,dict) and isinstance(o.get("messages"),list):
        for msg in o["messages"]:
            if isinstance(msg,dict) and msg.get("role")=="user":
                return str(msg.get("content",""))
    candidates=[]
    for key,value in nested_values(o):
        if isinstance(value,str) and len(value.strip())>12:
            score=sum(w in key.lower() for w in ("description","input","prompt","text","human"))
            if "### Description:" in value:
                value=value.split("### Description:",1)[1].split("### Shape parameters:")[0].strip()
                score+=10
            candidates.append((score,len(value),value))
    if not candidates:return ""
    candidates.sort(reverse=True)
    return candidates[0][2].strip()

def extract_vector(o):
    if isinstance(o,dict) and isinstance(o.get("messages"),list):
        for msg in reversed(o["messages"]):
            if isinstance(msg,dict) and msg.get("role")=="assistant":
                return parse_vector(msg.get("content"))
    candidates=[]
    for k,v in nested_values(o):
        priority=sum(t in k.lower() for t in ("shape","parameter","beta","output","completion","answer","target"))
        if priority and not isinstance(v,dict):
            a=parse_vector(v)
            if a is not None:candidates.append((priority,a))
    if candidates:return max(candidates,key=lambda t:t[0])[1]
    return None

def parse_vector(v):
    if isinstance(v,list):
        if len(v)>=10 and all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in v[:10]):
            return [float(x) for x in v[:10]]
    if isinstance(v,str):
        if "### Shape parameters:" in v:v=v.split("### Shape parameters:")[-1]
        matches=re.findall(r"[-+]?(?:\d+\.\d+|\d+)(?:[eE][-+]?\d+)?",v)
        if len(matches)>=10:
            nums=[float(x) for x in matches[:10]]
            if all(math.isfinite(x) for x in nums):return nums
    return None

def bodyshapegpt(root,receipt):
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import Ridge
    from sklearn.metrics import mean_absolute_error
    from sklearn.neighbors import NearestNeighbors

    demo=(root/"demo.py").read_text(encoding="utf-8")
    tree=ast.parse(demo)
    parser=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="parse_betas")
    module=ast.Module(body=[parser],type_ignores=[])
    namespace={"re":re}
    exec(compile(module,str(root/"demo.py"),"exec"),namespace)
    original=namespace["parse_betas"]
    prompt_with_number="### Description: An adult 190.5 cm tall. ### Shape parameters: "+str([0.1*i for i in range(10)])
    actual=original(prompt_with_number)
    receipt["upstream_native_parser"]={
        "source":"demo.py parse_betas AST exact upstream function",
        "normal_10_values":len(original("0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0"))==10,
        "description_number_leakage":len(actual)>=1 and actual[0]==190.5,
        "allows_integers_in_answer":len(original("1 2 3 4 5 6 7 8 9 10"))==10,
        "requires_full_exact_10_vector":len(original("0.2 0.3"))==0,
        "note":"Native parser selects first ten decimal numbers in *entire* decoded prompt+answer. Observed malformed returns are source-native behavior, not the learned model's quality."
    }
    path=root/"BodyShapeGPT_dataset.jsonl"
    rows=0; valid=0; err=0; descriptions={}; keyset=None
    with path.open(encoding="utf-8") as f:
        for raw in f:
            if not raw.strip():continue
            rows+=1
            try:
                o=json.loads(raw)
                if keyset is None:keyset=list(o.keys()) if isinstance(o,dict) else ["non_dict"]
                d=extract_description(o)
                vector=extract_vector(o)
                if not d or vector is None:
                    err+=1
                    continue
                valid+=1
                key=hashlib.sha256(d.lower().strip().encode()).hexdigest()
                descriptions.setdefault(key,(d,vector))
            except (ValueError,TypeError,KeyError):
                err+=1
    receipt["dataset"]={
        "source_blob_sha256":sha256(path),"rows":rows,"parsed_pairs":valid,
        "unparsed_rows":err,"unique_casefolded_description_hashes":len(descriptions),
        "json_top_level_fields":keyset,
        "raw_prompts_in_receipt":False
    }
    if len(descriptions)<100:
        receipt["baseline_status"]="BLOCKED_DATA_SCHEMA";return
    train=[];test=[]
    for k,(desc,vector) in sorted(descriptions.items()):
        if int(k[:8],16)%10==0:test.append((desc,vector))
        else:train.append((desc,vector))
    # Bound CPU cost and exact sample count; deterministic partitions before subsampling.
    train=train[:min(len(train),6000)];test=test[:min(len(test),600)]
    if len(test)<50 or len(train)<100:
        receipt["baseline_status"]="BLOCKED_DATA_SPLIT";return
    xs=[x for x,_ in train];ys=np.asarray([y for _,y in train])
    xt=[x for x,_ in test];yt=np.asarray([y for _,y in test])
    vec=TfidfVectorizer(max_features=5000,min_df=2,ngram_range=(1,2),strip_accents="unicode",lowercase=True)
    s=time.monotonic()
    X=vec.fit_transform(xs);T=vec.transform(xt)
    base=np.broadcast_to(ys.mean(axis=0),(len(yt),10))
    baseline_mae=float(np.mean(np.abs(base-yt)))
    reg=Ridge(alpha=10.0,solver="lsqr")
    reg.fit(X,ys);pred=reg.predict(T)
    ridge_mae=float(np.mean(np.abs(pred-yt)))
    nbr=NearestNeighbors(n_neighbors=1,metric="cosine",algorithm="brute",n_jobs=1).fit(X)
    ii=nbr.kneighbors(T,return_distance=False).ravel()
    neigh=ys[ii]
    nn_mae=float(np.mean(np.abs(neigh-yt)))
    elapsed=round(time.monotonic()-s,3)
    receipt["baseline_status"]="PASS_DATA_DERIVED_PROXY_ONLY"
    receipt["comparison"]={
        "training_rows":len(xs),"held_out_rows":len(xt),
        "train_test_split":"sha256(normalized prompt) % 10, disjoint by exact normalized prompt, then bounded sample",
        "methods":["train_mean","TFIDF_Ridge","TFIDF_nearest_neighbor"],
        "mean_absolute_error_beta":{
            "mean":round(baseline_mae,6),"ridge":round(ridge_mae,6),"nearest_neighbor":round(nn_mae,6)
        },
        "ridge_to_mean_mae_ratio":round(ridge_mae/baseline_mae,5) if baseline_mae else None,
        "nearest_to_mean_mae_ratio":round(nn_mae/baseline_mae,5) if baseline_mae else None,
        "ridge_per_coefficient_mae":[round(float(v),5) for v in np.mean(np.abs(pred-yt),axis=0)],
        "training_and_inference_seconds":elapsed,
        "interpretation":"These are CPU text-regression baselines on BodyShapeGPT's released pairs, NOT BodyShapeGPT Llama-3/LoRA inference, NOT geometric accuracy or metric measurements."
    }
    weights=list((root/"weights").glob("*"))
    receipt["native_inference"]={
        "status":"BLOCKED_EXTERNAL_MODEL_ASSETS_AND_ACCELERATOR",
        "repository_weight_files":[f.name for f in weights],
        "base_model":"meta-llama/Meta-Llama-3-8B (access-controlled, 8B, CUDA 4-bit in upstream demo)",
        "lora":"OneDrive-linked safetensors not included in GitHub repo",
        "runner_gpu_required_by_upstream_demo":True,
        "native_llm_executed":False
    }

def semantify(root,receipt):
    import torch
    import torch.nn as nn
    from typing import List, Union
    filename=root/"semantify/train/mapper_module.py"
    source=filename.read_text(encoding="utf-8")
    tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="C2M")
    # Execute ONLY upstream C2M architecture class, not its hydra/Lightning training or
    # render/asset loader graph. This is a source-native MLP forward/training smoke.
    ns={"nn":nn,"List":List,"Union":Union}
    exec(compile(ast.Module(body=[cls],type_ignores=[]),str(filename),"exec"),ns)
    torch.manual_seed(42)
    model=ns["C2M"](num_stats=6,hidden_size=[32,16],out_features=10,num_hiddens=1).cpu()
    x=torch.randn(512,6)
    true=torch.tanh(x@torch.randn(6,10)*0.65)
    xtrain,xval=x[:400],x[400:]
    ytrain,yval=true[:400],true[400:]
    opt=torch.optim.Adam(model.parameters(),lr=0.006)
    criterion=nn.MSELoss()
    with torch.no_grad():
        before=float(criterion(model(xval),yval))
        mean_base=float(criterion(yval.mean(dim=0,keepdim=True).expand_as(yval),yval))
    start=time.monotonic()
    model.train()
    for _ in range(175):
        opt.zero_grad(set_to_none=True)
        loss=criterion(model(xtrain),ytrain)
        loss.backward();opt.step()
    model.eval()
    with torch.no_grad():
        after=float(criterion(model(xval),yval))
        finite=bool(torch.isfinite(model(xval)).all().item())
        dim=list(model(xval).shape)
    receipt["native_mapper"]= {
        "status":"PASS_NATIVE_ARCHITECTURE_SYNTHETIC_TRAINING_ONLY" if after<before and finite else "FAIL_NATIVE_ARCHITECTURE_SMOKE",
        "code_path":"semantify/train/mapper_module.py::C2M (AST isolated exact class)",
        "source_sha256":sha256(filename),
        "torch_version":torch.__version__,
        "input_descriptor_dimensions":6,
        "output_shape_dimensions":10,
        "output_tensor_shape":dim,
        "synthetic_val_mse_before":round(before,6),
        "synthetic_val_mse_after":round(after,6),
        "synthetic_val_mean_mse":round(mean_base,6),
        "training_iterations":175,
        "training_seconds":round(time.monotonic()-start,3),
        "native_semantify_pretrained_mapper_executed":False,
        "native_clIP_descriptor_evaluation":False,
        "native_geometry_render_executed":False,
        "note":"Uses original C2M PyTorch class and SGD over a deterministic analytic toy relationship, not the published trained weights/CLIP renders. Establishes CPU trainability only."
    }
    receipt["artifact_dependency_gate"]={
        "status":"BLOCKED_NATIVE_GEOMETRY_AND_PRETRAINED_CHECKPOINT",
        "mapper_download_script_sha256":sha256(root/"get_mappers.sh"),
        "script_requires_unverified_external_google_drive_archive":True,
        "upstream_script_disables_TLS_verification":("--no-check-certificate" in (root/"get_mappers.sh").read_text()),
        "smplx_native_assets_requires_separate_registration":True,
        "pretrained_mapper_tested":False,
        "license_review":"Semantify MIT code; weights and underlying SMPL/SMPL-X model assets have independent rights and registration."
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--lane",choices=["bodyshapegpt","semantify"],required=True)
    p.add_argument("--source",required=True)
    p.add_argument("--expected-sha",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    root=Path(a.source);sha=git_sha(root)
    if sha!=a.expected_sha:
        raise SystemExit(f"FAIL_CLOSED pinned SHA mismatch: {sha} != {a.expected_sha}")
    receipt={
        "schema":"r015.prior_art.bakeoff.v1",
        "lane":a.lane,
        "source":str(root),
        "upstream_commit":sha,
        "python":platform.python_version(),
        "cpu_count":os.cpu_count(),
        "start_epoch":int(time.time()),
        "scope":"public research / synthetic adult morphology / no private assets",
        "merge_release_gate":"HOLD",
        "native_mesh_qualification":"NOT_PERFORMED"
    }
    try:
        (bodyshapegpt if a.lane=="bodyshapegpt" else semantify)(root,receipt)
        receipt["job_status"]="COMPLETED_WITH_BOUNDARIES"
    except Exception as e:
        receipt["job_status"]="FAILED"
        receipt["error_class"]=type(e).__name__
        receipt["error_details"]=str(e)[:900]
        traceback.print_exc()
    out=Path(a.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    print(json.dumps(receipt,indent=2,sort_keys=True))
    if receipt["job_status"]=="FAILED":
        raise SystemExit(1)

if __name__=="__main__":
    main()
