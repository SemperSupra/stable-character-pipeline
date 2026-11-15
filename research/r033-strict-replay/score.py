#!/usr/bin/env python3
"""R033 strict critic replay scorer, pure stdlib, public-original metadata only.

This is a SCOREBOARD of independently authored synthetic-fixture labels
against previously observed VLM text. It neither runs a vision model nor
proves images/model weights/labels are independently attested.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
# Preregistered strict response interface: optional trailing punctuation,
# but no aliases (Y), explanatory prose, multiple answers, or markup.
ANSWER = re.compile(r"[ \t]*(YES|NO|UNKNOWN)[.]?[ \t]*\Z", re.IGNORECASE)
LABELS = frozenset(("YES", "NO", "UNKNOWN"))
SCHEMA = "scp.r033.free-cpu-defect-r0"

def pairs_no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("DUPLICATE_JSON_KEY:" + str(k))
        out[k] = v
    return out

def load(source):
    content = Path(source).read_bytes()
    if not 0 < len(content) <= 1 << 20:
        raise ValueError("EVIDENCE_SIZE_BUDGET")
    return json.loads(content, object_pairs_hook=pairs_no_duplicates)

def score(data):
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or data.get("source_class") != "public_synthetic_original":
        raise ValueError("UNSUPPORTED_EVIDENCE_CLASS")
    if data.get("status") != "RESEARCH_ONLY_NO_CRITIC_APPROVAL":
        raise ValueError("CANONICAL_OR_APPROVAL_CLAIM_FORBIDDEN")
    if not isinstance(data.get("model"), str) or not data["model"].strip() or len(data["model"]) > 160:
        raise ValueError("UNBOUND_MODEL_NAME")
    if not isinstance(data.get("model_revision"), str) or not GIT_SHA.fullmatch(data["model_revision"]):
        raise ValueError("UNBOUND_MODEL_REVISION")
    if not isinstance(data.get("question_sha256"), str) or not SHA256.fullmatch(data["question_sha256"]):
        raise ValueError("UNBOUND_PROMPT")
    fixtures = data.get("fixtures")
    if not isinstance(fixtures, list) or not (1 <= len(fixtures) <= 128):
        raise ValueError("INVALID_FIXTURE_COUNT")
    seen = set()
    rows = []
    for i, item in enumerate(fixtures):
        if not isinstance(item, dict):
            raise ValueError("INVALID_FIXTURE_RECORD")
        fixture = item.get("fixture")
        if not isinstance(fixture, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,128}", fixture) or fixture in seen:
            raise ValueError("INVALID_OR_DUPLICATE_FIXTURE_ID")
        seen.add(fixture)
        expected = item.get("expected")
        if expected not in LABELS:
            raise ValueError("INVALID_SOURCE_KNOWN_LABEL")
        if not isinstance(item.get("image_sha256"), str) or not SHA256.fullmatch(item["image_sha256"]):
            raise ValueError("UNBOUND_IMAGE")
        raw = item.get("model_answer")
        if not isinstance(raw, str) or len(raw) > 160:
            raise ValueError("INVALID_MODEL_RESPONSE")
        response = ANSWER.fullmatch(raw)
        parsed = response.group(1).upper() if response else "UNPARSEABLE"
        # Do not consult self-reported 'correct_on_source_known_fixture'.
        exact = parsed == expected
        rows.append({
            "fixture": fixture, "expected": expected,
            "strict_parsed_answer": parsed,
            "format_valid": parsed != "UNPARSEABLE",
            "exact_match": exact,
            "critical_false_approval": parsed == "YES" and expected in ("NO", "UNKNOWN"),
            "occlusion_guess_not_abstained": expected == "UNKNOWN" and parsed in ("YES", "NO"),
            "image_sha256": item["image_sha256"],
        })
    summary = {
        "schema": "scp.r033.strict-replay-score.v1",
        "status": "RESEARCH_REPLAY_NOT_CRITIC_QUALIFICATION",
        "source_receipt_schema": SCHEMA,
        "model": data["model"],
        "model_revision": data["model_revision"],
        "question_sha256": data["question_sha256"],
        "source_media_hash_attestation": "DECLARED_IN_ORIGINAL_RUN_NOT_REHASHED_BY_REPLAY",
        "independent_geometry_truth": "NOT_TESTED",
        "full_body_multiview_anatomy_motion": "NOT_TESTED",
        "human_preference_or_consent": "NOT_TESTED",
        "count": len(rows),
        "strict_correct": sum(z["exact_match"] for z in rows),
        "format_failures": sum(not z["format_valid"] for z in rows),
        "critical_false_approvals": sum(z["critical_false_approval"] for z in rows),
        "occlusion_guesses_without_abstention": sum(z["occlusion_guess_not_abstained"] for z in rows),
        "rows": rows,
    }
    return summary

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = score(load(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("SCP_R033_STRICT_REPLAY_SCORE", json.dumps({
        "count": result["count"], "strict_correct": result["strict_correct"],
        "format_failures": result["format_failures"],
        "critical_false_approvals": result["critical_false_approvals"],
        "occlusion_guesses_without_abstention": result["occlusion_guesses_without_abstention"],
        "status": result["status"],
    }, sort_keys=True))
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print("SCP_R033_SCORE_REJECTED", str(exc), file=sys.stderr)
        sys.exit(3)
