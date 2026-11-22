#!/usr/bin/env python3
"""Nonproduction contract fixture conformance; no network/audio or user records."""
from __future__ import annotations
import json
import pathlib
import sys
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "audio-control" / "contract" / "audio_control.r0.schema.json"
VECTORS = ROOT / "audio-control" / "contract" / "vectors-r0.json"

def main() -> int:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    cases = json.loads(VECTORS.read_text(encoding="utf-8"))
    seen: set[str] = set()
    accepted = rejected = host_only = 0
    for case in cases:
        name = case["name"]
        assert name not in seen and name, "duplicate/blank vector id"
        seen.add(name)
        value = case["value"]
        valid = validator.is_valid(value)
        if valid != case["valid"]:
            errors = [str(x.message) for x in validator.iter_errors(value)]
            raise AssertionError(f"{name}: expected valid={case['valid']}, observed={valid}: {errors}")
        if case["valid"]:
            accepted += 1
            if case["channel"] == "host_only":
                host_only += 1
                assert value["action"].startswith("host_"), name
            if case["channel"] == "user":
                assert not value["action"].startswith("host_"), name
        else:
            rejected += 1
    assert accepted >= 5 and rejected >= 5 and host_only >= 2
    print(f"PASS schema 2020-12, vectors={len(cases)}, admitted={accepted}, rejected={rejected}, privileged-host-vectors={host_only}")
    print("NOTE: a valid host-only JSON envelope is NOT authenticated; real ingress separation is a host responsibility.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
