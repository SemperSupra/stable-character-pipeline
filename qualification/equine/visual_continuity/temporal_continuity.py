#!/usr/bin/env python3
"""Source-pinned decoded-video temporal continuity falsifier, not realism grading.

Tests whether a 48-frame 24fps public-original synthetic diagnostic clip has
abrupt local temporal jumps. Original smooth motion is only a negative control;
zero temporal jumps does NOT imply natural anatomy, gait or realistic appearance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

W, H, FRAMES = 160, 90, 48
SOURCE_SHA = '617f67ef76256ff03b5599b540374e1fbc42850df83b0e5a2c0dc65026b9074d'
MODEL_SHA = '9fbc0b517e1231c4032204c34cf9bed6eb76db349e81b390ee3812e43b331f33'
EXPECTED = {
    'side': 'd344c48270575db84fac7804289accc734010502ff5ecc6e8048b7823aeb9268',
    'face': '177eccaafa0d28799b842951d50cf47c27e5f609914b8c2be7e0a4ba42893380',
    'mane': 'fb5e09127f6575622bb0c7b14b5c8e83d248ace325b7c7c724c6361158548989',
    'tail': 'fd332817f2ba3efb715ce5e477cee4d3a3c9f2f0a72fc8b0b4dc2a961aee1147',
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_media(path, expected):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 2_000_000:
        raise ValueError('missing, linked or oversized media')
    if sha256(path.read_bytes()) != expected:
        raise ValueError('source media SHA mismatch')
    args = ['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
            '-show_entries', 'stream=codec_name,nb_read_frames,r_frame_rate', '-of', 'json', str(path)]
    data = json.loads(subprocess.run(args, capture_output=True, check=True, timeout=20).stdout)
    streams = data.get('streams', [])
    if len(streams) != 1 or streams[0].get('codec_name') != 'h264' or \
       streams[0].get('nb_read_frames') != str(FRAMES) or streams[0].get('r_frame_rate') != '24/1':
        raise ValueError('unexpected video codec/frame clock')


def decode(path):
    args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-i', str(path),
            '-map', '0:v:0', '-vf', f'scale={W}:{H}:flags=area,format=gray',
            '-vsync', '0', '-f', 'rawvideo', '-']
    raw = subprocess.run(args, capture_output=True, check=True, timeout=30).stdout
    sz = W * H
    if len(raw) != FRAMES * sz:
        raise ValueError('decoded video missing or extra frames')
    return [raw[i * sz:(i + 1) * sz] for i in range(FRAMES)]


def continuity(frames):
    if len(frames) != FRAMES or any(len(frame) != W * H for frame in frames):
        raise ValueError('wrong decoded frame count/shape')
    residual = []
    for f in range(1, FRAMES-1):
        prev, curr, nxt = frames[f-1], frames[f], frames[f+1]
        # Scale matches independent physical 2nd finite difference, /2 for clarity.
        total = sum(abs(2*c - p - n) for p, c, n in zip(prev, curr, nxt))
        residual.append(total / (2 * W * H))
    med = statistics.median(residual)
    mad = statistics.median(abs(x-med) for x in residual)
    threshold = max(med * 3.0, med + 8.0 * max(mad, 0.025))
    spikes = [i+1 for i,x in enumerate(residual) if x > threshold]
    return {
        'frame_count': FRAMES,
        'distinct_frame_sha256': len({sha256(f) for f in frames}),
        'second_difference_median': round(med, 6),
        'second_difference_mad': round(mad, 6),
        'second_difference_threshold': round(threshold, 6),
        'second_difference_max': round(max(residual), 6),
        'flagged_center_frames_zero_based': spikes,
    }


def qualify(view, path):
    if view not in EXPECTED:
        raise ValueError('unadmitted view')
    verify_media(path, EXPECTED[view])
    frames = decode(path)
    baseline = continuity(frames)
    # The previously deployed unique-frame observer cannot reject this permutation.
    attacked = frames[:]
    attacked[12], attacked[36] = attacked[36], attacked[12]
    challenger = continuity(attacked)
    if baseline['flagged_center_frames_zero_based']:
        raise RuntimeError(f'uncalibrated false positive on {view} real source')
    if len(challenger['flagged_center_frames_zero_based']) < 3:
        raise RuntimeError(f'failed to detect source-derived out-of-order video on {view}')
    if baseline['distinct_frame_sha256'] != 48 or challenger['distinct_frame_sha256'] != 48:
        raise RuntimeError('unique-frame comparator invalid')
    return {'source_mp4_sha256': EXPECTED[view], 'normal': baseline,
            'swapped_frames_12_36': challenger,
            'unique_frame_baseline_would_miss_swap': True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--media-dir', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = {'schema': 'equine.visual.temporal-continuity-challenger.v1',
              'source_scene_sha256': SOURCE_SHA, 'source_glb_sha256': MODEL_SHA,
              'scope': 'EXACT_ORIGINAL_SYNTHETIC_48F_24FPS_ONLY',
              'biological_quality': 'UNKNOWN', 'visual_acceptance': False,
              'source_custody': 'EXACT_MP4_SHA256_CHECKED', 'views': {}}
    for view in EXPECTED:
        result['views'][view] = qualify(view, args.media_dir/(view+'.mp4'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print('FOUR_VIEW_REAL_SOURCE_TEMPORAL_DIFFERENTIAL_PASS; BIOLOGICAL_REALISM_UNKNOWN')

if __name__ == '__main__':
    main()
