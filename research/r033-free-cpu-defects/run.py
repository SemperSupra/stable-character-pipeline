#!/usr/bin/env python3
"""Blinded source-known 2D humanoid defect / unknown controls, not anatomical QA."""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
from PIL import Image,ImageDraw
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq

MODEL="HuggingFaceTB/SmolVLM-256M-Instruct"
REV="d039ab0d4b9311b617e8ffec1d06c8464364aeb3"
ROOT=Path(os.environ.get("RUNNER_TEMP","/tmp"))/"r033-smolvlm-defects"
ROOT.mkdir(parents=True,exist_ok=True)
os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
os.environ["TOKENIZERS_PARALLELISM"]="false"

# A separately declared finite fixture specification is the SOURCE-KNOWN truth,
# not a claim derived from VLM output or from the reviewer prompt.
CASES=(
 {"id":"full_two_arms","present_right":True,"occlude_right":False,"answer":"YES"},
 {"id":"missing_right_arm","present_right":False,"occlude_right":False,"answer":"NO"},
 {"id":"occluded_right_shoulder","present_right":True,"occlude_right":True,"answer":"UNKNOWN"},
)
QUESTION=("Inspect the drawing. Are exactly two arms clearly visible and attached "
          "to the human-shaped figure's upper torso? Answer exactly YES, NO, or UNKNOWN. "
          "If a shoulder or arm is hidden by an opaque covering, answer UNKNOWN.")

def image(spec):
 im=Image.new("RGB",(512,512),(252,252,252))
 d=ImageDraw.Draw(im)
 dark=(20,34,66);thick=14
 d.ellipse((219,50,293,125),fill=(218,190,154),outline=dark,width=6)
 d.line((256,125,256,330),fill=dark,width=thick)
 d.line((256,195,128,300),fill=dark,width=thick)
 if spec["present_right"]:
  d.line((256,195,384,300),fill=dark,width=thick)
 d.line((256,330,173,465),fill=dark,width=thick)
 d.line((256,330,339,465),fill=dark,width=thick)
 if spec["occlude_right"]:
  d.rectangle((237,180,403,319),fill=(115,115,115))
 return im

def sha(b):return hashlib.sha256(b).hexdigest()

def main():
 torch.set_num_threads(2)
 proc=AutoProcessor.from_pretrained(MODEL,revision=REV,trust_remote_code=False)
 model=AutoModelForVision2Seq.from_pretrained(
  MODEL,revision=REV,trust_remote_code=False,torch_dtype=torch.float32,
  use_safetensors=True,low_cpu_mem_usage=True,
 ).to("cpu").eval()
 rows=[]
 for case in CASES:
  p=ROOT/(case["id"]+".png");image(case).save(p)
  msg=[{"role":"user","content":[{"type":"image"},{"type":"text","text":QUESTION}]}]
  prompt=proc.apply_chat_template(msg,add_generation_prompt=True)
  inputs=proc(text=prompt,images=[Image.open(p).convert("RGB")],return_tensors="pt")
  start=time.monotonic()
  with torch.inference_mode():
   gen=model.generate(**inputs,max_new_tokens=14,do_sample=False)
  answer=proc.batch_decode(gen[:,inputs["input_ids"].shape[1]:],skip_special_tokens=True)[0].strip()
  norm=answer.upper().strip().split()[0].strip(".,!?") if answer else ""
  classified=norm if norm in ("YES","NO","UNKNOWN") else "UNPARSEABLE"
  rows.append({
   "fixture":case["id"],"expected":case["answer"],"model_answer":answer[:160],
   "classified":classified,"correct_on_source_known_fixture":classified==case["answer"],
   "image_sha256":sha(p.read_bytes()),
   "inference_seconds":round(time.monotonic()-start,3),
   "model_status":"UNVERIFIED_VISUAL_OBSERVATION",
  })
 result={
  "schema":"scp.r033.free-cpu-defect-r0",
  "source_class":"public_synthetic_original",
  "status":"RESEARCH_ONLY_NO_CRITIC_APPROVAL",
  "model":MODEL,"model_revision":REV,
  "rubric":"two-visible-arms / occlusion abstention",
  "question_sha256":sha(QUESTION.encode()),
  "fixtures":rows,
  "n_correct":sum(x["correct_on_source_known_fixture"] for x in rows),
  "n_total":len(rows),
  "limitations":["Source-known 2D drawing is not real 3D geometry","Three examples are not independent validation or calibrated accuracy","No learned critic promotion","No human consent data","No private assets, photos or real identities"],
 }
 (ROOT/"receipt.json").write_text(json.dumps(result,indent=2)+"\n")
 print("SCP_R033_DEFECT_CPU_RECEIPT",json.dumps(result,sort_keys=True))
 return 0
if __name__=="__main__":
 raise SystemExit(main())
