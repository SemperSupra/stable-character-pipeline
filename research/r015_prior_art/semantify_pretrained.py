#!/usr/bin/env python3
"""Semantify upstream distributed mapper archival + safe pretrained forward.
No unverified model pickle execution, no asset redistribution, no licensed 3DMM.
"""
import ast
from hashlib import sha256
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
from typing import List,Union
import zipfile

SOURCE="https://drive.google.com/uc?export=download&id=1KZRSvSny-BD7fbXvogkSwN8tEvnzlYOa"
ARCHIVE_MAX=200_000_000
UNCOMPRESSED_MAX=400_000_000
MEMBER_MAX=60_000_000

def digest(b):
    if isinstance(b,Path):
        h=sha256()
        with b.open("rb") as f:
            for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
        return h.hexdigest()
    return sha256(b).hexdigest()

def run(repo_path, path):
    record={
        "schema":"r015.semantify.pretrained.v1",
        "research_only":True,
        "source":"Omergral/Semantify@78b001d3dc4ea4efa428e3aff1213cefddf6ebd8",
        "model_archive_source":"upstream project's public Google Drive ID, TLS verified",
        "model_archive_redistributed":False,
        "model_asset_licensing_confirmed":False,
        "licensed_smplx_3dmm_instantiated":False,
        "native_geometry_measured":False,
        "merger_release_approval":False,
    }
    try:
        outdir=Path(os.environ.get("RUNNER_TEMP","/tmp"))/"r015-pretrained"
        outdir.mkdir(exist_ok=True)
        archive=outdir/"mappers.zip"
        # Trusted system curl. Never use the upstream --no-check-certificate script.
        cmd=["curl","--silent","--show-error","--fail","--location","--proto","=https",
             "--proto-redir","=https","--max-redirs","6","--max-time","100",
             "--max-filesize",str(ARCHIVE_MAX),"--output",str(archive),SOURCE]
        st=time.monotonic()
        cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        record["download_seconds"]=round(time.monotonic()-st,3)
        record["curl_exit_code"]=cp.returncode
        if cp.returncode:
            record["status"]="BLOCKED_DOWNLOAD"
            record["download_error"]=cp.stderr[-500:]
            return record
        size=archive.stat().st_size
        record["archive_size_bytes"]=size
        if size>ARCHIVE_MAX:
            record["status"]="REJECT_OVERSIZE"
            return record
        record["archive_sha256"]=digest(archive)
        if not zipfile.is_zipfile(archive):
            with archive.open("rb") as f:record["first_12_bytes_hex"]=f.read(12).hex()
            record["status"]="BLOCKED_NONZIP_PAYLOAD"
            return record
        with zipfile.ZipFile(archive) as z:
            info=z.infolist()
            record["archive_member_count"]=len(info)
            record["archive_files"]=[p.filename for p in info if p.filename.endswith((".ckpt",".json"))][:40]
            if len(info)>600 or sum(p.file_size for p in info)>UNCOMPRESSED_MAX or any(
                p.file_size>MEMBER_MAX or p.filename.startswith("/") or
                ".." in Path(p.filename).parts or (p.external_attr >> 16)&0o170000==0o120000 for p in info
            ):
                record["status"]="REJECT_UNSAFE_ZIP_MANIFEST"
                return record
            ckpts=[p for p in info if p.filename.lower().endswith("/smplx_neutral.ckpt") or p.filename.lower()=="smplx_neutral.ckpt"]
            metadatas=[p for p in info if p.filename.lower().endswith("/smplx_neutral_metadata.json") or p.filename.lower()=="smplx_neutral_metadata.json"]
            if not ckpts:
                record["status"]="BLOCKED_NO_SMPLX_NEUTRAL_MAPPER"
                return record
            cp_info=ckpts[0]
            record["checkpoint_compressed_bytes"]=cp_info.compress_size
            record["checkpoint_uncompressed_bytes"]=cp_info.file_size
            with z.open(cp_info) as c:
                bytes_ckpt=c.read(MEMBER_MAX+1)
            if len(bytes_ckpt)>MEMBER_MAX:
                record["status"]="REJECT_UNCOMPRESSED_CHECKPOINT_LIMIT"
                return record
            record["checkpoint_sha256"]=digest(bytes_ckpt)
            metadata={}
            if metadatas:
                with z.open(metadatas[0]) as f:
                    b=f.read(1_000_001)
                if len(b)<=1_000_000:
                    metadata=json.loads(b)
            record["metadata_top_level_keys"]=list(metadata) if isinstance(metadata,dict) else ["not_dict"]
            record["metadata_labels"]=(metadata.get("labels") or metadata.get("labels_to_get") or [])[:20] if isinstance(metadata,dict) else []
        # Treat checkpoint as untrusted input. Never use pickle weights_only=False.
        import torch
        import torch.nn as nn
        record["torch_version"]=torch.__version__
        try:
            obj=torch.load(io.BytesIO(bytes_ckpt),map_location="cpu",weights_only=True)
        except Exception as e:
            record["status"]="BLOCKED_SAFE_DESERIALIZATION"
            record["safe_load_error"]=type(e).__name__+": "+str(e)[-1700:]
            # Static Python pickle opcode inspection does not unpickle or execute.
            # Record the exact globals that block PyTorch's restricted weights loader.
            try:
                import pickletools
                with zipfile.ZipFile(io.BytesIO(bytes_ckpt)) as kzip:
                    kname=next(n for n in kzip.namelist() if n.endswith("/data.pkl") or n=="data.pkl")
                    pbytes=kzip.read(kname)
                ops=list(pickletools.genops(pbytes))
                record["pickle_GLOBAL_symbols"]=sorted({str(arg) for op,arg,pos in ops if op.name=="GLOBAL"})[:100]
                record["pickle_STACK_GLOBAL_count"]=sum(1 for op,arg,pos in ops if op.name=="STACK_GLOBAL")
                record["pickle_opcode_count"]=len(ops)
            except Exception as pe:
                record["static_pickle_diagnostics_error"]=type(pe).__name__+": "+str(pe)[:250]
            return record
        state=obj.get("state_dict",obj) if isinstance(obj,dict) else {}
        if not isinstance(state,dict) or len(state)>200:
            record["status"]="REJECT_INVALID_STATE_DICT"
            return record
        shapes={k:list(v.shape) for k,v in state.items() if hasattr(v,"shape")}
        record["checkpoint_tensor_count"]=len(shapes)
        record["checkpoint_shape_summary"]={k:shapes[k] for k in sorted(shapes)[:12]}
        layers=[]
        for key,v in state.items():
            match=re.search(r"(?:^|[.])fc_layers[.](\d+)[.]weight$",key)
            if match and getattr(v,"ndim",0)==2:
                layers.append((int(match.group(1)),key,v))
        layers.sort()
        out_layer=[(k,v) for k,v in state.items() if k.endswith("out_layer.weight") and getattr(v,"ndim",0)==2]
        if not layers or len(out_layer)!=1:
            record["status"]="BLOCKED_UNKNOWN_NATIVE_CHECKPOINT_LAYOUT"
            return record
        input_size=int(layers[0][2].shape[1])
        hidden_sizes=[int(v.shape[0]) for _,_,v in layers]
        output_size=int(out_layer[0][1].shape[0])
        record["network_input_size"]=input_size
        record["hidden_sizes"]=hidden_sizes
        record["network_output_size"]=output_size
        native=(repo_path/"semantify/train/mapper_module.py")
        tree=ast.parse(native.read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=="C2M")
        ns={"nn":nn,"List":List,"Union":Union}
        exec(compile(ast.Module(body=[cls],type_ignores=[]),str(native),"exec"),ns)
        model=ns["C2M"](num_stats=input_size,hidden_size=hidden_sizes,out_features=output_size,
                        num_hiddens=len(hidden_sizes)-1)
        model_sd={k.removeprefix("model."):v for k,v in state.items() if k.startswith("model.")}
        model.load_state_dict(model_sd,strict=True)
        model.eval()
        if input_size>256 or output_size>256:
            record["status"]="REJECT_IMPLAUSIBLE_DIMENSIONS"
            return record
        # These are numerical probes, not CLIP-calibrated ratings or age-coded generator presets.
        x=torch.full((1,input_size),0.25,dtype=torch.float32)
        start=time.monotonic()
        with torch.no_grad():
            base=model(x)
            repeat=model(x)
            altered=x.clone();altered[0,0]+=0.05
            changed=model(altered)
        record["forward_seconds"]=round(time.monotonic()-start,6)
        finite=bool(torch.isfinite(base).all() and torch.isfinite(changed).all())
        repeat_diff=float((repeat-base).abs().max().item())
        sensitivity=float(torch.linalg.vector_norm(changed-base).item())
        record["nominal_output_vector"]=[round(float(v),6) for v in base[0].tolist()]
        record["repeat_max_abs_delta"]=round(repeat_diff,8)
        record["first_descriptor_0p05_sensitivity_l2"]=round(sensitivity,8)
        record["all_output_finite"]=finite
        record["score_calibration"]="NOT_VALIDATED; 0.25 is synthetic numeric probe, not measured CLIP score"
        record["status"]="PASS_ACTUAL_PUBLISHED_MAPPER_NUMERIC_FORWARD_ONLY" if finite and repeat_diff==0 and output_size==10 else "FAIL_NATIVE_PRETRAINED_FORWARD"
    except Exception as e:
        traceback.print_exc()
        record["status"]="FAILED_EXCEPTION"
        record["error_type"]=type(e).__name__
        record["error_message"]=str(e)[:450]
    return record

if __name__=="__main__":
    repo=Path(sys.argv[1])
    sha=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
    if sha!="78b001d3dc4ea4efa428e3aff1213cefddf6ebd8":
        raise SystemExit("FAIL_CLOSED: upstream SHA mismatch")
    output=Path(sys.argv[2])
    output.parent.mkdir(parents=True,exist_ok=True)
    receipt=run(repo,output)
    output.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+"\n")
    print(output.read_text())
    if receipt["status"].startswith(("FAILED","REJECT","FAIL_")):
        raise SystemExit(1)
