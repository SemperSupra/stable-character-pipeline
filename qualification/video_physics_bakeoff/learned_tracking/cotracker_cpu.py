#!/usr/bin/env python3
"""First rights-original *real checkpoint* CPU video point-tracker RDT&E.
Never treat motion-tracking score as evidence of human anatomy or real-world physics.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

FRAMES, WIDTH, HEIGHT, FPS = 12, 128, 128, 8
CO_SRC_SHA = '82e02e8029753ad4ef13cf06be7f4fc5facdda4d'
CO_WEIGHTS_SHA = '2670d4562ed69326dda775a26e54883925cd11b6fc9b24cb7aa9f8078bce7834'


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def truth():
    return [(24.0 + 3.0*t, 60.0) for t in range(FRAMES)]


def video_rgb():
    """Exact original moving-checker video; no person or third-party image."""
    frames = bytearray()
    for t, (cx, cy) in enumerate(truth()):
        for y in range(HEIGHT):
            for x in range(WIDTH):
                # Background is moderately textured and unchanging.
                b = 26 + ((x*7 + y*11) % 31)
                if abs(x-cx) <= 7 and abs(y-cy) <= 7:
                    frames.extend(((235 if (x+y) % 2 else 210),
                                   (145 if (x-y) % 2 else 225), 35))
                else:
                    frames.extend((b, b + 7, b + 12))
    return bytes(frames)


def decoded_h264(directory):
    """Actually encode and decode native H.264; fail on frame shape mismatch."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    clip = directory / 'synthetic.mp4'
    raw = video_rgb()
    encode = ['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-f','rawvideo',
              '-pix_fmt','rgb24','-video_size',f'{WIDTH}x{HEIGHT}',
              '-framerate',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-crf','18',
              '-pix_fmt','yuv420p',str(clip)]
    subprocess.run(encode, input=raw, capture_output=True, check=True, timeout=40)
    decode = ['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-i',str(clip),
              '-map','0:v:0','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    decoded = subprocess.run(decode, capture_output=True, check=True, timeout=40).stdout
    if len(decoded) != len(raw):
        raise ValueError('DECODED_FRAME_LENGTH_INCONSISTENT')
    return clip, decoded


def adjudicate(points, visible):
    if len(points) != FRAMES or len(visible) != FRAMES:
        raise ValueError('TRACK_LENGTH_INCONSISTENT')
    errors = []
    for point, on, target in zip(points, visible, truth()):
        if len(point) != 2 or any(not math.isfinite(float(v)) for v in point):
            raise ValueError('TRACK_NONFINITE')
        if type(on) is not bool:
            raise ValueError('VISIBILITY_NOT_BOOLEAN')
        errors.append(round(math.hypot(float(point[0])-target[0],float(point[1])-target[1]),4)
                      if on else None)
    observed = [e for e in errors if e is not None]
    # Independent quality gate deliberately NOT equivalent to inference-executed.
    quality = 'UNKNOWN' if len(observed)<FRAMES-2 else ('PASS' if sum(observed)/len(observed)<=5 else 'FAIL')
    return {'gate':quality, 'visible_frames':len(observed),
            'pixel_errors':errors,'mae_px':round(sum(observed)/len(observed),4) if observed else None}


def infer(src, checkpoint, output, directory):
    import numpy as np
    import torch
    if torch.cuda.is_available():
        raise ValueError('DISPOSABLE_CPU_LANE_NOT_CPU_ONLY')
    torch.set_num_threads(2)
    if digest(checkpoint) != CO_WEIGHTS_SHA:
        raise ValueError('MODEL_CHECKPOINT_SHA_MISMATCH')
    if not (Path(src)/'cotracker'/'predictor.py').is_file():
        raise ValueError('PINNED_SOURCE_MISSING')
    sys.path.insert(0,str(Path(src).resolve()))
    from cotracker.predictor import CoTrackerPredictor
    clip, raw = decoded_h264(directory)
    array = np.frombuffer(raw,dtype=np.uint8).copy().reshape(FRAMES,HEIGHT,WIDTH,3)
    tensor = torch.from_numpy(array).permute(0,3,1,2).unsqueeze(0).float()
    queries = torch.tensor([[[0.0,truth()[0][0],truth()[0][1]]]],dtype=torch.float32)
    start = time.monotonic()
    model = CoTrackerPredictor(checkpoint=str(checkpoint),offline=True,window_len=60).eval().cpu()
    with torch.inference_mode():
        tracks, v = model(tensor,queries=queries)
    duration = time.monotonic()-start
    points = tracks[0,:,0,:].cpu().tolist()
    visible = [bool(x) for x in v[0,:,0].cpu().tolist()]
    measured = adjudicate(points,visible)
    receipt = {'schema':'scp.cotracker3.first-actual-cpu.v1','inference':'EXECUTED',
               'science':measured,'frames':FRAMES,'width':WIDTH,'height':HEIGHT,
               'source_repo':'facebookresearch/co-tracker','source_git_sha':CO_SRC_SHA,
               'source_license':'CC BY-NC 4.0 — research only',
               'checkpoint_sha256':CO_WEIGHTS_SHA,
               'evaluator_sha256':digest(__file__),
               'video_h264_sha256':digest(clip),
               'decoded_rgb_sha256':hashlib.sha256(raw).hexdigest(),
               'torch_version':str(torch.__version__),'device':'cpu',
               'runtime_seconds':round(duration,3),'predicted_points':points,
               'truth_points':truth(),
               'limitations':['Checkerboard-style synthetic out-of-domain object only',
                              'One point queried; not a representative tracking benchmark',
                              'Pixel motion metrics do not establish gait, anatomy, or physical realism',
                              'Noncommercial upstream licensing must be rechecked before promotion']}
    Path(output).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print('COTRACKER_MODEL_INFERENCE_EXECUTED=1')
    print('COTRACKER_RESEARCH_SCIENCE_GATE='+measured['gate'])
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('source','checkpoint','out','workdir'):
        p.add_argument('--'+n,required=True)
    a=p.parse_args()
    try:infer(a.source,a.checkpoint,a.out,a.workdir)
    except Exception as exc:
        # Public CI must expose a useful short failure class without raw source data.
        print('COTRACKER_RDT_E_FAILED='+type(exc).__name__+':'+str(exc)[:180],file=sys.stderr)
        sys.exit(2)
