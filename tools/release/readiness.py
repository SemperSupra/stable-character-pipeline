#!/usr/bin/env python3
"""Read-only, offline R16 technical evidence intake. Never grants a release."""
import argparse
import json
import re
import sys
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
REQUIRED = {"native_two_camera", "source_recovery", "human_browser"}
class InvalidEvidence(ValueError): pass
def require(ok, code):
 if not ok: raise InvalidEvidence(code)
def object_pairs_unique(pairs):
 out={}
 for k,v in pairs:
  require(k not in out,"DUPLICATE_JSON_FIELD")
  out[k]=v
 return out
def load(path):
 data=Path(path).read_bytes()
 require(len(data)<=1048576,"MANIFEST_TOO_LARGE")
 return json.loads(data,object_pairs_hook=object_pairs_unique)

def audit(receipt):
 require(type(receipt) is dict and set(receipt)=={"schema","source_commit","workflows","scope","rights","scientific","release"}, "RECEIPT_KEYS")
 require(receipt["schema"]=="scp.synthetic-release-intake.v1", "RECEIPT_VERSION")
 sha=receipt["source_commit"]
 require(type(sha) is str and SHA.fullmatch(sha), "SOURCE_SHA_NOT_PINNED")
 require(receipt["scope"]=="public-original-synthetic" and receipt["rights"]=="ORIGINAL_SELF_AUTHORED_SYNTHETIC","PROTECTED_SOURCE_NOT_ADMITTED")
 require(receipt["scientific"]=={"human_behavior":"FAIL_ABSTRACT_LIMBS_ONLY",
 "human_anatomy":"UNKNOWN_NO_INDEPENDENT_JCS_OR_ROM"}, "SCIENTIFIC_NONPROMOTION_REQUIRED")
 require(receipt["release"]=="HELD_R009_NOT_RUN_NOT_ADMITTED", "RELEASE_PROMOTION_FORBIDDEN")
 runs=receipt["workflows"]
 require(type(runs) is list and len(runs)==3,"EXACT_THREE_INDEPENDENT_EVIDENCE_PATHS")
 seen=set()
 for run in runs:
  require(type(run) is dict and set(run)=={"kind","source_commit","status","conclusion","run_id","artifact_digest"},"WORKFLOW_SCHEMA")
  kind=run["kind"];require(type(kind) is str and kind in REQUIRED and kind not in seen,"DUPLICATE_OR_UNKNOWN_WORKFLOW")
  seen.add(kind)
  require(run["source_commit"]==sha,"CROSS_SOURCE_CI_MISMATCH")
  require(run["status"]=="completed" and run["conclusion"]=="success","CI_NOT_SUCCESSFUL")
  require(type(run["run_id"]) is int and run["run_id"]>0,"UNBOUND_RUN_ID")
  digest=run["artifact_digest"]
  require(digest is None or (type(digest) is str and DIGEST.fullmatch(digest)),"MALFORMED_ARTIFACT_DIGEST")
 require(seen==REQUIRED,"MISSING_EVIDENCE_PATH")
 # Workflows are self-declared input. Without authenticated GitHub API evidence,
 # actual artifact custody, signed issuer and owner approval, never promote.
 return {"schema":"scp.synthetic-release-readiness.v1","source_commit":sha,
  "technical_ci_claim":"THREE_COMPLETED_SUCCESS_ASSERTED_UNTRUSTED_INPUT",
  "authenticated_ci_proof":"NOT_PERFORMED",
  "original_artifact_byte_custody":"NOT_VERIFIED",
  "private_character_product":"HELD_NOT_ACCEPTED",
  "decision":"HOLD_RELEASE_AND_CPE_PROMOTION"}
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("receipt",type=Path)
 args=p.parse_args(argv)
 try: result=audit(load(args.receipt))
 except (InvalidEvidence,ValueError,OSError,TypeError) as e:
  print("SOURCE_SAFE_INTAKE_FAIL_CLOSED:"+str(e),file=sys.stderr);return 2
 print(json.dumps(result,sort_keys=True,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
