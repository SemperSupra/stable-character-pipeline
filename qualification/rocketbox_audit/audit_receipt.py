#!/usr/bin/env python3
"""Read-only frozen MIT native-gait evidence audit; never claims human acceptance."""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

SCHEMA = 'scp.mit_rocketbox_native_walk.v1'
FRAMES = (0, 3, 18, 36, 54, 71)
ACTORS = ('RB_RB_F01_root', 'RB_RB_F02_root')
BONES = ('Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 R Thigh', 'Bip01 R Calf',
         'Bip01 L UpperArm', 'Bip01 R UpperArm', 'Bip01 L Forearm', 'Bip01 R Forearm')
MEDIA = {'front.mp4': '7f112a5c15664ebca6321e0e1ce9371f67709486b4c2a050be14498b01126a86',
         'oblique.mp4': 'cd877f23196d6f949e16d72d2ffec713ccc521052129919f06aa016fe42eaaf9'}

def denial(reason):
    raise ValueError(reason)

def no_duplicate_pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out: denial('DUPLICATE_JSON_KEY:' + k)
        out[k] = v
    return out

def load_receipt(path):
    def no_constant(value): denial('INVALID_JSON_CONSTANT:' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      object_pairs_hook=no_duplicate_pairs, parse_constant=no_constant)

def numeric(v, label):
    if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v):
        denial('NONFINITE_OR_NONNUMERIC:' + label)
    return float(v)

def audit(r):
    if not isinstance(r, dict): denial('RECEIPT_NOT_OBJECT')
    must = {'schema': SCHEMA, 'status': 'NATIVE_SKINNED_WALK_SOURCE_ONLY_NOT_HUMAN_ACCEPTED',
            'source_rights': 'MIT_with_notice', 'frame_count': 72, 'fps': 12,
            'profile': 'two_80_bone_actual_source_mesh_actors',
            'bone_basis_calibrated': False, 'foot_contact': 'UNKNOWN',
            'human_gait': 'UNKNOWN', 'camera_visual_acceptance': 'UNKNOWN',
            'product_accepted': False}
    for k, v in must.items():
        if k not in r or type(r[k]) is not type(v) or r[k] != v:
            denial('CLAIM_OR_SOURCE_CONTRACT_MISMATCH:' + k)
    if r.get('views') != {'front': 72, 'oblique': 72}: denial('TWO_CAMERA_FRAME_COUNT_MISMATCH')
    samples = r.get('samples')
    if not isinstance(samples, list) or len(samples) != len(FRAMES): denial('SAMPLE_SET_MISMATCH')
    trajectory = [[], []]
    liveness = [[], []]
    for i, (entry, frame) in enumerate(zip(samples, FRAMES)):
        if not isinstance(entry, dict) or type(entry.get('frame')) is not int or entry['frame'] != frame:
            denial('SAMPLE_FRAME_ORDER_MISMATCH:' + str(i))
        actors = entry.get('actors')
        if not isinstance(actors, list) or len(actors) != 2: denial('SAMPLE_ACTOR_COUNT_MISMATCH:' + str(i))
        for j, (a, name) in enumerate(zip(actors, ACTORS)):
            if not isinstance(a, dict) or a.get('root') != name:
                denial('SAMPLE_ACTOR_ID_MISMATCH:' + str(i) + ':' + str(j))
            x = numeric(a.get('mean_x'), 'mean_x')
            bounds = a.get('bounds_x')
            if not isinstance(bounds, list) or len(bounds) != 2: denial('MISSING_MESH_BOUNDS')
            lo, hi = (numeric(v, 'bounds_x') for v in bounds)
            if lo > x or x > hi or lo >= hi: denial('MESH_MEAN_OUTSIDE_BOUNDS')
            numeric(a.get('evaluated_mesh_min_z'), 'min_z')
            bone = a.get('animated_local_bones')
            if not isinstance(bone, dict) or set(bone) != set(BONES): denial('MISSING_OR_EXTRA_LOCAL_BONE')
            for n, angle in bone.items(): numeric(angle, n)
            trajectory[j].append(x)
            liveness[j].append(numeric(bone['Bip01 L Thigh'], 'L thigh'))
    for j in range(2):
        if abs(trajectory[j][-1] - trajectory[j][0]) < 1.0:
            denial('EVALUATED_MESH_CENTER_STATIC:' + str(j))
        if max(liveness[j]) - min(liveness[j]) < .3:
            denial('SAMPLED_LOCAL_THIGH_STATIC:' + str(j))
    separation = [abs(trajectory[1][i] - trajectory[0][i]) for i in range(6)]
    if separation[-1] >= separation[0] - 1.0: denial('NO_MEASURED_ACTOR_APPROACH')
    return {'schema': 'scp.mit_rocketbox_independent_artifact_audit.v1',
            'status': 'INTEGRITY_AND_SIX_SAMPLE_KINEMATIC_LIVENESS_ONLY',
            'source_schema': SCHEMA, 'sampled_frames': list(FRAMES),
            'first_last_measured_center_separation_m': [round(separation[0], 5), round(separation[-1], 5)],
            'physical_contact': 'UNKNOWN', 'human_gait': 'UNKNOWN',
            'two_camera_pixel_visibility': 'NOT_RUN', 'product_accepted': False}

def audit_media(directory):
    directory = Path(directory)
    evidence = {}
    for name, expected in MEDIA.items():
        matches = list(directory.rglob(name))
        if len(matches) != 1: denial('MEDIA_NOT_UNIQUE:' + name)
        path = matches[0]
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha != expected: denial('MEDIA_DIGEST_MISMATCH:' + name)
        p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                            '-count_frames', '-show_entries',
                            'stream=nb_read_frames,avg_frame_rate,duration',
                            '-of', 'json', str(path)], capture_output=True, text=True)
        if p.returncode: denial('FFPROBE_FAILED:' + name)
        data = json.loads(p.stdout)
        streams = data.get('streams', [])
        if len(streams) != 1: denial('VIDEO_STREAM_MISMATCH:' + name)
        s = streams[0]
        if s.get('nb_read_frames') != '72' or s.get('avg_frame_rate') != '12/1':
            denial('VIDEO_CLOCK_FRAME_MISMATCH:' + name)
        if abs(numeric(float(s.get('duration', 'nan')), 'duration') - 6.0) > .01:
            denial('VIDEO_DURATION_MISMATCH:' + name)
        evidence[name] = {'sha256': sha, 'frames': 72, 'fps': '12/1', 'duration_seconds': 6.0}
    return evidence

def main():
    p = argparse.ArgumentParser()
    p.add_argument('receipt', type=Path)
    p.add_argument('--media-dir', type=Path)
    p.add_argument('--out', type=Path)
    a = p.parse_args()
    result = audit(load_receipt(a.receipt))
    if a.media_dir: result['native_h264_source_sha_verification'] = audit_media(a.media_dir)
    raw = json.dumps(result, sort_keys=True, indent=2) + '\n'
    if a.out: a.out.write_text(raw, encoding='utf-8')
    print(raw, end='')

if __name__ == '__main__':
    main()
