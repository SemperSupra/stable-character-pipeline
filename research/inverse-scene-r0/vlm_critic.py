#!/usr/bin/env python3
"""Real tiny public SmolVLM CPU appearance critic on R63 3D inverse-fit renders.

Blind paired images: reference vs candidate. The model sees neither source
procedural armrest presence nor numerical IoU labels. A source-known graph
comparison is a distinct oracle and is NOT automatically visual truth.
"""
from __future__ import annotations
import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont
import torch
from transformers import AutoProcessor,AutoModelForVision2Seq

sys.path.insert(0,str(Path(__file__).resolve().parent))
from bakeoff import CAMERAS,TRUTH,case_run,render,source_image,validate

ROOT=Path(os.environ.get("R64_VLM_OUT","out/r64-vlm-critic")).resolve()
ROOT.mkdir(parents=True,exist_ok=True)
SCHEMA="r64-real-smolvlm-source-known-object-critic/v1"
MODEL="HuggingFaceTB/SmolVLM-256M-Instruct"
MODEL_REV="d039ab0d4b9311b617e8ffec1d06c8464364aeb3"
QUESTION=("Compare the left REFERENCE and right CANDIDATE images of the same "
          "room. Focus only on the BLUE CHAIR's pair of armrests, not the couch "
          "or person. Do they appear structurally the same in both images? "
          "Answer exactly one word: MATCH, DIFFERENT, or UNKNOWN. "
          "Use UNKNOWN if chair armrests cannot be judged from this view.")
CASES=("C_part_program_discrete_then_fit","D_RGBD_geometry_init_then_object_fit")
os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
os.environ["TOKENIZERS_PARALLELISM"]="false"

def hash_bytes(x):return hashlib.sha256(x).hexdigest()

def panel(reference,candidate,name):
    # Neither source program nor expected armrest status is encoded in pixels.
    out=Image.new("RGB",(512,286),(248,248,248))
    d=ImageDraw.Draw(out)
    d.text((5,4),"REFERENCE",fill=(0,0,0))
    d.text((262,4),"CANDIDATE",fill=(0,0,0))
    left=Image.fromarray(source_image(reference)).resize((240,240),Image.Resampling.NEAREST)
    right=Image.fromarray(source_image(candidate)).resize((240,240),Image.Resampling.NEAREST)
    out.paste(left,(7,36))
    out.paste(right,(265,36))
    path=ROOT/(name+".png")
    out.save(path)
    return path

def answer_to_class(s):
    x=s.upper().strip()
    if not x:return "UNPARSEABLE"
    first=x.split()[0].strip(".,:;!?\"'[]()")
    return first if first in ("MATCH","DIFFERENT","UNKNOWN") else "UNPARSEABLE"

def infer(model,processor,img):
    msg=[{"role":"user","content":[{"type":"image"},{"type":"text","text":QUESTION}]}]
    prompt=processor.apply_chat_template(msg,add_generation_prompt=True)
    inputs=processor(text=prompt,images=[Image.open(img).convert("RGB")],return_tensors="pt")
    t0=time.monotonic()
    with torch.inference_mode():
        result=model.generate(**inputs,max_new_tokens=18,do_sample=False)
    output=processor.batch_decode(
        result[:,inputs["input_ids"].shape[1]:],skip_special_tokens=True)[0].strip()
    return output,round(time.monotonic()-t0,3)

