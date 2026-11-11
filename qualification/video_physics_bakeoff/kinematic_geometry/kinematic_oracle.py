#!/usr/bin/env python3
"""Source-observed 3D gait geometry witness. No learned model and no anatomy certification."""
import argparse
import hashlib
import json
import math
import pathlib
import sys


def vsub(a, b):
    return [x - y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    return math.sqrt(dot(a, a))


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def analyze(data):
    """Return fail-dominant PASS/FAIL/UNKNOWN based only on trusted source coordinates."""
    findings = []
    unknown = []
    measurements = []
    if data.get('schema') != 'scp.gait-geometry.v1':
        raise ValueError('bad schema')
    frames = data.get('frames')
    pole = data.get('approved_bend_pole')
    lengths = data.get('segment_lengths_m')
    if not isinstance(frames, list) or len(frames) < 3 or not isinstance(pole, list) or len(pole) != 3 or not isinstance(lengths, list) or len(lengths) != 2:
        raise ValueError('missing frame/pole/segment information')
    for n in (*pole, *lengths):
        if not isinstance(n, (int, float)) or isinstance(n, bool) or not math.isfinite(n):
            raise ValueError('nonfinite or malformed model parameters')
    if norm(pole) < 1e-6 or min(lengths) <= 0:
        raise ValueError('unusable pole or segment lengths')
    pole = [v / norm(pole) for v in pole]
    last = None
    prior_t = None
    for idx, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError('malformed frame')
        t = frame.get('time_s')
        if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t) or (prior_t is not None and t <= prior_t):
            raise ValueError('invalid frame time')
        prior_t = t
        points = []
        for key in ('hip', 'knee', 'ankle'):
            p = frame.get(key)
            if not isinstance(p, list) or len(p) != 3 or any(not isinstance(x, (int, float)) or isinstance(x, bool) or not math.isfinite(x) for x in p):
                raise ValueError('missing/nonfinite joint coordinate')
            points.append(p)
        hip, knee, ankle = points
        thigh, shin = vsub(hip, knee), vsub(ankle, knee)
        a, b = norm(thigh), norm(shin)
        if min(a, b) <= 1e-8:
            findings.append({'frame': idx, 'code': 'DEGENERATE_SEGMENT'})
            continue
        if abs(a - lengths[0]) > 0.01 or abs(b - lengths[1]) > 0.01:
            findings.append({'frame': idx, 'code': 'SEGMENT_LENGTH_VIOLATION', 'thigh_m': a, 'shin_m': b})
        cosine = max(-1, min(1, dot(thigh, shin) / (a * b)))
        internal = math.degrees(math.acos(cosine))
        flexion = 180 - internal
        sided = dot(cross(thigh, shin), pole) / (a * b)
        if abs(sided) < 0.025:
            unknown.append({'frame': idx, 'code': 'STRAIGHT_OR_UNRESOLVED_BEND'})
        elif sided < -0.025:
            findings.append({'frame': idx, 'code': 'REVERSED_KNEE_BEND', 'bend_signed': sided})
        if flexion > 155:
            findings.append({'frame': idx, 'code': 'EXTREME_FLEXION', 'degrees': flexion})
        measurements.append({'frame': idx, 'flexion_deg': round(flexion, 4), 'bend_signed': round(sided, 6)})
        if last is not None:
            delta = math.sqrt(sum((x - y) ** 2 for x, y in zip(knee, last['knee']))) / (t - last['time_s'])
            if delta > 6:
                findings.append({'frame': idx, 'code': 'KNEE_SPEED_SPIKE', 'speed_m_s': round(delta, 4)})
        last = {'knee': knee, 'time_s': t}
    status = 'FAIL' if findings else ('UNKNOWN' if unknown else 'PASS')
    return {'status': status, 'findings': findings, 'uncertainties': unknown, 'measurements': measurements,
            'limits': ['3D points are supplied observations, not independently recovered anatomy',
                       'bend-pole, segment lengths and time base must be independently calibrated',
                       'single-leg geometry does not prove physical balance or natural gait']}


def run(source, output):
    raw = pathlib.Path(source).read_bytes()
    data = json.loads(raw)
    result = analyze(data)
    result.update({'schema': 'scp.gait-geometry-receipt.v1', 'input_sha256': hashlib.sha256(raw).hexdigest()})
    payload = json.dumps(result, indent=2, sort_keys=True) + '\n'
    if output:
        pathlib.Path(output).write_text(payload)
    else:
        sys.stdout.write(payload)
    return result['status']


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('input')
    p.add_argument('--out')
    a = p.parse_args()
    try:
        run(a.input, a.out)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'INVALID_EVIDENCE: {exc}', file=sys.stderr)
        sys.exit(2)
