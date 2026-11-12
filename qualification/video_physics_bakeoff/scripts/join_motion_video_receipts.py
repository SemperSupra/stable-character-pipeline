#!/usr/bin/env python3
"""Independent dual-modality research witness. Never a production realism grader.

Consumes two source-exact, originally independent artifact JSON receipts.
Does not reclassify any FAIL or UNKNOWN as science/character acceptance.
Python stdlib only; no videos, identities, model weights, external services.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{64}$")
STATES = {"PASS", "FAIL", "UNKNOWN"}

def read_bounded(path):
    raw = Path(path).read_bytes()
    if len(raw) > 2_000_000:
        raise ValueError("RECEIPT_OVERSIZE")
    return json.loads(raw), hashlib.sha256(raw).hexdigest()

def triage(source, video, source_digest, video_digest):
    if source.get("schema") != "scp.motion-math-corpus-audit.v1" or video.get("schema") != "scp.video-bakeoff-receipt.v1":
        raise ValueError("SCHEMA_MISMATCH")
    cases = source.get("cases")
    observations = video.get("results")
    if not isinstance(cases, list) or not isinstance(observations, list) or not cases or not observations:
        raise ValueError("EMPTY_OR_MISSING_INPUTS")
    if source.get("case_count") != len(cases) or video.get("total") != len(observations):
        raise ValueError("COUNT_MISMATCH")
    if video.get("matched") != 0 or video.get("discrepancies") != 0:
        raise ValueError("NOT_AN_UNLABELLED_DIAGNOSTIC")
    src, vid = {}, {}
    for case in cases:
        name = case.get("case")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9_]+", name) or name in src:
            raise ValueError("DUPLICATE_OR_INVALID_SOURCE_CASE")
        if case.get("status") not in STATES or not SHA.fullmatch(case.get("source_sha256", "")):
            raise ValueError("INVALID_SOURCE_EVIDENCE")
        if not isinstance(case.get("findings"), list):
            raise ValueError("MISSING_SOURCE_FINDINGS")
        src[name] = case
    for observation in observations:
        key = observation.get("id")
        if not isinstance(key, str) or not key.endswith("_video"):
            raise ValueError("VIDEO_ID_MISMATCH")
        name = key[:-6]
        if name in vid or observation.get("verdict") not in STATES or not SHA.fullmatch(observation.get("source_sha256", "")):
            raise ValueError("INVALID_VIDEO_EVIDENCE")
        if observation.get("expected") != "" or observation.get("matches_oracle") is not False or observation.get("error"):
            raise ValueError("VIDEO_GOLD_LABEL_OR_ERROR")
        if not isinstance(observation.get("findings"), list):
            raise ValueError("MISSING_VIDEO_FINDINGS")
        vid[name] = observation
    if set(src) != set(vid):
        raise ValueError("CASE_CUSTODY_MISMATCH")
    if Counter(c["status"] for c in cases) != Counter(source.get("counts", {})):
        raise ValueError("SOURCE_COUNTS_DISAGREE")
    rows, matrix, dispositions = [], Counter(), Counter()
    for name in sorted(src):
        a, b = src[name], vid[name]
        s, v = a["status"], b["verdict"]
        matrix[(s, v)] += 1
        if s == "FAIL" or v == "FAIL":
            hold = "REJECT_TARGETED_CONTROLS"
        elif s == "UNKNOWN" or v == "UNKNOWN":
            hold = "INSUFFICIENT_TARGETED_EVIDENCE"
        else:
            hold = "TARGETED_CONTROLS_ONLY"
        dispositions[hold] += 1
        rows.append({
            "case": name,
            "source_status": s, "video_status": v, "disposition": hold,
            "modality_conflict": (s, v) in {("FAIL", "PASS"), ("PASS", "FAIL")},
            "source_label_sha256": a["source_sha256"],
            "decoded_video_sha256": b["source_sha256"],
            "source_findings": a["findings"],
            "video_findings": b["findings"],
            "video_metrics": b.get("metrics", {}),
            "labeled_stance_intervals": a.get("labeled_contiguous_stance_intervals"),
        })
    return {
        "schema": "scp.video-geometry-dual-modality-triage.v1",
        "scientific_status": "RDT_AND_E_DIAGNOSTIC_NOT_REALISM_ACCEPTANCE",
        "source_receipt_sha256": source_digest,
        "video_receipt_sha256": video_digest,
        "case_count": len(rows),
        "matrix": [{"source": a, "video": b, "cases": n} for (a,b),n in sorted(matrix.items())],
        "dispositions": dict(sorted(dispositions.items())),
        "cases": rows,
        "limits": [
            "Neither source label nor basic black/freeze FFmpeg check is an independent human realism model",
            "PASS+PASS means targeted checks only; no biomechanical or identity qualification",
            "Source-label/decoded-video SHA values intentionally refer to different file types",
            "Pretrained model pose tracking and synchronized 3D-to-pixel correspondence remain distinct gates",
        ],
    }

def markdown(report):
    lines = [
        "# Independent geometry vs decoded-video triage",
        "",
        "Scope: rights-original synthetic Stable Character test corpus; **not an overall realism or product acceptance**.",
        "",
        "Source math receipt SHA256: `" + report["source_receipt_sha256"] + "`.",
        "",
        "Decoded-video receipt SHA256: `" + report["video_receipt_sha256"] + "`.",
        "",
        "## Contingency counts",
        "",
        "| Source geometry/contact | Actual decoded video | Cases |",
        "|---|---|---:|",
    ]
    for entry in report["matrix"]:
        lines.append("| " + entry["source"] + " | " + entry["video"] + " | " + str(entry["cases"]) + " |")
    lines += [
        "", "## Case-level observations",
        "",
        "| Case | Source | Video | Targeted disposition | Source defects | Video findings |",
        "|---|---|---|---|---:|---|",
    ]
    for row in report["cases"]:
        findings = ", ".join(row["video_findings"]) or "none"
        lines.append("| " + row["case"] + " | " + row["source_status"] + " | " + row["video_status"] +
                     " | " + row["disposition"] + " | " + str(len(row["source_findings"])) + " | " + findings + " |")
    lines += ["", "## Limitations", ""]
    lines += ["- " + s for s in report["limits"]]
    return "\n".join(lines) + "\n"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--video", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--markdown", required=True)
    args = p.parse_args()
    s, sh = read_bounded(args.source)
    v, vh = read_bounded(args.video)
    result = triage(s, v, sh, vh)
    Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    Path(args.markdown).write_text(markdown(result))
    print("DUAL_MODALITY_CASES", result["case_count"], "MATRIX", result["matrix"], "DISPOSITIONS", result["dispositions"])

if __name__ == "__main__":
    main()
