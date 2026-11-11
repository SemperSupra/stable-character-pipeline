#!/usr/bin/env python3
"""Frame-decoded, reference-free luma stability metric. Scene cuts abstain."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

MAX_PIXELS = 1920 * 1080
MAX_FRAMES = 300


def probe(path):
    p = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_frames',
                        '-show_entries', 'stream=width,height,nb_read_frames', '-of', 'json', str(path)],
                       capture_output=True, text=True, timeout=15, check=True)
    streams = json.loads(p.stdout).get('streams', [])
    if len(streams) != 1:
        raise ValueError('expected one video stream')
    s = streams[0]
    w, h, n = int(s['width']), int(s['height']), int(s['nb_read_frames'])
    if w < 4 or h < 4 or w*h > MAX_PIXELS or n < 4 or n > MAX_FRAMES:
        raise ValueError('video outside bounded RDT&E profile')
    return w, h, n


def analyze(path):
    path = pathlib.Path(path)
    w, h, n = probe(path)
    cmd = ['ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-map', '0:v:0',
           '-fps_mode', 'passthrough', '-an', '-pix_fmt', 'gray', '-f', 'rawvideo', '-']
    raw = subprocess.run(cmd, capture_output=True, timeout=35, check=True).stdout
    frame_size = w*h
    if len(raw) != n*frame_size:
        raise ValueError('decoded frame count and raw-byte length disagree')
    means = []
    diffs = []
    prior = None
    for i in range(n):
        frame = raw[i*frame_size:(i+1)*frame_size]
        means.append(sum(frame)/frame_size)
        if prior is not None:
            diffs.append(sum(abs(a-b) for a,b in zip(frame, prior))/frame_size)
        prior = frame
    luma_delta = [means[i]-means[i-1] for i in range(1,n)]
    significant = [(i+1,d) for i,d in enumerate(luma_delta) if abs(d) >= 18.0]
    alternating = sum(significant[i][1]*significant[i-1][1] < 0 for i in range(1,len(significant)))
    findings = []
    uncertainties = []
    if max(means) <= 3.0:
        findings.append('ALL_BLACK_VIDEO')
    if len(significant) >= max(8, n//3) and alternating >= (len(significant)-1)*0.7:
        findings.append('HIGH_FREQUENCY_LUMA_FLICKER')
    elif significant:
        uncertainties.append('SCENE_CUT_OR_LIGHTING_CHANGE')
    status = 'FAIL' if findings else ('UNKNOWN' if uncertainties else 'PASS')
    hsh = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'schema':'scp.temporal-pixels.v1', 'verdict':status, 'input_sha256':hsh,
            'dimensions':[w,h], 'decoded_frames':n,
            'metrics':{'mean_luma_min':round(min(means),4), 'mean_luma_max':round(max(means),4),
                       'mean_frame_change':round(sum(diffs)/len(diffs),4),
                       'large_luma_jumps':len(significant), 'alternating_jump_count':alternating},
            'findings':findings, 'uncertainties':uncertainties,
            'limits':['Large scene cuts and intentional lighting effects can mimic flicker',
                      'This metric measures image brightness, not physics, visual naturalness or causal defect source',
                      'RDT&E synthetic thresholds are not calibrated for artistic intent']}


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('video')
    ap.add_argument('--out')
    args=ap.parse_args()
    try:
        obj=analyze(args.video)
        payload=json.dumps(obj,indent=2)+'\n'
        if args.out:pathlib.Path(args.out).write_text(payload)
        else:sys.stdout.write(payload)
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print('INVALID_EVIDENCE:',str(exc),file=sys.stderr)
        sys.exit(2)
