#!/usr/bin/env python3
"""Separate stdlib-only oracle for source-generated USD stage semantics."""
import hashlib
import json
from pathlib import Path
import sys
r=Path(sys.argv[1])
create=json.loads((r/"create.json").read_text())
verify=json.loads((r/"verify.json").read_text())
usda=(r/"scene.usda").read_bytes()
expected_points=[[-1.0,0.0,0.0],[1.0,0.0,0.0],[1.0,2.0,0.0],[-1.0,2.0,0.0]]
hashv=hashlib.sha256(usda).hexdigest()
errors=[]
for phase,rec in (("create",create),("verify",verify)):
    if rec["phase"]!=phase or rec["status"]!="PASS":errors.append(phase+"_status")
    if rec["stage_sha256"]!=hashv:errors.append(phase+"_hash")
    if rec["points"]!=expected_points or rec["counts"]!=[3,3] or rec["indices"]!=[0,1,2,0,2,3]:
        errors.append(phase+"_topology")
    if rec["semantic"]!="original-procedural-test" or rec["custom"]!="r8-openusd":
        errors.append(phase+"_semantic")
    if rec["up_axis"]!="Z" or rec["meters_per_unit"]!=1.0:
        errors.append(phase+"_units_up")
if not usda.startswith(b"#usda"):errors.append("missing_usda_magic")
if b"pipeline:semantic" not in usda or b"Mesh" not in usda:
    errors.append("missing_typed_payload")
receipt={"schema":"openusd-independent-oracle/v1","status":"PASS" if not errors else "FAIL",
         "stage_sha256":hashv,"points":4,"triangles":2,
         "metadata_retained":not any("semantic" in e for e in errors),
         "errors":errors}
(r/"independent-oracle.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,sort_keys=True))
if errors:raise SystemExit(1)