def prepared_panels():
    validate()
    items=[]
    for scene_id,truth in enumerate(TRUTH):
        result=case_run(scene_id,truth,ROOT)
        for view in (2,3):
            ref_lab,_=render(truth,CAMERAS[view])
            for kind in CASES:
                cand=result["methods"][kind]
                arms=tuple(cand.get("armrest_program_selected",(2,2)))
                param=np.asarray(cand["parameter_estimate"])
                can_lab,_=render(param,CAMERAS[view],arms)
                name=f"s{scene_id}_v{view}_{kind[0]}"
                img=panel(ref_lab,can_lab,name)
                # Structural answer from source graph, NOT perceptually verified.
                expected="MATCH" if arms==(2,2) else "DIFFERENT"
                items.append({"scene":scene_id,"view":view,"candidate_family":kind,
                  "candidate_arms":arms,"source_arms":(2,2),
                  "structure_label":expected,"comparison_role":"source_graph_truth_not_visible_truth",
                  "panel":str(img),"rgb_pixel_l1":round(float(np.mean(
                    np.abs(source_image(ref_lab).astype(float)-
                           source_image(can_lab).astype(float)))),4)})
        if scene_id==0:
            view=2
            lab,_=render(truth,CAMERAS[view])
            img=panel(lab,lab,"exact_duplicate_reference")
            items.append({"scene":scene_id,"view":view,"candidate_family":"exact_pixel_identity_control",
              "candidate_arms":(2,2),"source_arms":(2,2),"structure_label":"MATCH",
              "comparison_role":"EXACT_PIXEL_IDENTITY","panel":str(img),"rgb_pixel_l1":0.0})
    return items

def run():
    start=time.monotonic()
    record={"schema":SCHEMA,"status":"FAIL","model_id":MODEL,"model_revision":MODEL_REV,
      "source_commit":os.getenv("GITHUB_SHA","LOCAL"),
      "source_rights":"original public synthetic R63 scene, no real person/media",
      "cpu_only":True,"question_sha256":hash_bytes(QUESTION.encode()),
      "question":QUESTION,"observations":[],
      "science_limits":["Real pretrained small VLM, but NO trained 3D reconstruction nor SAM mask inference",
        "Source program structure can disagree while visible pixels are ambiguous",
        "Not a calibrated visual critic or human-body/furniture benchmark",
        "No automatic source graph repairs/critic promotion or end-user VLM safety assurance"]}
    try:
        torch.set_num_threads(2)
        items=prepared_panels()
        processor=AutoProcessor.from_pretrained(MODEL,revision=MODEL_REV,trust_remote_code=False)
        model=AutoModelForVision2Seq.from_pretrained(
            MODEL,revision=MODEL_REV,trust_remote_code=False,torch_dtype=torch.float32,
            use_safetensors=True,low_cpu_mem_usage=True).to("cpu").eval()
        for entry in items:
            img=Path(entry.pop("panel"))
            text,secs=infer(model,processor,img)
            line={**entry,"image_sha256":hash_bytes(img.read_bytes()),
              "model_raw":text[:240],"classification":answer_to_class(text),
              "inference_seconds":secs,
              "structure_agreement_indicator":answer_to_class(text)==entry["structure_label"],
              "critical_limit":"Source semantic armrest count is not necessarily observable in image"}
            record["observations"].append(line)
            print("VLM_SCENE_CRITIC="+json.dumps({k:line[k] for k in
                ("scene","view","candidate_family","structure_label","classification",
                 "rgb_pixel_l1","inference_seconds")},sort_keys=True),flush=True)
        if len(record["observations"])!=9:raise AssertionError("missing blind candidate views")
        record["summary"]={"n":len(record["observations"]),
          "parseable":sum(x["classification"]!="UNPARSEABLE" for x in record["observations"]),
          "unknown":sum(x["classification"]=="UNKNOWN" for x in record["observations"]),
          "source_program_agreement_nonvisual":sum(
              x["structure_agreement_indicator"] for x in record["observations"]),
          "scientific_nonclaim":"These are *not* calibrated accuracy metrics due unobservable geometry and tiny synthetic sample"}
        record["status"]="PASS"
    except BaseException as e:
        record["error"]={"type":type(e).__name__,"message":str(e)}
        raise
    finally:
        record["wall_seconds"]=round(time.monotonic()-start,3)
        record["peak_rss_kb"]=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        p=ROOT/"receipt.json"
        p.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
        print("R64_VLM_FINAL="+json.dumps({"status":record["status"],
          "n":len(record["observations"]),"wall_seconds":record["wall_seconds"],
          "peak_rss_kb":record["peak_rss_kb"],"receipt_sha256":hash_bytes(p.read_bytes()),
          "summary":record.get("summary")},sort_keys=True),flush=True)
if __name__=="__main__":
    run()
