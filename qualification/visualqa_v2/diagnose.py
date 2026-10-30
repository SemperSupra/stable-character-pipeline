"""Independent source-clean decoded-pixel temporal diagnostics, additive to frozen L1.
No human pose, visual naturalness, identity, or override of L1 acceptance.
"""
import argparse, hashlib, json, statistics, subprocess, sys
from pathlib import Path
MAX_FRAMES=600
MAX_PIXELS=1920*1080
def run(*args):
    return subprocess.run(list(args), check=True, capture_output=True, timeout=120).stdout
def analyze(video, l1, output):
    video, l1, output=Path(video),Path(l1),Path(output)
    if video.is_symlink() or not video.is_file() or video.stat().st_size>100*1024*1024:
        raise ValueError('VIDEO_NOT_ADMITTED')
    src=hashlib.sha256(video.read_bytes()).hexdigest()
    parent=json.loads(l1.read_text())
    if parent.get('schema')!='scp.visualqa.l1_video.v1' or parent.get('source_sha256')!=src or parent.get('status') not in ('FAIL','PASS_L1_VIDEO_ONLY'):
        raise ValueError('L1_PROVENANCE_NOT_VERIFIED')
    meta=json.loads(run('ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,nb_read_frames,codec_name','-of','json',str(video)))
    if len(meta['streams'])!=1:raise ValueError('UNSUPPORTED_STREAMS')
    info=meta['streams'][0];w=int(info['width']);h=int(info['height']);n=int(info['nb_read_frames'])
    if info['codec_name']!='h264' or not 16<=w<=1920 or not 16<=h<=1080 or w*h>MAX_PIXELS or not 2<=n<=MAX_FRAMES:raise ValueError('VIDEO_SHAPE_NOT_ADMITTED')
    raw=run('ffmpeg','-nostdin','-loglevel','error','-i',str(video),'-map','0:v:0','-an','-pix_fmt','gray','-f','rawvideo','pipe:1')
    plane=w*h
    if len(raw)!=n*plane:raise ValueError('DECODED_FRAME_COUNT_MISMATCH')
    seq=[]
    for i in range(1,n):
        a=raw[(i-1)*plane:i*plane];b=raw[i*plane:(i+1)*plane]
        total=0;changed=0
        for x,y in zip(a,b):
            d=abs(x-y);total+=d;changed+=d>4
        seq.append({'start_frame':i-1,'end_frame':i,'mean_absolute_luma_change':round(total/plane,8),'fraction_pixels_changed_gt4':round(changed/plane,8)})
    vals=[x['mean_absolute_luma_change'] for x in seq]
    outcome={
      'schema':'scp.visualqa.v2_luma_diagnostics.v1',
      'status':'OBSERVATION_ONLY_PARENT_L1_'+parent['status'],
      'video_sha256':src,'source_l1_status':parent['status'],'source_l1_failures':parent.get('failures',[]),
      'decoded_frames':n,'width':w,'height':h,'pairs':len(seq),'mean_luma_change_min':min(vals),'median':statistics.median(vals),'max':max(vals),
      'pixel_motion_diagnostics':seq,
      'not_tested':['HUMAN_SKELETAL_ORIENTATION','COMPLETE_PERSON_DETECTION','OPTICAL_FLOW_GEOMETRIC_TRACKING','PHYSICAL_CONTACT','VISUAL_NATURALNESS'],
      'can_override_parent_l1':False
    }
    output.write_text(json.dumps(outcome,sort_keys=True,indent=2)+'\n')
    print('VISUALQA_V2_LUMA_DIAGNOSTIC_ONLY',parent['status'],n,'median',outcome['median'])
    return outcome
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--video',required=True);a.add_argument('--l1',required=True);a.add_argument('--out',required=True)
    x=a.parse_args()
    try:analyze(x.video,x.l1,x.out)
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as e:
        print('VISUALQA_V2_FIRST_FAILURE',e,file=sys.stderr);sys.exit(2)
