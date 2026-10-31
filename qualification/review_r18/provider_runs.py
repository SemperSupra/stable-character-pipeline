#!/usr/bin/env python3
"""Public GitHub provider run observation. Never a signed release attestation.

The source commit is an immutable observed prior R15 reference, not current
reviewer head. Original synthetic-only; no GitHub tokens or private APIs.
"""
import json
import sys
import urllib.request

SOURCE="0e07d607b9c0003dbea54e872f82be98bb3fcb84"
REPO="SemperSupra/stable-character-pipeline"
REQUIRED={
 41237673021:".github/workflows/r9-native-job.yml",
 41237672990:".github/workflows/r10-persistent-job.yml",
 41237673011:".github/workflows/r15-headless-browser.yml"}
class ProviderMismatch(ValueError):pass
def insist(value,code):
 if not value:raise ProviderMismatch(code)
def validate(records):
 insist(type(records) is dict and set(records)==set(REQUIRED),"RUN_SET_DRIFT")
 for rid,path in REQUIRED.items():
  entry=records[rid]
  insist(type(entry) is dict,"RUN_NOT_OBJECT")
  insist(type(entry.get("id")) is int and entry["id"]==rid,"RUN_ID_MISMATCH")
  insist(entry.get("head_sha")==SOURCE,"HEAD_SHA_MISMATCH")
  insist(entry.get("path")==path,"WORKFLOW_PATH_MISMATCH")
  insist(entry.get("event")=="pull_request","RUN_TRIGGER_MISMATCH")
  insist(entry.get("status")=="completed" and entry.get("conclusion")=="success","RUN_NOT_GREEN")
  insist(entry.get("repository",{}).get("full_name")==REPO,"REPOSITORY_MISMATCH")
  insist(entry.get("head_repository",{}).get("full_name")==REPO,"HEAD_REPOSITORY_MISMATCH")
  insist(type(entry.get("run_attempt")) is int and entry["run_attempt"]>=1,"RUN_ATTEMPT_INVALID")
 return {"schema":"scp.public-ci-provider-observation.v1","source_sha":SOURCE,
  "repository":REPO,"observed_run_ids":sorted(REQUIRED),
  "scope":"PUBLIC_ORIGINAL_SYNTHETIC_ONLY",
  "source_bound_provider_runs":"THREE_TERMINAL_SUCCESS",
  "artifact_byte_integrity":"NOT_VERIFIED_BY_RUN_METADATA",
  "issuer_signature":"NOT_VERIFIED",
  "private_original_r009":"HELD_NOT_RUN",
  "decision":"HOLD_RELEASE_AND_CPE_PROMOTION"}
def fetch(rid):
 url="https://api.github.com/repos/"+REPO+"/actions/runs/"+str(rid)
 request=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json",
  "User-Agent":"scp-r18-source-safe-provider-review"})
 with urllib.request.urlopen(request,timeout=15) as response:
  insist(response.status==200,"PROVIDER_HTTP_FAIL")
  raw=response.read(1048577)
  insist(len(raw)<=1048576,"PROVIDER_RESPONSE_TOO_LARGE")
  return json.loads(raw)
def main():
 try:report=validate({i:fetch(i) for i in REQUIRED})
 except (ProviderMismatch,ValueError,OSError,urllib.error.URLError) as exc:
  print("PROVIDER_OBSERVATION_FAIL_CLOSED:"+str(exc),file=sys.stderr)
  return 2
 print(json.dumps(report,sort_keys=True,indent=2))
 return 0
if __name__=="__main__":raise SystemExit(main())
