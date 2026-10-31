#!/usr/bin/env python3
"""R19 original .blend semantic witness comparator and hostile controls."""
import json
import sys
from pathlib import Path

EXPECTED={"schema","original_blend_sha256","scene_semantic_sha256","scene_semantic_bytes","objects","frames","scope","biomechanics","human_behavior","product"}
def audit(a,b):
 for item in (a,b):
  if not isinstance(item,dict) or set(item)!=EXPECTED:raise ValueError("WITNESS_SCHEMA_MISMATCH")
  if item["scope"]!="PUBLIC_ORIGINAL_SYNTHETIC_ONLY" or item["product"]!="HELD_R009_NOT_RUN_NOT_ADMITTED":
   raise ValueError("UNAUTHORIZED_PRODUCT_SOURCE_PROMOTION")
  if item["human_behavior"]!="FAIL_ABSTRACT_LIMBS_ONLY" or item["biomechanics"]!="UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM":
   raise ValueError("SCIENTIFIC_PROMOTION_FORBIDDEN")
  if item["frames"]!=24 or item["objects"]<=0:raise ValueError("INCOMPLETE_SOURCE_SCENE_WITNESS")
  for key in ("original_blend_sha256","scene_semantic_sha256"):
   if not isinstance(item[key],str) or len(item[key])!=64 or any(c not in "0123456789abcdef" for c in item[key]):
    raise ValueError("MALFORMED_SCENE_DIGEST")
 if a["original_blend_sha256"]==b["original_blend_sha256"]:
  raise ValueError("EXPECTED_ORIGINAL_BINARY_NONDETERMINISM_NOT_OBSERVED")
 return {"schema":"scp.r19.original_binary_vs_semantic_parity.v1",
 "binary_equal":False,"scene_semantic_equal":a["scene_semantic_sha256"]==b["scene_semantic_sha256"],
 "decision":"SEMANTIC_EQUIVALENT_BUT_NOT_BYTE_DETERMINISTIC" if a["scene_semantic_sha256"]==b["scene_semantic_sha256"] else "FAIL_SCENE_SEMANTIC_DIVERGENCE",
 "original_behavior":"FAIL_ABSTRACT_LIMBS_ONLY","private_r009":"HELD_NOT_RUN"}
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("expected two witness JSON paths")
 print(json.dumps(audit(json.loads(Path(sys.argv[1]).read_text()),json.loads(Path(sys.argv[2]).read_text())),sort_keys=True,indent=2))
