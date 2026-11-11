#!/usr/bin/env python3
"""Strict reference-based PSNR/SSIM A/B analysis; no nonstdlib Python dependencies."""
import hashlib
import json
import math
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(sys.argv[1]).resolve()

def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def frames(p):
    cmd = ['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,nb_read_frames,r_frame_rate', '-of', 'json', str(p)]
    stream = json.loads(subprocess.check_output(cmd))['streams'][0]
    return (int(stream['width']), int(stream['height']), stream['r_frame_rate'], int(stream['nb_read_frames']))

def metric(name, kind, count):
    source = (ROOT / f'{name}.{kind}').read_text()
    field = 'psnr_avg' if kind == 'psnr' else 'All'
    values = []
    for line in source.splitlines():
        m = re.search(r'(?:^|\s)' + field + r':([0-9]+(?:\.[0-9]+)?)', line)
        if not m:
            raise ValueError(f'{name}/{kind} missing expected field')
        number = float(m.group(1))
        if not math.isfinite(number):
            raise ValueError(f'{name}/{kind} nonfinite score')
        values.append(number)
    if len(values) != count:
        raise ValueError(f'{name}/{kind} missing or extra frames: {len(values)} != {count}')
    return sum(values) / len(values)

reference = ROOT / 'reference.mkv'
baseline, candidate = ROOT / 'baseline.mp4', ROOT / 'candidate.mp4'
rmeta = frames(reference)
if rmeta != (160, 120, '12/1', 36):
    raise ValueError(f'unexpected reference shape/time: {rmeta}')
if frames(baseline) != rmeta or frames(candidate) != rmeta:
    raise ValueError('frame clock or dimensions changed')
results = {}
for name, path in [('baseline', baseline), ('candidate', candidate)]:
    results[name] = {'sha256': digest(path), 'psnr_db': metric(name, 'psnr', 36), 'ssim': metric(name, 'ssim', 36)}
psnr_delta = results['candidate']['psnr_db'] - results['baseline']['psnr_db']
ssim_delta = results['candidate']['ssim'] - results['baseline']['ssim']
status = 'PROVISIONAL_IMPROVEMENT' if psnr_delta >= 3 and ssim_delta >= 0.02 else 'REJECT'
receipt = {'schema':'scp.video-reference-ab.v1', 'reference_sha256':digest(reference), 'reference_metadata':{'width':160,'height':120,'fps':12,'frames':36}, 'baseline':results['baseline'], 'candidate':results['candidate'], 'delta':{'psnr_db':psnr_delta,'ssim':ssim_delta}, 'result':status, 'limitations':['Synthetic original test pattern; source re-render, not video restoration','PSNR/SSIM measure reference similarity, not anatomy, physics, semantics, identity or realism','Acceptance thresholds are experimental; independent calibration required']}
(ROOT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
if status != 'PROVISIONAL_IMPROVEMENT':sys.exit(1)
