#!/usr/bin/env python3
"""R015 PyTorch uplift comparison on immutable, ephemeral converted SafeTensors.
The original published pickle is never loaded on the modern target framework.
"""
import argparse
import ast
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import List,Union

EXPECTED_SOURCE="78b001d3dc4ea4efa428e3aff1213cefddf6ebd8"
EXPECTED_ORIGINAL_CKPT="7bb79747504919656ecacb120b5be70b51b6faac1535d1cfd7f46b1401a3ed7b"
EXPECTED_CLIP="40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af"

def sha_file(path):
    h=sha256()
    with Path(path).open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""):h.update(c)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    for name in ("source","weights","conversion_receipt","reference","out"):ap.add_argument("--"+name.replace("_","-"),required=True)
    p=ap.parse_args()
    import torch
    import torch.nn as nn
    from safetensors.torch import load_file
    torch.set_num_threads(2)
    result={
        "schema":"r015.rolling_framework_uplift.safetensors.v1",
        "status":"BLOCKED_OR_FAILED",
        "torch_version":torch.__version__,
        "torch_cuda_build":torch.version.cuda,
        "device":"cpu",
        "original_ckpt_sha256":EXPECTED_ORIGINAL_CKPT,
        "source":"Omergral/Semantify@"+EXPECTED_SOURCE,
        "native_geometry_tested":False,
        "native_language_model_tested":False,
        "mode":"modern native source class loaded only from hash verified tensor-only SafeTensors converted by pinned PyTorch2.5.1 restricted deserializer",
        "third_party_asset_redistributed":False,
        "merge_release":"HOLD",
    }
    try:
        source=Path(p.source)
        got=subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()
        if got!=EXPECTED_SOURCE:raise ValueError("SOURCE_DRIFT")
        conversion=json.loads(Path(p.conversion_receipt).read_text(encoding="utf8"))
        if conversion.get("safe_tensor_export",{}).get("original_checkpoint_sha256")!=EXPECTED_ORIGINAL_CKPT:
            raise ValueError("CONVERSION_CKPT_MISMATCH")
        if conversion.get("safe_load_mode")!="weights_only_explicit_audited_omegaconf_2_3_0_globals":
            raise ValueError("UNSAFE_CONVERTER")
        if not conversion.get("torch_version","").startswith("2.5.1"):
            raise ValueError("UNKNOWN_CONVERTER_TORCH")
        digest=sha_file(p.weights)
        if digest!=conversion["safe_tensor_export"]["sha256"]:raise ValueError("SAFE_TENSOR_HASH_MISMATCH")
        result["safe_tensor_sha256"]=digest
        result["converted_artifact_bytes"]=Path(p.weights).stat().st_size
        orig=Path(p.reference)
        fixture=json.loads(orig.read_text(encoding="utf8"))
        observed=fixture["original_clip_chain"]
        if observed["source_clip_weights_sha256"]!=EXPECTED_CLIP:raise ValueError("CLIP_FIXTURE_HASH_DRIFT")
        if fixture["checkpoint_sha256"]!=EXPECTED_ORIGINAL_CKPT:raise ValueError("SOURCE_MAPPER_HASH_DRIFT")
        result["reference_receipt_sha256"]=sha_file(orig)
        scores=observed["scores_raw_image_text_logits"]
        expected=observed["mapper_output_10_smplx_betas"]
        if len(scores)!=3 or len(expected)!=3 or any(len(v)!=8 for v in scores) or any(len(v)!=10 for v in expected):
            raise ValueError("BAD_TEST_FIXTURE_SHAPE")
        module_path=source/"semantify/train/mapper_module.py"
        tree=ast.parse(module_path.read_text(encoding="utf8"))
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="C2M")
        ns={"nn":nn,"List":List,"Union":Union}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),str(module_path),"exec"),ns)
        model=ns["C2M"](num_stats=8,hidden_size=[800,500],out_features=10,num_hiddens=1)
        sd=load_file(str(p.weights),device="cpu")
        model.load_state_dict(sd,strict=True)
        model.eval()
        x=torch.tensor(scores,dtype=torch.float32)
        target=torch.tensor(expected,dtype=torch.float32)
        start=time.perf_counter()
        with torch.inference_mode():
            got=model(x)
            repeated=model(x)
        elapsed=time.perf_counter()-start
        err=torch.abs(got-target)
        maxerr=float(err.max().item())
        mae=float(err.mean().item())
        replay=float(torch.max(torch.abs(got-repeated)).item())
        result.update({
            "source_native_class":"Semantify::C2M 8→800→500→10",
            "published_clip_inputs":3,
            "eight_descriptor_logit_min":float(x.min().item()),
            "eight_descriptor_logit_max":float(x.max().item()),
            "max_abs_beta_error":round(maxerr,9),
            "mean_abs_beta_error":round(mae,9),
            "max_replay_abs_error":round(replay,9),
            "tolerance":0.0003,
            "warm_two_forward_seconds":round(elapsed,6),
            "all_finite":bool(torch.isfinite(got).all()),
            "output_dimension":list(got.shape)
        })
        result["status"]="PASS_MODERNIZED_NATIVE_PRETRAINED_TENSOR_PARITY" if (
            result["all_finite"] and maxerr<=0.0003 and replay==0 and list(got.shape)==[3,10]
        ) else "FAIL_MODERNIZED_TENSOR_PARITY"
    except Exception as e:
        result["failure_type"]=type(e).__name__
        result["failure_detail"]=str(e)[:800]
    out=Path(p.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf8")
    print(out.read_text())
    if not result["status"].startswith("PASS"):raise SystemExit(1)

if __name__=="__main__":main()
