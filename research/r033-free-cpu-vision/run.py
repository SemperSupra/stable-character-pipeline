#!/usr/bin/env python3
"""Public original synthetic-only CPU VLM smoke, never a source/quality approval."""
from __future__ import annotations
import hashlib, json, os, re, sys, time
from pathlib import Path

MODEL="HuggingFaceTB/SmolVLM-256M-Instruct"
REV="d039ab0d4b9311b617e8ffec1d06c8464364aeb3"
ROOT=Path(os.environ.get("RUNNER_TEMP","/tmp")) / "sc-r033-smolvlm"
ROOT.mkdir(parents=True,exist_ok=True)
os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
os.environ["TOKENIZERS_PARALLELISM"]="false"

from PIL import Image,ImageDraw
import torch
from transformers import AutoProcessor,AutoModelForVision2Seq

def sha(b: bytes) -> str:
 return hashlib.sha256(b).hexdigest()

def original_public_image(count:int) -> Path:
 """Create first-party synthetic images; no private repo assets or human photos."""
 im=Image.new("RGB",(320,320),(242,242,242))
 d=ImageDraw.Draw(im)
 for k in range(count):
  x=40+85*k
  d.ellipse((x,112,x+50,162),fill=(228,24,24))
 d.rectangle((18,238,302,249),fill=(60,80,160))
 p=ROOT/f"original-synthetic-{count}-red-circles.png"
 im.save(p)
 return p

def main():
 torch.set_num_threads(2)
 t0=time.monotonic()
 processor=AutoProcessor.from_pretrained(MODEL, revision=REV, trust_remote_code=False)
 model=AutoModelForVision2Seq.from_pretrained(
  MODEL,revision=REV,torch_dtype=torch.float32,
  trust_remote_code=False,low_cpu_mem_usage=True,use_safetensors=True
 ).to("cpu").eval()
 loaded=time.monotonic()-t0
 results=[]
 for n in (2,3):
  p=original_public_image(n)
  from PIL import Image
  with Image.open(p) as im: img=im.convert("RGB")
  msg=[{"role":"user","content":[{"type":"image"},{"type":"text","text":"Count the solid red circles in this picture. Reply with one digit, or UNKNOWN if uncertain."}]}]
  prompt=processor.apply_chat_template(msg, add_generation_prompt=True)
  values=processor(text=prompt,images=[img],return_tensors="pt")
  t=time.monotonic()
  with torch.inference_mode():
   ids=model.generate(**values,max_new_tokens=18,do_sample=False)
  answer=processor.batch_decode(ids[:,values["input_ids"].shape[1]:],skip_special_tokens=True)[0].strip()
  duration=round(time.monotonic()-t,3)
  match=re.search(r"\b[0-9]+\b",answer)
  observed=int(match.group()) if match else None
  results.append({"fixture":"original_synthetic_count_"+str(n),
                  "image_sha256":sha(p.read_bytes()),
                  "expected_count":n,"model_answer":answer[:160],
                  "parsed_count":observed,"exact_match":observed==n,
                  "inference_seconds":duration,"status":"OBSERVATION_NOT_QUALIFIED"})
 report={
  "schema":"scp.r033.free-cpu-vlm-r0",
  "status":"RESEARCH_ONLY_NOT_APPROVED",
  "source_class":"public_synthetic_original",
  "model":MODEL,
  "pinned_revision":REV,
  "license_claim":"apache-2.0 (model card, not independently adjudicated)",
  "device":"cpu",
  "framework":"transformers",
  "model_loading_seconds":round(loaded,3),
  "tests":results,
  "limitations":["Not an independent anatomical/3D critic","No human/preference labels","No private media or identity","No calibrated confidence","No source-to-image provenance beyond original generated PNGs","No rights/canonical/release promotion"]
 }
 (ROOT/"public-result.json").write_text(json.dumps(report,indent=2)+"\n")
 print("SCP_R033_SMALL_VLM_CPU_RECEIPT",json.dumps(report,sort_keys=True))
 return 0
if __name__=="__main__":
 raise SystemExit(main())
