#!/usr/bin/env python3
"""Candidate-only plan bridge: exact original synthetic source bytes + Go policy."""
import hashlib
import json
import math
import sys
from pathlib import Path

FIELDS = {"schema", "experiment_id", "joint", "axis", "baseline_sha256",
          "reference_sha256", "candidate_plans", "disposition", "limits", "execution"}
DELTAS = (-0.6, 0.0, 0.6)
EXPERIMENT = "synthetic_pony_neck_multiview"

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def proposal(model, evidence):
    a, b = sha256(model), sha256(evidence)
    if a == b:
        raise ValueError("model and evidence are identical")
    return {
        "schema":"scp.actor_parameter_plan.v1",
        "experiment_id":EXPERIMENT,
        "subject_class":"public_original_synthetic_equine",
        "baseline_sha256":a,
        "reference_sha256":b,
        "joint":"neck",
        "axis":"Z",
        "min_radians":-0.6,
        "max_radians":0.6,
        "candidates":3,
        "evidence_class":"public_original_synthetic_self_reference",
        "intent":"candidate_only"
    }

def unique_pairs(pairs):
    value = {}
    for k, v in pairs:
        if k in value:
            raise ValueError("duplicate JSON key: "+k)
        value[k] = v
    return value

def load_plan(path):
    raw = Path(path).read_bytes()
    if not raw or len(raw) > (1 << 20):
        raise ValueError("plan must be 1..1048576 bytes")
    return json.loads(raw, object_pairs_hook=unique_pairs)

def validate(model, evidence, plan):
    p = proposal(model, evidence)
    if not isinstance(plan, dict) or set(plan) != FIELDS:
        raise ValueError("unknown or missing plan fields")
    for k, v in {
        "schema":"scp.actor_candidate_plan.v1",
        "experiment_id":EXPERIMENT,
        "joint":"neck","axis":"Z",
        "baseline_sha256":p["baseline_sha256"],
        "reference_sha256":p["reference_sha256"],
        "disposition":"VALID_PLAN_ONLY",
        "execution":False,
    }.items():
        if plan[k] != v or (k == "execution" and type(plan[k]) is not bool):
            raise ValueError("mismatch: "+k)
    if not isinstance(plan["limits"], str) or len(plan["limits"]) > 256:
        raise ValueError("invalid limits declaration")
    values = plan["candidate_plans"]
    if not isinstance(values, list) or len(values) != 3:
        raise ValueError("invalid candidate count")
    ids = []
    for i, (v, angle) in enumerate(zip(values, DELTAS)):
        if not isinstance(v, dict) or set(v) != {"index","angle_radians","candidate_id"}:
            raise ValueError("candidate field mismatch")
        actual = v["angle_radians"]
        if type(actual) not in (float,int) or not math.isfinite(actual) or abs(actual-angle) > 1e-12 or type(v["index"]) is not int or v["index"] != i:
            raise ValueError("unapproved angle/index")
        wire = f'{EXPERIMENT}|{p["baseline_sha256"]}|{p["reference_sha256"]}|neck|Z|{i}|{float(actual):.17g}'
        ident = hashlib.sha256(wire.encode("utf8")).hexdigest()
        if v["candidate_id"] != ident:
            raise ValueError("candidate ID does not bind exact proposal")
        ids.append(ident)
    receipt = {"schema":"scp.native_actor_bridge.v1",
        "source_sha256":p["baseline_sha256"],
        "evidence_sha256":p["reference_sha256"],
        "candidate_ids":ids,
        "candidate_deltas_radians":[v["angle_radians"] for v in values],
        "plan_sha256":hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "evidence_kind":"SYNTHETIC_SOURCE_GLB_NOT_EXTERNAL_PHOTOGRAPH",
        "disposition":"VALIDATED_PLAN_ONLY",
        "model_promotion":False
    }
    return receipt

if __name__=="__main__":
    try:
        if len(sys.argv)==4 and sys.argv[1]=="make":
            v=proposal(sys.argv[2],sys.argv[3])
        elif len(sys.argv)==5 and sys.argv[1]=="check":
            v=validate(sys.argv[2],sys.argv[3],load_plan(sys.argv[4]))
        else:
            raise ValueError("usage: plan_bridge.py make model.blend evidence.glb | check model.blend evidence.glb plan.json")
        print(json.dumps(v,sort_keys=True))
    except (OSError,ValueError,TypeError,KeyError) as e:
        print("REJECT_ACTOR_PLAN: "+str(e),file=sys.stderr)
        sys.exit(2)
