#!/usr/bin/env python3
"""Read-only independent result oracle for a fixed Kaggle direct video-QA notebook.

Scientific receipt verification is *not* native provider job/version verification.
The trusted executor must additionally verify exact Kaggle identity, native version,
terminal state, quota admission and downloaded byte digest.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = 'scp.videoqa.kaggle-motion-receipt.v1'
FIXTURE_SHA256 = 'f40ded92073bc8ee9d8680b47cdd4da3a92f270ab218224e8f252e3b99639f20'
VALID_BACKENDS = {'gpu': ('cuda', 2), 'tpu': ('tpu', 8), 'cpu': ('cpu', 1)}


def verify(record: dict, expected_backend: str, expected_code_sha: str) -> dict:
    if expected_backend not in VALID_BACKENDS:
        raise ValueError('UNSUPPORTED_BACKEND')
    if not isinstance(expected_code_sha, str) or re.fullmatch(r'[0-9a-f]{64}', expected_code_sha) is None:
        raise ValueError('INVALID_EXPECTED_CODE_SHA')
    if not isinstance(record, dict) or record.get('schema') != SCHEMA or record.get('workload') != 'videoqa-motion-v1' or record.get('status') != 'PASS':
        raise ValueError('UNTRUSTED_RECEIPT')
    actual, count = VALID_BACKENDS[expected_backend]
    if (record.get('requested_backend') != expected_backend or
            record.get('actual_backend') != actual or
            record.get('source_sha256') != FIXTURE_SHA256 or
            record.get('executed_source_sha256') != expected_code_sha):
        raise ValueError('SOURCE_OR_BACKEND_MISMATCH')
    d = record.get('device')
    if not isinstance(d, dict) or d.get('backend') != actual:
        raise ValueError('MISSING_DEVICE_WITNESS')
    n = d.get('device_count')
    if type(n) is not int or (n != count if expected_backend != 'cpu' else n < 1):
        raise ValueError('DEVICE_COUNT_INVALID')
    if expected_backend in ('gpu', 'tpu'):
        if d.get('separate_device_computation') is not True:
            raise ValueError('DEVICE_COMPUTATION_NOT_ATTESTED')
        names = d.get('device_models')
        if not isinstance(names, list) or len(names) != count or any(not isinstance(v, str) for v in names):
            raise ValueError('DEVICE_MODELS_UNTRUSTED')
        if expected_backend == 'gpu' and any('T4' not in v for v in names):
            raise ValueError('UNEXPECTED_GPU_MODEL')
        if expected_backend == 'tpu' and any('TPU' not in v.upper() for v in names):
            raise ValueError('UNEXPECTED_TPU_MODEL')
    scores = record.get('metric_scores')
    verdicts = record.get('verdicts')
    if not isinstance(scores, list) or len(scores) != 8 or verdicts != ['PASS'] * 4 + ['FAIL'] * 4:
        raise ValueError('WRONG_MEASUREMENT_SHAPE')
    for idx, v in enumerate(scores):
        target = 0.0 if idx < 4 else 0.2
        if type(v) not in (float, int) or not math.isfinite(v) or abs(v - target) > 0.002:
            raise ValueError('BAD_NUMERIC_ORACLE')
    if record.get('scope') != 'original-synthetic-numeric-oracle-only':
        raise ValueError('SCOPE_MISMATCH')
    return {'schema': 'scp.videoqa.direct-adjudication.v1',
            'verdict': 'SCIENTIFIC_SYNTHETIC_CONTROL_PASS',
            'backend': expected_backend, 'code_sha256': expected_code_sha,
            'fixture_sha256': FIXTURE_SHA256, 'measurements_checked': 8,
            'provider_status': 'NOT_VERIFIED_BY_THIS_TOOL'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipt', required=True)
    p.add_argument('--backend', choices=sorted(VALID_BACKENDS), required=True)
    p.add_argument('--code-sha256', required=True)
    a = p.parse_args()
    try:
        raw = Path(a.receipt).read_bytes()
        if len(raw) > 65536:
            raise ValueError('OVERSIZED_RECEIPT')
        verdict = verify(json.loads(raw.decode('utf-8')), a.backend, a.code_sha256)
        verdict['receipt_sha256'] = hashlib.sha256(raw).hexdigest()
        print(json.dumps(verdict, sort_keys=True))
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        print('DIRECT_ADJUDICATION_BLOCKED=' + type(error).__name__, file=sys.stderr)
        sys.exit(2)
