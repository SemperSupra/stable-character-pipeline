#!/usr/bin/env python3
"""Plan source-bound, group-disjoint motion dataset splits without acquiring media.

A candidate catalog entry is NOT permission to ingest or train. Only explicit
admitted source records may enter this split planner.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

SPLITS = ("train", "validation", "test")

def assign(records):
    if not isinstance(records, list) or not records:
        raise ValueError("EMPTY_RECORD_SET")
    seen = set()
    by_group = collections.defaultdict(list)
    required = ("id", "domain", "source_id", "source_group", "lineage_key",
                "skeleton_id", "modality", "license_state", "admission_state")
    for row in records:
        for k in required:
            if not isinstance(row.get(k), str) or not row[k].strip():
                raise ValueError("INVALID_" + k.upper())
        if row["id"] in seen:
            raise ValueError("DUPLICATE_RECORD_ID")
        seen.add(row["id"])
        if row["domain"] not in ("human", "fauna"):
            raise ValueError("INVALID_DOMAIN")
        if row["admission_state"] != "admitted":
            raise ValueError("NOT_ADMITTED")
        # Same underlying take/session and all derived views remain in one split.
        group = row["lineage_key"] + "|" + row["source_group"]
        by_group[group].append(row)
    buckets = {k: [] for k in SPLITS}
    for group, rows in sorted(by_group.items()):
        score = int(hashlib.sha256(("scp-motion-split-v1|"+group).encode()).hexdigest()[:12], 16) % 100
        bucket = "train" if score < 70 else "validation" if score < 85 else "test"
        buckets[bucket] += rows
    result = {s: sorted(x["id"] for x in buckets[s]) for s in SPLITS}
    assert sum(map(len, result.values())) == len(records)
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--records", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    source = a.records.read_bytes()
    records = json.loads(source)
    result = {
        "schema": "scp.motion.split-plan.v1",
        "records_sha256": hashlib.sha256(source).hexdigest(),
        "split_rule": "source_lineage_and_session_group_sha256_v1",
        "data_scope": "admitted_records_only",
        "splits": assign(records),
        "limitations": [
            "hash-based bins need not be balanced for small samples",
            "aliases of an original source must share lineage_key",
            "this split does not establish real-world generalization"
        ]
    }
    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    if a.output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_bytes(encoded)
    print("SPLIT_PLAN_WRITTEN", hashlib.sha256(encoded).hexdigest())

if __name__ == "__main__":
    main()
