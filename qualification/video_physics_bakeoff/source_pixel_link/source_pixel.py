#!/usr/bin/env python3
"""Source-bound 3D-joint to independently decoded H.264 pixel corroboration.

Research fiducials only: not photorealistic anatomy or image-derived human pose.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

WIDTH,HEIGHT,FRAMES = 128,128,12
GEOMETRY_SHA = 'bcccffbc016b980974fb46397e6eaa6e6f6d0b45'
COLORS = {'hip':(20,80,255), 'knee':(255,20,20), 'ankle':(20,255,40)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source(reverse=False):
    length=math.hypot(.1,.45)
    frames=[]
    for t in range(FRAMES):
        drift=.005*t
        ankle_offset=-.1 if reverse and t>=6 else .1
        frames.append({'time_s':t/12,
                       'hip':[drift,0,1.0],
                       'knee':[drift,0,.5],
                       'ankle':[drift+ankle_offset,0,.05]})
    return {'schema':'scp.gait-geometry.v1',
            'approved_bend_pole':[0,1,0],
            'segment_lengths_m':[.5,length],
            'frames':frames}


def project(point):
    x,y,z=point
    if y!=0:raise ValueError('ONLY_CALIBRATED_PLANAR_SYNTHETIC_CAMERA')
    return round(64.+160.*x),round(118.-100.*z)


def blank():
    return bytearray(bytes((30,30,30))*(WIDTH*HEIGHT))


def write_px(img,x,y,rgb):
    if 0<=x<WIDTH and 0<=y<HEIGHT:
        at=(y*WIDTH+x)*3
        img[at:at+3]=bytes(rgb)


def line(img,a,b):
    x,y=a;xx,yy=b
    steps=max(abs(xx-x),abs(yy-y),1)
    for n in range(steps+1):
        t=n/steps
        write_px(img,round(x+(xx-x)*t),round(y+(yy-y)*t),(100,100,100))


def circle(img,xy,color):
    cx,cy=xy
    for dy in range(-4,5):
        for dx in range(-4,5):
            if dx*dx+dy*dy<=16:write_px(img,cx+dx,cy+dy,color)


def render_rgb(pose):
    result=bytearray()
    for frame in pose['frames']:
        img=blank()
        pts={name:project(frame[name]) for name in COLORS}
        line(img,pts['hip'],pts['knee'])
        line(img,pts['knee'],pts['ankle'])
        for name,color in COLORS.items():circle(img,pts[name],color)
        result.extend(img)
    return bytes(result)


def encoded_decoded(pose,root,kind):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    native=render_rgb(pose);video=root/(kind+'.mp4')
    enc=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-f','rawvideo',
         '-pix_fmt','rgb24','-video_size',f'{WIDTH}x{HEIGHT}',
         '-framerate','12','-i','pipe:0','-an','-c:v','libx264',
         '-crf','18','-pix_fmt','yuv420p',str(video)]
    subprocess.run(enc,input=native,check=True,capture_output=True,timeout=45)
    dec=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-i',str(video),
         '-map','0:v:0','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    observed=subprocess.run(dec,capture_output=True,check=True,timeout=45).stdout
    if len(observed)!=len(native):raise ValueError('INCOMPLETE_VIDEO_DECODE')
    return video,observed


def find_color(frame,name):
    picked=[]
    for y in range(HEIGHT):
        for x in range(WIDTH):
            at=(y*WIDTH+x)*3
            r,g,b=frame[at:at+3]
            if name=='hip':yes=(b>155 and b>r*1.7 and b>g*1.5)
            elif name=='knee':yes=(r>155 and r>g*1.7 and r>b*1.7)
            else:yes=(g>155 and g>r*1.7 and g>b*1.7)
            if yes:picked.append((x,y))
    if len(picked)<8:raise ValueError('DECODED_COLOR_KEYPOINT_MISSING')
    return (sum(x for x,_ in picked)/len(picked),
            sum(y for _,y in picked)/len(picked))


def corroborate(pose,decoded):
    size=WIDTH*HEIGHT*3
    if len(decoded)!=len(pose['frames'])*size:raise ValueError('DECODE_OR_POSE_FRAME_COUNT_DRIFT')
    errors=[];worst=0
    for t,frame in enumerate(pose['frames']):
        raw=decoded[t*size:(t+1)*size]
        for name in COLORS:
            expected=project(frame[name])
            actual=find_color(raw,name)
            error=round(math.hypot(actual[0]-expected[0],actual[1]-expected[1]),4)
            worst=max(worst,error)
            errors.append({'frame':t,'joint':name,
                           'expected_pixel':expected,'observed_pixel':[round(v,3) for v in actual],
                           'error_px':error})
    return {'verdict':'PASS' if worst<=2.5 else 'FAIL',
            'maximum_error_px':round(worst,4),'measured_points':len(errors),
            'records':errors}


def global_verdict(geom,px):
    if any(x not in ('PASS','FAIL','UNKNOWN') for x in (geom,px)):
        raise ValueError('UNTRUSTED_JUDGE')
    if 'FAIL' in (geom,px):return 'FAIL'
    if 'UNKNOWN' in (geom,px):return 'UNKNOWN'
    return 'PASS'


def execute(judge_root,output):
    judge=Path(judge_root)/'qualification/video_physics_bakeoff/kinematic_geometry/kinematic_oracle.py'
    if not judge.is_file() or judge.is_symlink():raise ValueError('PINNED_GEOMETRY_SOURCE_ABSENT')
    spec=importlib.util.spec_from_file_location('geometry_independent_native',str(judge))
    if spec is None or spec.loader is None:raise ValueError('INVALID_GEOMETRY_SOURCE')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows=[]
    work=Path(output).parent/'video-evidence'
    for name,reverse in (('clean',False),('reversed_knee',True)):
        pose=source(reverse)
        geometry=module.analyze(pose)
        clip,pixels=encoded_decoded(pose,work,name)
        alignment=corroborate(pose,pixels)
        expected='FAIL' if reverse else 'PASS'
        combined=global_verdict(geometry['status'],alignment['verdict'])
        rows.append({'case':name,'expected':expected,'verdict':combined,
                     'matches_expected':expected==combined,
                     'geometry_verdict':geometry['status'],
                     'geometry_findings':[x['code'] for x in geometry['findings']],
                     'pixel_corroboration':alignment,
                     'source_sha256':sha(json.dumps(pose,sort_keys=True,
                         separators=(',',':')).encode()),
                     'video_sha256':sha(clip.read_bytes()),
                     'decoded_rgb_sha256':sha(pixels)})
        if alignment['verdict']!='PASS':raise ValueError('SYNCHRONIZED_RENDER_COORDINATES_DISAGREE')
    # A valid frame stream with wrong source is a falsifier, not an inference success.
    clean_pose=source(False)
    rev_clip,pixels=encoded_decoded(source(True),work,'reversed_crosscheck')
    stale=corroborate(clean_pose,pixels)
    if stale['verdict']!='FAIL':raise ValueError('STALE_SOURCE_VIDEO_NOT_DETECTED')
    receipt={'schema':'scp.source-pixel-synchronization.v1',
             'geometry_source_git_sha':GEOMETRY_SHA,
             'geometry_source_sha256':sha(judge.read_bytes()),
             'script_sha256':sha(Path(__file__).read_bytes()),
             'projection':'fixed orthographic x/z with RGB joint fiducials',
             'status':'SYNTHETIC_ORACLE_PASS' if all(x['matches_expected'] for x in rows)
                         else 'REJECT',
             'cases':rows,
             'negative_stale_source_crosscheck':{'verdict':stale['verdict'],
                         'max_error_px':stale['maximum_error_px'],
                         'video_sha256':sha(rev_clip.read_bytes())},
             'limits':['Original schematic colored joint markers only, not human-derived pose',
                       'Rendering and detection are independent functions but share this synthetic calibration',
                       'No real biological anatomy, body shape, optical ambiguity, shadows or occlusion',
                       'Synthetic alignment does not satisfy natural gait or actor/identity release gates']}
    Path(output).write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    if receipt['status']!='SYNTHETIC_ORACLE_PASS':raise ValueError('SCENE_COUPLING_CASE_MISMATCH')
    print('SOURCE_PIXEL_COUPLING='+receipt['status'])
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--geometry-root',required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    try:execute(a.geometry_root,a.out)
    except Exception as e:
        print('SOURCE_PIXEL_INVALID='+type(e).__name__+':'+str(e)[:140],file=sys.stderr)
        sys.exit(2)
