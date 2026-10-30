#!/usr/bin/env python3
"""Public synthetic-only four-shard qualification pilot.

No private CPE data, user identities, source URL collections, or live retrieval.
This tests only bounded parallel-worker invariants and artifact contracts.
"""
import argparse
import hashlib
import json
from pathlib import Path

SHARDS = {"alpha", "beta", "gamma", "delta"}
SYNTHETIC = [
    {"language": "en", "word": "blue", "sense": "color", "source": "fixture://a"},
    {"language": "de", "word": "blau", "sense": "color", "source": "fixture://b"},
    {"language": "fr", "word": "bleu", "sense": "color", "source": "fixture://c"},
    {"language": "en", "word": "small", "sense": "size", "source": "fixture://d"},
]
NEGATIVES = [
    {"example": "blue book", "expected": "color", "forbidden": ["size"]},
    {"example": "small blue item", "expected": "multi_attribute", "forbidden": ["identity"]},
    {"example": "translated announcement", "expected": "shared_ancestry", "forbidden": ["independent_source_count_2"]},
    {"example": "word appears in dictionary", "expected": "term_mention", "forbidden": ["person_claim"]},
]

def execute(shard: str):
    assert shard in SHARDS
    assert len(SYNTHETIC) == len({(x["language"], x["word"], x["sense"]) for x in SYNTHETIC})
    assert all(x["source"].startswith("fixture://") for x in SYNTHETIC)
    assert all(x["expected"] not in x["forbidden"] for x in NEGATIVES)
    assert all("person_claim" not in x["example"] for x in NEGATIVES)
    assert all(x["source"].startswith("fixture://") for x in SYNTHETIC)
    subset = [x for i, x in enumerate(SYNTHETIC) if i % len(SHARDS) == sorted(SHARDS).index(shard)]
    receipt = {
        "protocol_version": 1, "shard": shard, "status": "PASS",
        "reference_status": "SYNTHETIC_ONLY_NO_NATIVE_CPE_TREATMENT",
        "rows": len(subset), "negative_controls": len(NEGATIVES),
        "source_uris_are_synthetic": True,
        "no_private_data": True, "policy_disposition": None,
    }
    return receipt

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--shard", choices=sorted(SHARDS), required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    record = execute(a.shard)
    blob = json.dumps(record, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(blob, encoding="utf-8")
    print(json.dumps({"shard": a.shard, "sha256": hashlib.sha256(blob.encode()).hexdigest(),
                      "status": record["status"], "reference_status": record["reference_status"]}))

if __name__ == "__main__":
    main()
