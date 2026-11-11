#!/usr/bin/env python3
"""Second actual pretrained CoTracker3 research rep: occlusion and direction-change controls.

No model acceptance inferred from its own visibility probabilities or synthetic scores.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from cotracker_cpu import FRAMES, HEIGHT, WIDTH, CO_SRC_SHA, CO_WEIGHTS_SHA, digest, truth, video_rgb


PROFILES=('baseline','occluded','reversed_direction')


def ground_truth(profile):
    if profile not in PROFILES:raise ValueError('UNKNOWN_ORIGINAL_SYNTHETIC_PROFILE')
    if profile=='reversed_direction':
        return [(24.+(3.*t if t<=5 else 15.-3.*(t-5)),60.) for t in range(FRAMES)]
    return truth()


def truth_visible(profile):
    return [not (profile=='occluded' and 4<=t<=7) for t in range(FRAMES)]


def frames(profile):
    if profile not in PROFILES:raise ValueError('UNKNOWN_PROFILE')
    if profile=='baseline':return video_rgb()
    raw=bytearray(video_rgb())
    if profile=='occluded':
        for t in range(4,8):
            # Solid static wall covers the full target; true target continues behind it.
            for y in range(46,75):
                for x in range(0,85):
                    i=((t*HEIGHT+y)*WIDTH+x)*3
                    raw[i:i+3]=bytes((118,118,118))
        return bytes(raw)
    for t in range(FRAMES):
        # Restore exactly original stable texture for this entire frame.
        target_x,target_y=ground_truth(profile)[t]
        base=bytearray()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                b=26+((x*7+y*11)%31)
                if abs(x-target_x)<=7 and abs(y-target_y)<=7:
                    base.extend((235 if (x+y)%2 else 210,
                                 145 if (x-y)%2 else 225,35))
                else:base.extend((b,b+7,b+12))
        raw[t*WIDTH*HEIGHT*3:(t+1)*WIDTH*HEIGHT*3]=base
    return bytes(raw)


def encode_decode(profile,folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    src=frames(profile)
    video=folder/(profile+'.mp4')
    enc=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-f','rawvideo',
         '-pix_fmt','rgb24','-video_size',f'{WIDTH}x{HEIGHT}','-framerate','8',
         '-i','pipe:0','-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p',str(video)]
    subprocess.run(enc,input=src,check=True,capture_output=True,timeout=40)
    dec=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-i',str(video),
         '-map','0:v:0','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    raw=subprocess.run(dec,capture_output=True,check=True,timeout=40).stdout
    if len(raw)!=len(src):raise ValueError('FRAME_DECODE_SHAPE_MISMATCH')
    return video,raw


def measure(profile,points,observed_visible):
    source_truth=ground_truth(profile)
    target_visible=truth_visible(profile)
    if len(points)!=FRAMES or len(observed_visible)!=FRAMES:
        raise ValueError('MODEL_OUTPUT_FRAME_COUNT_MISMATCH')
    errs=[]
    for pt,on,gt,gt_on in zip(points,observed_visible,source_truth,target_visible):
        if len(pt)!=2 or any(not math.isfinite(float(v)) for v in pt) or type(on) is not bool:
            raise ValueError('INVALID_MODEL_PREDICTION')
        errs.append(round(math.hypot(pt[0]-gt[0],pt[1]-gt[1]),4) if gt_on and on else None)
    good=[v for v in errs if v is not None]
    missed=sum(bool(gt) and not bool(on) for gt,on in zip(target_visible,observed_visible))
    false_visible=sum((not bool(gt)) and bool(on) for gt,on in zip(target_visible,observed_visible))
    return {'profile':profile,'visible_gt_frames':sum(target_visible),
            'predicted_visible_frames':sum(observed_visible),
            'missed_visible_frames':missed,'false_visible_during_occlusion':false_visible,
            'ground_truth_visible_mae_px':round(sum(good)/len(good),4) if good else None,
            'per_frame_observed_errors_px':errs,
            'acceptance':'UNQUALIFIED_RESEARCH_OBSERVATION'}


def run(source,checkpoint,folder,outfile):
    import numpy as np
    import torch
    from cotracker.predictor import CoTrackerPredictor
    if torch.cuda.is_available():raise ValueError('WRONG_EXECUTION_CLASS')
    torch.set_num_threads(2)
    if digest(checkpoint)!=CO_WEIGHTS_SHA:raise ValueError('WEIGHT_SOURCE_SHA_MISMATCH')
    model=CoTrackerPredictor(checkpoint=str(checkpoint),offline=True,window_len=60).eval().cpu()
    outputs=[]
    for profile in PROFILES:
        clip,raw=encode_decode(profile,Path(folder))
        tensor=torch.from_numpy(np.frombuffer(raw,dtype=np.uint8).copy()
                .reshape(FRAMES,HEIGHT,WIDTH,3)).permute(0,3,1,2).unsqueeze(0).float()
        x,y=ground_truth(profile)[0]
        queries=torch.tensor([[[0.,x,y]]],dtype=torch.float32)
        start=time.monotonic()
        with torch.inference_mode():tracks,vis=model(tensor,queries=queries)
        elapsed=time.monotonic()-start
        points=tracks[0,:,0,:].cpu().tolist()
        visible=[bool(v) for v in vis[0,:,0].cpu().tolist()]
        row=measure(profile,points,visible)
        row.update(h264_sha256=digest(clip),decoded_sha256=hashlib.sha256(raw).hexdigest(),
                   model_seconds=round(elapsed,3),predicted_xy=points,
                   ground_truth_xy=ground_truth(profile),
                   ground_truth_visibility=truth_visible(profile))
        outputs.append(row)
        print(f'COTRACKER_PROFILE_MEASURED={profile}')
    receipt={'schema':'scp.cotracker3.robustness.v1',
             'inference':'REAL_PRETRAINED_CPU',
             'checkpoint_sha256':CO_WEIGHTS_SHA,'upstream_git_sha':CO_SRC_SHA,
             'source_code_sha256':digest(__file__),'model_license':'CC BY-NC 4.0',
             'device':'cpu','torch_version':str(torch.__version__),
             'profiles':outputs,'status':'MEASURED_NOT_PROMOTED',
             'limitations':['One original synthetic checker object in each 12-frame clip',
               'Occlusion ground truth is synthetic and independent of tracker self-confidence',
               'No human, gait, physics, cross-camera, diversity or product acceptance'] }
    Path(outfile).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    a=argparse.ArgumentParser()
    for key in ('source','checkpoint','workdir','out'):a.add_argument('--'+key,required=True)
    opt=a.parse_args()
    try:
        # Source must be checked out at an immutable SHA by the caller.
        sys.path.insert(0,str(Path(opt.source).resolve()))
        r=run(opt.source,opt.checkpoint,opt.workdir,opt.out)
        print('COTRACKER_ROBUSTNESS_COMPLETED='+str(len(r['profiles'])))
    except Exception as exc:
        print('COTRACKER_ROBUSTNESS_ERROR='+type(exc).__name__+':'+str(exc)[:140],file=sys.stderr)
        sys.exit(2)
