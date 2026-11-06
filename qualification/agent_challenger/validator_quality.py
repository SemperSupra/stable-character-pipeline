#!/usr/bin/env python3
"""Versioned synthetic validator-quality replay for the independent native challenger.

Reports validator capability, NOT actor competence, external photograph fit,
human anatomy, image perceptual quality, or permission to merge/release.
Expected outcomes are fixed independently of the validator implementation.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import platform
import time

from challenge import CANDIDATES, EvidenceError, challenge

SCHEMA = "scp.validator.performance.v1"
CORPUS = "scp.native_multiview_challenger.hostile.v1"
CLASSES = ("ACCEPT", "ABSTAIN", "REJECT", "ERROR")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def controls(source):
    """Immutable source input; controlled mutations do not represent real photo ground truth."""
    rows = []
    def add(name, expected, mutation=None):
        data = copy.deepcopy(source)
        if mutation is not None:
            mutation(data)
        rows.append((name, expected, data))

    add("source-native-original", "ACCEPT")
    add("wrong-model-sha", "REJECT", lambda x: x.update(model_source_sha256="invalid"))
    add("forged-external-photo", "REJECT", lambda x: x.update(external_photo_fit="PASS"))
    add("forged-reasoning-inference", "REJECT", lambda x: x.update(reasoning_model_inference="PASS"))
    add("missing-view", "REJECT", lambda x: x["per_view_frame"].pop())
    add("foreign-reference", "REJECT", lambda x: x["per_view_frame"][0].update(reference_sha256="e" * 64))
    add("forged-aggregate", "REJECT", lambda x: x["mean_iou_by_candidate"].update(zero=0.0))
    add("forged-baseline", "REJECT", lambda x: x.update(baseline_mean_iou=0.0))
    add("unexpected-nonnumeric-score", "REJECT", lambda x: x["per_view_frame"][0].update(candidate_iou="nan"))
    add("forged-winner", "REJECT", lambda x: x.update(best_candidate=next(k for k in CANDIDATES if k != x["best_candidate"])))

    def no_improvement(x):
        for row in x["per_view_frame"]:
            row["candidate_iou"] = row["baseline_iou"]
        baseline = sum(row["baseline_iou"] for row in x["per_view_frame"] if row["candidate"] == "zero") / 4
        for key in CANDIDATES:
            x["mean_iou_by_candidate"][key] = baseline
        x["best_candidate"] = CANDIDATES[0]
        x["measured_gain"] = 0.0
    add("valid-abstention-no-improvement", "ABSTAIN", no_improvement)
    return rows


def classify(source, validator):
    try:
        result = validator(source)
    except EvidenceError:
        return "REJECT"
    except Exception:
        return "ERROR"
    if not isinstance(result, dict):
        return "ERROR"
    decision = result.get("decision")
    if decision == "RULE_ONLY_SYNTHETIC_IMPROVEMENT_OBSERVED":
        return "ACCEPT"
    if decision == "ABSTAIN_NO_CROSS_VIEW_IMPROVEMENT":
        return "ABSTAIN"
    return "ERROR"


def percentile(values, numerator, denominator):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * numerator / denominator) - 1)] if ordered else 0


def measure(source, validator=challenge):
    cases = controls(source)
    matrix = {label: {actual: 0 for actual in CLASSES} for label in CLASSES}
    observations = []
    times = []
    for name, expected, candidate in cases:
        t0 = time.perf_counter_ns()
        observed = classify(candidate, validator)
        dt = time.perf_counter_ns() - t0
        times.append(dt)
        matrix[expected][observed] += 1
        observations.append({"id": name, "expected": expected, "actual": observed,
                             "input_sha256": sha(candidate), "elapsed_ns": dt})
    wrong = sum(int(x["actual"] != x["expected"]) for x in observations)
    rejected = sum(int(x["expected"] == "REJECT") for x in observations)
    detected = sum(int(x["expected"] == "REJECT" and x["actual"] == "REJECT") for x in observations)
    false_accept = sum(int(x["expected"] != "ACCEPT" and x["actual"] == "ACCEPT") for x in observations)
    false_reject = sum(int(x["expected"] == "ACCEPT" and x["actual"] != "ACCEPT") for x in observations)
    return {
        "schema": SCHEMA,
        "validator": "scp.native_multiview_challenger",
        "validator_sha256": hashlib.sha256(Path(__file__).with_name("challenge.py").read_bytes()).hexdigest(),
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "corpus": CORPUS,
        "corpus_sha256": sha([{"id": n, "expected": e, "input_sha256": sha(c)} for n, e, c in cases]),
        "source_evidence_sha256": sha(source),
        "source_class": "IMMUTABLE_ARCHIVED_NATIVE_SYNTHETIC_WITH_MUTATED_CONTROLS",
        "model_inference": "NOT_RUN",
        "external_photo_validation": "NOT_RUN",
        "anatomical_or_perceptual_validation": "UNKNOWN",
        "runtime": {"python": platform.python_version(), "latency_p50_ns": percentile(times, 1, 2),
                    "latency_p95_ns": percentile(times, 95, 100), "latency_max_ns": max(times)},
        "confusion": matrix, "case_count": len(cases), "rejection_detection": {"detected": detected, "total": rejected},
        "false_acceptance_count": false_accept, "false_rejection_count": false_reject,
        "hard_error_count": sum(int(x["actual"] == "ERROR") for x in observations),
        "contract_mismatch_count": wrong, "cases": observations,
        "verdict": "PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY" if wrong == 0 else "FAIL_VALIDATOR_CONTROLS",
        "model_promotion": False, "merge_release_CPE_approval": False
    }


def compare(old, new):
    """Do not compare performance when source/fixtures differ; time is observational only."""
    keys = ("schema", "validator", "corpus", "corpus_sha256", "source_evidence_sha256")
    if any(old.get(k) != new.get(k) for k in keys):
        return {"comparable": False, "decision": "HOLD_DIFFERENT_CORPUS_OR_SOURCE"}
    regressions = {}
    for field in ("false_acceptance_count", "false_rejection_count", "hard_error_count", "contract_mismatch_count"):
        before, after = old.get(field), new.get(field)
        if type(before) is not int or type(after) is not int:
            return {"comparable": False, "decision": "HOLD_MALFORMED_REFERENCE"}
        if after > before:
            regressions[field] = {"before": before, "after": after}
    return {"comparable": True, "decision": "FAIL_QUALITY_REGRESSION" if regressions else "NO_COUNT_REGRESSION_LATENCY_OBSERVATIONAL",
            "regressions": regressions}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous", help="optional prior quality receipt for comparable regression")
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text())
    report = measure(source)
    if args.previous:
        report["comparison"] = compare(json.loads(Path(args.previous).read_text()), report)
    out = Path(args.output)
    out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    if report["contract_mismatch_count"] or report.get("comparison", {}).get("decision") == "FAIL_QUALITY_REGRESSION":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
