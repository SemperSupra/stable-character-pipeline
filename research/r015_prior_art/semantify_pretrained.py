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


def original_clip_numeric_fixture(mapper, labels, scratch):
    """Execute original Semantify CLIP scoring function (AST-isolated, pinned sources).
    All images are locally generated stylized nonsexual adult silhouette controls.
    No SMPL-X geometry or photorealism is asserted.
    """
    import torch
    from PIL import Image,ImageDraw
    from tqdm import tqdm
    clip_source=Path(os.environ.get("R015_CLIP_SOURCE",""))
    clip_sha="d05afc436d78f1c48dc0dbf8e5980a9d471f35f6"
    got=subprocess.check_output(["git","-C",str(clip_source),"rev-parse","HEAD"],text=True).strip()
    if got!=clip_sha:raise RuntimeError("FAIL_CLOSED_OPENAI_CLIP_SHA")
    import sys
    sys.path.insert(0,str(clip_source))
    import clip
    import hashlib
    import time
    torch.set_num_threads(2)
    root=Path(scratch)/"r015-silhouettes"
    root.mkdir(parents=True,exist_ok=True)
    shapes=[
        {"id":0,"kind":"tall-narrow-analytic","top":9,"bottom":220,"shoulder":26,"waist":13,"hip":19,"head_r":10},
        {"id":1,"kind":"short-broad-analytic","top":38,"bottom":197,"shoulder":45,"waist":31,"hip":37,"head_r":14},
        {"id":2,"kind":"medium-analytic-control","top":23,"bottom":208,"shoulder":35,"waist":23,"hip":28,"head_r":12}
    ]
    if os.environ.get("R015_CLIP_ROBUSTNESS")=="1":
        for source_cfg in list(shapes):
            variant=dict(source_cfg)
            variant["id"]=source_cfg["id"]+3
            variant["kind"]=source_cfg["kind"]+"-warm-background-control"
            variant["background"]=(207,226,238)
            shapes.append(variant)
    hashes={}
    for cfg in shapes:
        canvas=Image.new("RGB",(224,224),cfg.get("background",(244,244,244)))
        draw=ImageDraw.Draw(canvas)
        cx=112
        top=cfg["top"];bottom=cfg["bottom"];sr=cfg["shoulder"];wa=cfg["waist"];hip=cfg["hip"];head=cfg["head_r"]
        head_y=top+head
        draw.ellipse((cx-head,top,cx+head,top+2*head),fill=(32,42,50))
        necktop=top+head*2+2
        shoulder_y=necktop+10
        waist_y=shoulder_y+(bottom-shoulder_y)*0.34
        hip_y=waist_y+(bottom-shoulder_y)*0.19
        # Neutral, fully clothed abstract adult figure. No sexual detail/age-coded features.
        draw.polygon([(cx-sr,shoulder_y),(cx+sr,shoulder_y),(cx+wa,waist_y),(cx+hip,hip_y),(cx-hip,hip_y),(cx-wa,waist_y)],fill=(32,42,50))
        arm_bottom=hip_y+8
        draw.line([(cx-sr+2,shoulder_y+5),(cx-sr-7,arm_bottom)],fill=(32,42,50),width=11)
        draw.line([(cx+sr-2,shoulder_y+5),(cx+sr+7,arm_bottom)],fill=(32,42,50),width=11)
        draw.polygon([(cx-hip+3,hip_y),(cx-3,hip_y),(cx-8,bottom),(cx-hip+2,bottom)],fill=(32,42,50))
        draw.polygon([(cx+3,hip_y),(cx+hip-3,hip_y),(cx+hip-2,bottom),(cx+8,bottom)],fill=(32,42,50))
        outfile=root/(str(cfg["id"])+"_front.png")
        canvas.save(outfile)
        hashes[cfg["kind"]]=digest(outfile)
    source=Path(os.environ["R015_SEMANTIFY_SOURCE"])/"semantify/data_management/creation/clip_encoder.py"
    tree=ast.parse(source.read_text(encoding="utf8"))
    native=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="generate_clip_scores")
    # Original function compiled unchanged, but neither the heavyweight Semantify
    # general imports nor any renderer/model-asset code is imported.
    scope={"clip":clip,"torch":torch,"Image":Image,"tqdm":tqdm,"Path":Path,"json":json,"List":List}
    exec(compile(ast.Module(body=[native],type_ignores=[]),str(source),"exec"),scope)
    # Author's function downloads signed official ViT-B/32 weights verified via SHA.
    st=time.monotonic()
    scope["generate_clip_scores"](device="cpu",multiview=False,imgs_dir=str(root),descriptors=[str(v[0]) for v in labels])
    elapsed=round(time.monotonic()-st,3)
    from clip.clip import _MODELS
    expected=_MODELS["ViT-B/32"].split("/")[-2]
    cache=Path.home()/".cache/clip/ViT-B-32.pt"
    if not cache.is_file() or digest(cache)!=expected:
        raise RuntimeError("FAIL_CLOSED_CLIP_WEIGHTS_DIGEST")
    scores=[]
    for cfg in shapes:
        datum=json.loads((root/(str(cfg["id"])+"_labels.json")).read_text())
        vals=[]
        for lab in labels:
            key=str(lab[0])
            raw=datum[key]
            vals.append(float(raw[0][0]))
        scores.append(vals)
    x=torch.tensor(scores,dtype=torch.float32)
    with torch.no_grad():
        mapped=mapper(x)
        repeated=mapper(x)
    if not torch.isfinite(x).all() or not torch.isfinite(mapped).all():
        raise RuntimeError("NONFINITE_CLIP_OR_MAPPER")
    beta=mapped.tolist()
    norms=[round(float(torch.linalg.vector_norm(mapped[i]).item()),5) for i in range(len(shapes))]
    result={
        "status":"PASS_ORIGINAL_CLIP_TO_ORIGINAL_MAPPER_NUMERIC_CHAIN_ONLY",
        "source_clip_commit":clip_sha,
        "source_clip_weights_sha256":digest(cache),
        "source_semantify_score_function_sha256":digest(source),
        "descriptor_order":[str(v[0]) for v in labels],
        "synthetic_silhouette_hashes":hashes,
        "scores_raw_image_text_logits":[[round(v,5) for v in row] for row in scores],
        "mapper_output_10_smplx_betas":[[round(v,6) for v in row] for row in beta],
        "mapped_vector_l2_norms":norms,
        "repeat_max_abs_delta":round(float((mapped-repeated).abs().max().item()),8),
        "score_min":round(float(x.min().item()),5),
        "score_max":round(float(x.max().item()),5),
        "original_clip_score_and_mapper_wall_seconds":elapsed,
        "cpu_concurrent_model_calls":"Sequential per image and descriptor, matching upstream scoring",
        "disclaimer":"Inputs are public vector-drawn stylized adult silhouettes, NOT native 3DMM renders, CLIP scores are not calibrated to original SMPL-X training image distribution. No real body geometry or photoreal output evaluated.",
        "model_assets_redistributed":False,
        "generated_images_redistributed":False,
    }
    if os.environ.get("R015_CLIP_BATCH")=="1":
        # Exact official CLIP implementation in both paths. First match the
        # upstream per-label source inference, then call CLIP's native BxN batch.
        # No model retraining or custom approximation; benchmark the scorer only.
        import statistics,resource
        model_clip,preprocess=clip.load("ViT-B/32",device="cpu",jit=False)
        model_clip.eval()
        images=torch.stack([preprocess(Image.open(root/(str(cfg["id"])+"_front.png"))) for cfg in shapes])
        tokens=clip.tokenize([str(v[0]) for v in labels])
        serial_times=[]
        serial_logits=None
        with torch.inference_mode():
            for _ in range(2):
                start=time.monotonic()
                serial_logits=torch.stack([
                    torch.stack([model_clip(im.unsqueeze(0),tok.unsqueeze(0))[0].flatten()[0] for tok in tokens])
                    for im in images
                ])
                serial_times.append(time.monotonic()-start)
        batch_times=[]
        batch_logits=None
        with torch.inference_mode():
            for _ in range(5):
                start=time.monotonic()
                batch_logits=model_clip(images,tokens)[0]
                batch_times.append(time.monotonic()-start)
        diff=float(torch.max(torch.abs(serial_logits-batch_logits)).item())
        native_diff=float(torch.max(torch.abs(x-batch_logits)).item())
        if not torch.isfinite(batch_logits).all():
            result["status"]="FAIL_NONFINITE_BATCHED_CLIP"
        if diff>0.05 or native_diff>0.05:
            result["status"]="FAIL_BATCH_SCORE_INEQUIVALENCE"
        result["batch_inference_operating_probe"]={
            "status":"PASS_NUMERIC_EQUIVALENCE" if result["status"].startswith("PASS_") else "FAIL_BATCH_SCORE_INEQUIVALENCE",
            "images":len(shapes),"descriptors":len(labels),
            "original_native_sequential_round_seconds":[round(v,6) for v in serial_times],
            "original_native_batched_round_seconds":[round(v,6) for v in batch_times],
            "sequential_warm_median_seconds":round(statistics.median(serial_times),6),
            "batched_warm_median_seconds":round(statistics.median(batch_times),6),
            "warm_batch_to_serial_speedup_ratio":round(statistics.median(serial_times)/statistics.median(batch_times),4) if statistics.median(batch_times)>0 else None,
            "batch_vs_native_serial_max_abs_logit_delta":round(diff,8),
            "batch_vs_author_source_max_abs_logit_delta":round(native_diff,8),
            "peak_maxrss_kib_linux":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "source":"official OpenAI CLIP pin; same image preprocessing and same descriptor order",
            "scope":"Only CLIP image/text forward latency after load; NOT checkpoint download/startup, Semantify mapper runtime, renderer or service p95",
            "model_asset_rights_included":False,
        }
    if len(shapes)==6:
        def distance(a,b):
            return float(torch.linalg.vector_norm(mapped[a]-mapped[b]).item())
        def score_distance(a,b):
            return float(torch.linalg.vector_norm(x[a]-x[b]).item())
        geometry_control=distance(0,1)
        same_geometry_background=[distance(i,i+3) for i in range(3)]
        sem_control=score_distance(0,1)
        sem_background=[score_distance(i,i+3) for i in range(3)]
        result["background_robustness_probe"]={
            "status":"MEASURED_NO_QUALITY_ASSERTION",
            "baseline_geometry_controls":"Three original stylized silhouettes; variants are byte-identical geometry but changed background",
            "background_rgb_baseline":[244,244,244],
            "background_rgb_variant":[207,226,238],
            "mapped_beta_l2_between_tall_and_broad":round(geometry_control,6),
            "mapped_beta_l2_for_same_shape_background_changed":[round(v,6) for v in same_geometry_background],
            "mean_background_to_shape_beta_l2_ratio":round(sum(same_geometry_background)/len(same_geometry_background)/geometry_control,6) if geometry_control>0 else None,
            "raw_clip_score_l2_between_tall_and_broad":round(sem_control,6),
            "raw_clip_score_l2_for_background_changed":[round(v,6) for v in sem_background],
            "mean_background_to_shape_clip_l2_ratio":round(sum(sem_background)/len(sem_background)/sem_control,6) if sem_control>0 else None,
            "not_geometry_qualified":True
        }
    return result

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
        # Immutable original public snapshot: only this audited archive+checkpoint may
        # receive narrowly scoped compatibility allowlisting. Fail on any upstream drift.
        if record["archive_sha256"]!="91682ac20d450f02c02f97e99ab5858fc12e0f15dbcedbd1e8d2bb4c244a72c2" or record["checkpoint_sha256"]!="7bb79747504919656ecacb120b5be70b51b6faac1535d1cfd7f46b1401a3ed7b":
            record["status"]="REJECT_ARCHIVE_OR_CHECKPOINT_DRIFT"
            return record
        # Static pickle opcode enumeration does not execute any deserializer.
        import pickletools
        with zipfile.ZipFile(io.BytesIO(bytes_ckpt)) as kzip:
            kname=next(n for n in kzip.namelist() if n.endswith("/data.pkl") or n=="data.pkl")
            pbytes=kzip.read(kname)
        ops=list(pickletools.genops(pbytes))
        actual_globals=sorted({str(arg) for op,arg,pos in ops if op.name=="GLOBAL"})
        stack_global=sum(1 for op,arg,pos in ops if op.name=="STACK_GLOBAL")
        record["pickle_GLOBAL_symbols"]=actual_globals
        record["pickle_STACK_GLOBAL_count"]=stack_global
        record["pickle_opcode_count"]=len(ops)
        allowed_globals=sorted([
            "__builtin__ dict","__builtin__ list","__builtin__ long",
            "collections OrderedDict","collections defaultdict",
            "omegaconf.base ContainerMetadata","omegaconf.base Metadata",
            "omegaconf.dictconfig DictConfig","omegaconf.listconfig ListConfig",
            "omegaconf.nodes AnyNode","torch FloatStorage",
            "torch._utils _rebuild_tensor_v2","typing Any"
        ])
        if actual_globals!=allowed_globals or stack_global:
            record["status"]="REJECT_UNREVIEWED_PICKLE_GLOBALS"
            return record
        try:
            obj=torch.load(io.BytesIO(bytes_ckpt),map_location="cpu",weights_only=True)
            record["safe_load_mode"]="torch.weights_only_no_custom_globals"
        except Exception as e:
            record["default_weights_only_error"]=type(e).__name__+": "+str(e)[-900:]
            # Pinned OmegaConf 2.3.0 structural containers only, from the audited
            # pickle global manifest above; *never* weights_only=False.
            try:
                from collections import defaultdict
                from omegaconf.base import ContainerMetadata,Metadata
                from omegaconf.dictconfig import DictConfig
                from omegaconf.listconfig import ListConfig
                from omegaconf.nodes import AnyNode
                from typing import Any
                safe=[defaultdict,ContainerMetadata,Metadata,DictConfig,ListConfig,AnyNode,Any,list,dict,int]
                with torch.serialization.safe_globals(safe):
                    obj=torch.load(io.BytesIO(bytes_ckpt),map_location="cpu",weights_only=True)
                record["safe_load_mode"]="weights_only_explicit_audited_omegaconf_2_3_0_globals"
            except Exception as restricted:
                record["status"]="BLOCKED_RESTRICTED_WEIGHTS_ONLY_DESERIALIZATION"
                record["restricted_error"]=type(restricted).__name__+": "+str(restricted)[-1100:]
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
        if os.environ.get("R015_SAFE_TENSOR_EXPORT"):
            # Exact-hash gated author checkpoint has already passed the restricted
            # weights-only loader. Export only tensor values, no metadata classes
            # or pickle executables. Keep this file inside the disposable runner.
            from safetensors.torch import save_file
            export=Path(os.environ["R015_SAFE_TENSOR_EXPORT"])
            export.parent.mkdir(parents=True,exist_ok=True)
            clean={k:v.detach().cpu().contiguous() for k,v in model.state_dict().items()}
            save_file(clean,str(export))
            record["safe_tensor_export"]={
                "sha256":digest(export),
                "bytes":export.stat().st_size,
                "tensor_keys":sorted(clean.keys()),
                "format":"safetensors; detached contiguous CPU tensors only",
                "asset_redistributed":False,
                "original_checkpoint_sha256":record["checkpoint_sha256"],
                "conversion_torch_version":torch.__version__
            }
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
        if os.environ.get("R015_SCORE_REPLAY_RECEIPT"):
            fixture_path=Path(os.environ["R015_SCORE_REPLAY_RECEIPT"])
            fixture=json.loads(fixture_path.read_text(encoding="utf8"))
            prior=fixture["original_clip_chain"]
            assert prior["source_clip_weights_sha256"]=="40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af"
            expected=prior["mapper_output_10_smplx_betas"]
            scores=prior["scores_raw_image_text_logits"]
            if len(scores)!=3 or len(expected)!=3 or any(len(x)!=8 for x in scores) or any(len(v)!=10 for v in expected):
                record["status"]="REJECT_SCORE_FIXTURE_SHAPE"
                return record
            with torch.inference_mode():
                got=model(torch.tensor(scores,dtype=torch.float32))
                target=torch.tensor(expected,dtype=torch.float32)
                abs_error=torch.abs(got-target)
            maxerr=float(abs_error.max().item())
            mae=float(abs_error.mean().item())
            # Reference was rounded to six decimal places. Allow documented
            # roundoff and CPU threading differences, but not numerical drift.
            tol=0.0003
            status="PASS_MODERN_FRAMEWORK_SCORE_REPLAY" if maxerr<=tol and torch.isfinite(got).all() else "FAIL_MODERN_FRAMEWORK_SCORE_REPLAY"
            record["modern_score_replay"]={
                "status":status,
                "reference_receipt_sha256":digest(fixture_path),
                "reference_github_run":43278119546,
                "reference_clip_weights_sha256":prior["source_clip_weights_sha256"],
                "input_source":"published CLIP ViT-B/32 raw scores on 3 synthetic age-neutral adult silhouettes from prior original source run",
                "test_vectors":3,"inputs_each":8,"output_betas_each":10,
                "max_abs_beta_error":round(maxerr,9),
                "mean_abs_beta_error":round(mae,9),
                "max_abs_error_allowed":tol,
                "checkpoint_sha256":record["checkpoint_sha256"],
                "torch_version":torch.__version__,
                "native_mesh_qualified":False,
                "native_LLM_qualified":False,
                "no_new_image_encoding":True,
            }
            if not status.startswith("PASS"):
                record["status"]=status
        if os.environ.get("R015_CLIP_SOURCE"):
            realclip=original_clip_numeric_fixture(model, metadata["labels"], os.environ.get("RUNNER_TEMP","/tmp"))
            record["original_clip_chain"]=realclip
            if realclip["status"].startswith("PASS_"):
                record["status"]="PASS_ORIGINAL_CLIP_TO_ORIGINAL_MAPPER_NUMERIC_CHAIN_ONLY"

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
