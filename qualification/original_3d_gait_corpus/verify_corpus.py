#!/usr/bin/env python3
"""Independent, fail-closed QA receipts for source-generated full-body 3D gait corpus."""
import hashlib, json, math, pathlib, struct, subprocess
import cv2
import numpy as np
import build_corpus as m


def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()


def verify(root, only_case=None):
 root=pathlib.Path(root)
 records=[]
 for variant in ((only_case,) if only_case else ('clean','knee_reverse','foot_slide')):
  glb=root/(variant+'.glb')
  raw=glb.read_bytes();magic,vers,total=struct.unpack_from('<III',raw)
  assert magic==0x46546c67 and vers==2 and total==len(raw)
  n,kind=struct.unpack_from('<II',raw,12)
  assert kind==0x4e4f534a
  meta=json.loads(raw[20:20+n]);anim=meta['animations'][0]
  assert len(meta['nodes'])>=18 and len(anim['channels'])>=54
  assert len(anim['samplers'])==len(anim['channels'])
  assert meta['asset']['version']=='2.0'
  labels=json.loads((root/(variant+'_ground_truth.json')).read_text())
  assert len(labels['frames'])==m.FRAMES and labels['gltf_sha256']==digest(glb)
  moving={};reversal={}
  for side in ('left','right'):
   velocities=[];signed=[]
   for i,p in enumerate(labels['frames']):
    joints=p['joints'];hip=np.array(joints[side+'_hip']);knee=np.array(joints[side+'_knee']);ankle=np.array(joints[side+'_ankle'])
    signed.append(float(np.cross(knee-hip,ankle-knee)[1]))
    assert abs(np.linalg.norm(hip-knee)-m.LEN1)<1e-8
    assert abs(np.linalg.norm(knee-ankle)-m.LEN2)<1e-8
    if i and labels['frames'][i-1]['contact'][side] and p['contact'][side]:
     prev=np.array(labels['frames'][i-1]['joints'][side+'_ankle'])
     velocities.append(float(np.linalg.norm(ankle-prev)*m.FPS))
   moving[side]=round(max(velocities),6)
   reversal[side]=sum(x<0 for x in signed)
  expectation={'clean':(False,False),'knee_reverse':(True,False),'foot_slide':(False,True)}[variant]
  assert (reversal['left']>0,moving['left']>.15)==expectation
  assert moving['right']<1e-7
  clips=[]
  for view in ('side','three_quarter'):
   file=root/(variant+'_'+view+'.mp4')
   info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,nb_frames,r_frame_rate:format=duration','-of','json',str(file)]))
   stream=info['streams'][0]
   assert stream['codec_name']=='h264' and stream['width']==m.SIZE and stream['height']==m.SIZE
   assert int(stream['nb_frames'])==m.FRAMES and stream['r_frame_rate']==f'{m.FPS}/1'
   cap=cv2.VideoCapture(str(file));ok,first=cap.read();assert ok
   last=first
   for i in range(m.FRAMES-1):
    ok,frame=cap.read();assert ok
    last=frame
   cap.release()
   movement=float(np.mean(np.abs(first.astype(float)-last.astype(float))))
   assert movement>1.0
   clips.append({'view':view,'file':file.name,'sha256':digest(file),'bytes':file.stat().st_size,
                 'fps':m.FPS,'decoded_frames':m.FRAMES,'first_last_mean_abs_pixel_difference':round(movement,3)})
  records.append({'case':variant,'model':glb.name,'model_sha256':digest(glb),'model_bytes':len(raw),
                  'rig_nodes':len(meta['nodes']),'animation_channels':len(anim['channels']),
                  'ground_truth':variant+'_ground_truth.json',
                  'ground_truth_sha256':digest(root/(variant+'_ground_truth.json')),
                  'peak_planted_ankle_speed_m_s':moving,'reversed_left_knee_frames':reversal['left'],
                  'video':clips})
 case_data={x['case']:x for x in records}
 if 'clean' in case_data: assert case_data['clean']['reversed_left_knee_frames']==0
 if 'knee_reverse' in case_data: assert case_data['knee_reverse']['reversed_left_knee_frames']==16
 if 'foot_slide' in case_data: assert abs(case_data['foot_slide']['peak_planted_ankle_speed_m_s']['left']-.283333)<.001
 manifest={'schema':'scp.original-full-body-gait-corpus.v1','result':'QUALIFIED_SOURCE_SYNTHETIC',
           'rights':'Original procedural 3D mesh and motion; CC0-1.0',
           'fps':m.FPS,'resolution':[m.SIZE,m.SIZE],'frames_per_video':m.FRAMES,
           'total_videos':len(records)*2,'total_animated_gltf_models':3,'cases':records,
           'limits':['Stylized mannequin, not realistic human anatomy',
             'Both views derive from same deterministic 3D coordinates',
             'Knee reversal and contact skate are source-defined controlled defects',
             'Not real-person imagery, model inference, or biologically valid gait']}
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'result':manifest['result'],'models':len(records),'videos':2*len(records),
                   'cases':{r['case']:{'sliding':r['peak_planted_ankle_speed_m_s']['left'],
                            'reversed_knee_frames':r['reversed_left_knee_frames']} for r in records}},indent=2))
 return manifest

if __name__=='__main__':
 import sys
 verify(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)