#!/usr/bin/env python3
"""Fail-closed source+decoded-video evidence join for original 22-case candidate.

Only an L1/L2 *targeted* multi-witness gate; this can never issue full human
motion, physical realism, identity, rig, texture or production acceptance.
Original negative controls are never changed or silently relabelled.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

SHA256 = re.compile(r"^[a-f0-9]{64}$")
SOURCE_SCHEMA = "scp.motion-math-corpus-audit.v1"
VIDEO_SCHEMA = "scp.video-bakeoff-receipt.v1"
OUTPUT_SCHEMA = "scp.visualqa.dual-evidence-gate.v1"
STATES = {"PASS", "FAIL", "UNKNOWN"}
EXPECTED_SOURCE = {"PASS":18, "FAIL":3, "UNKNOWN":1}
EXPECTED_VIDEO = {"PASS":14, "FAIL":6, "UNKNOWN":2}
CASE_COUNT = 22

def targeted_gate(source: str, video: str) -> str:
    """Neither a targeted PASS nor a codec PASS authorizes realism acceptance."""
    if source not in STATES or video not in STATES:
        raise ValueError("UNRECOGNIZED_EVIDENCE_VERDICT")
    if "FAIL" in (source, video):
        return "BLOCK_CORRECTIVE_RESEARCH"
    if "UNKNOWN" in (source, video):
        return "ABSTAIN_HUMAN_OR_INDEPENDENT_REVIEW"
    return "TARGETED_SOURCE_AND_VIDEO_PASS_ONLY"

def _json(path: Path):
    raw = path.read_bytes()
    if not raw or len(raw) > 5_000_000:
        raise ValueError("EVIDENCE_SIZE_UNTRUSTWORTHY")
    return json.loads(raw)

def _sha(value):
    return isinstance(value, str) and bool(SHA256.fullmatch(value))

def _count(rows, field):
    return {v: sum(x[field] == v for x in rows) for v in ("PASS","FAIL","UNKNOWN")}

def combine(source_doc: dict, video_doc: dict) -> dict:
    if (source_doc.get("schema") != SOURCE_SCHEMA
        or source_doc.get("case_count") != CASE_COUNT
        or video_doc.get("schema") != VIDEO_SCHEMA
        or video_doc.get("total") != CASE_COUNT
        or video_doc.get("matched") != 0
        or video_doc.get("discrepancies") != 0):
        raise ValueError("SOURCE_OR_VIDEO_RECEIPT_CONTRACT_MISMATCH")
    sr, vr = source_doc.get("cases"), video_doc.get("results")
    if not isinstance(sr,list) or not isinstance(vr,list) or len(sr)!=CASE_COUNT or len(vr)!=CASE_COUNT:
        raise ValueError("CASE_COUNT_OR_CASE_LIST_INVALID")
    if _count(sr,"status") != EXPECTED_SOURCE or _count(vr,"verdict") != EXPECTED_VIDEO:
        raise ValueError("EIGHT_FIX_QUALIFIED_COUNTS_CHANGED")
    left, right = {}, {}
    for s in sr:
        cid = s.get("case")
        if (not isinstance(cid,str) or not re.fullmatch(r"[a-z0-9_]+", cid)
            or cid in left or s.get("status") not in STATES
            or not _sha(s.get("source_sha256"))):
            raise ValueError("UNTRUSTWORTHY_SOURCE_CASE_OR_SHA")
        if s.get("frames_checked") != 40:
            raise ValueError("SOURCE_FRAMES_INCOMPLETE")
        left[cid] = s
    for v in vr:
        rid = v.get("id")
        if (not isinstance(rid,str) or not rid.endswith("_video")
            or rid in right or v.get("kind") != "video"
            or v.get("verdict") not in STATES or not _sha(v.get("source_sha256"))
            or v.get("expected","") != "" or v.get("matches_oracle") is not False
            or v.get("error")):
            raise ValueError("UNTRUSTWORTHY_VIDEO_CASE_OR_ORACLE")
        right[rid] = v
    if set(right) != {name+"_video" for name in left}:
        raise ValueError("SOURCE_VIDEO_IDENTITY_SET_MISMATCH")
    rows = []
    for case, s in sorted(left.items()):
        v = right[case+"_video"]
        rows.append({
            "case": case,
            "source_status": s["status"], "video_status": v["verdict"],
            "source_labels_sha256": s["source_sha256"],
            "decoded_h264_sha256": v["source_sha256"],
            "targeted_gate": targeted_gate(s["status"],v["verdict"]),
            "source_defect_count": s["defect_count"],
            "video_findings": v.get("findings",[]),
            "human_motion_realism_accepted": False,
        })
    gates = {k:sum(x["targeted_gate"]==k for x in rows)
             for k in ("BLOCK_CORRECTIVE_RESEARCH",
                       "ABSTAIN_HUMAN_OR_INDEPENDENT_REVIEW",
                       "TARGETED_SOURCE_AND_VIDEO_PASS_ONLY")}
    if sum(gates.values()) != CASE_COUNT:
        raise AssertionError("MISSING_ADJUDICATION")
    return {
        "schema": OUTPUT_SCHEMA,
        "original_negative_controls": "IMMUTABLE",
        "case_count": CASE_COUNT,
        "source_counts": EXPECTED_SOURCE,
        "decoded_video_counts": EXPECTED_VIDEO,
        "gate_counts": gates,
        "cases": rows,
        "global_realism_verdict": "NOT_QUALIFIED",
        "global_deployment_verdict": "HOLD",
        "limits": [
            "Source pass covers selected geometric/contact checks, not full 3D anatomy",
            "Decoded H264 pass covers a narrow FFmpeg black/freeze diagnostic, not visual realism",
            "No independently learned joint/pixel pose acceptance, soft-tissue dynamics, stable identity, or ground reaction forces",
            "Original corpus and original negative controls remain untouched",
            "This adjudicator consumes source and video receipts from one qualified prior cloud artifact; independent witnesses still needed for production",
        ],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--video", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    result=combine(_json(Path(a.source)),_json(Path(a.video)))
    dest=Path(a.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("DUAL_ORACLE_TARGETED_ONLY",result["case_count"],result["gate_counts"])

if __name__ == "__main__":
    main()
