#!/usr/bin/env python3
"""Fixed-source, public-synthetic Video QA CPU/GPU/TPU execution qualification.

No credential handling, model downloads, network, package installation or persistent state.
Runs only inside the existing governed Agent Dispatch Kaggle launcher once admitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

SCHEMA = 'scp.videoqa.kaggle-motion-probe.v1'
RESULT_SCHEMA = 'scp.videoqa.kaggle-motion-receipt.v1'


def fixtures():
    # Identical 8 original, artificial 32-frame motion traces for CPU/GPU/TPU.
    # 4 stationary planted feet + 4 intentionally skidding planted feet.
    return [[[round(0.25 + (0.02 * t if i >= 4 else 0), 8), 0.0]
             for t in range(32)] for i in range(8)]


def source_bytes(traces):
    return json.dumps({'schema': SCHEMA, 'frame_delta_s': 0.1, 'traces': traces},
                      sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def validate_traces(traces):
    if not isinstance(traces, list) or len(traces) != 8:
        raise ValueError('exactly 8 artificial traces required')
    for trace in traces:
        if not isinstance(trace, list) or len(trace) != 32:
            raise ValueError('exactly 32 frames required')
        for point in trace:
            if (not isinstance(point, list) or len(point) != 2 or
                any(type(v) not in (float, int) or not math.isfinite(v) for v in point)):
                raise ValueError('nonfinite/malformed position')


def cpu_scores(traces):
    validate_traces(traces)
    return [sum(math.hypot(trace[t][0] - trace[t - 1][0],
                           trace[t][1] - trace[t - 1][1]) / 0.1
                for t in range(1, 32)) / 31 for trace in traces]


def gpu_scores(traces):
    validate_traces(traces)
    import torch
    if not torch.cuda.is_available() or torch.cuda.device_count() != 2:
        raise RuntimeError('GPU_T4X2_NOT_ATTESTED')
    names = [torch.cuda.get_device_name(i) for i in range(2)]
    if any('T4' not in n for n in names):
        raise RuntimeError('GPU_DEVICE_NOT_T4')
    observed = []
    # Exact same input batch split across both independently activated GPUs.
    for device_index in range(2):
        device = torch.device(f'cuda:{device_index}')
        local = torch.tensor(traces[device_index*4:(device_index+1)*4], dtype=torch.float32, device=device)
        velocity = torch.linalg.vector_norm(local[:, 1:, :] - local[:, :-1, :], dim=2) / 0.1
        scores = velocity.mean(dim=1)
        torch.cuda.synchronize(device_index)
        observed.extend([float(s) for s in scores.cpu().tolist()])
    return observed, {'backend': 'cuda', 'device_count': 2, 'device_models': names,
                      'separate_device_computation': True}


def tpu_scores(traces):
    validate_traces(traces)
    import jax
    import jax.numpy as jnp
    # Device enumeration alone is inadequate; require actual JAX computation.
    devices = jax.local_devices(backend='tpu')
    if jax.default_backend() != 'tpu' or len(devices) != 8:
        raise RuntimeError('TPU_V5E8_NOT_ATTESTED')

    @jax.pmap
    def measure(track):
        delta = track[1:, :] - track[:-1, :]
        return jnp.mean(jnp.sqrt(jnp.sum(delta * delta, axis=-1)) / 0.1)

    scores = measure(jnp.asarray(traces, dtype=jnp.float32))
    scores.block_until_ready()
    return [float(s) for s in scores.tolist()], {
        'backend': 'tpu', 'device_count': 8,
        'device_models': [str(d.device_kind) for d in devices],
        'separate_device_computation': True,
    }


def verify(scores, expected_source_sha, actual_source_sha):
    if expected_source_sha != actual_source_sha:
        raise ValueError('SOURCE_HASH_MISMATCH')
    if not isinstance(scores, list) or len(scores) != 8:
        raise ValueError('WRONG_RESULT_COUNT')
    for idx, value in enumerate(scores):
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError('NONFINITE_SCORE')
        expected = 0.0 if idx < 4 else 0.2
        if abs(value - expected) > 0.002:
            raise ValueError(f'METRIC_ORACLE_MISMATCH:{idx}')
    return ['PASS' if score <= 0.03 else 'FAIL' for score in scores]


def run(kind: str):
    traces = fixtures()
    data = source_bytes(traces)
    sha = hashlib.sha256(data).hexdigest()
    if kind == 'cpu':
        scores = cpu_scores(traces)
        device = {'backend': 'cpu', 'device_count': os.cpu_count() or 1,
                  'device_models': [], 'separate_device_computation': False}
    elif kind == 'gpu':
        scores, device = gpu_scores(traces)
    elif kind == 'tpu':
        scores, device = tpu_scores(traces)
    else:
        raise ValueError('INVALID_BACKEND')
    verdicts = verify(scores, sha, hashlib.sha256(data).hexdigest())
    result = {'schema': RESULT_SCHEMA, 'workload': 'videoqa-motion-v1',
              'requested_backend': kind, 'actual_backend': device['backend'],
              'status': 'PASS', 'source_sha256': sha, 'device': device,
              'metric': 'mean_planted_foot_speed_m_s',
              'metric_scores': [round(float(s), 6) for s in scores],
              'verdicts': verdicts, 'expected_verdicts': ['PASS'] * 4 + ['FAIL'] * 4,
              'scope': 'original-synthetic-numeric-oracle-only',
              'limitations': ['Not decoded video', 'Not human biomechanics',
                              'No pretrained physics judge or corrective flywheel tested']}
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--backend', choices=('cpu', 'gpu', 'tpu'), required=True)
    p.add_argument('--out', default=None)
    a = p.parse_args()
    try:
        output = run(a.backend)
    except Exception as exc:
        # No exception string, untrusted traceback, provider paths or credentials in receipts.
        print('VIDEOQA_PROBE_FAIL=' + type(exc).__name__, file=sys.stderr)
        sys.exit(2)
    path = a.out or ('/kaggle/working/videoqa_probe_receipt.json' if Path('/kaggle/working').is_dir() else '')
    encoded = json.dumps(output, sort_keys=True, indent=2) + '\n'
    if path:
        Path(path).write_text(encoded)
    else:
        print(encoded)
