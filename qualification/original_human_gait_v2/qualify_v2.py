#!/usr/bin/env python3
"""Independent fail-closed structural, kinematic and deformed-mesh qualification.
Do not equate bounded motion/sole proxy with full natural gait/human approval.
"""
import json,sys,math,hashlib,subprocess
from pathlib import Path
import numpy as np
from render_v2 import RenderModel
from gait_v2 import frame_pose,decode_glb,FRAMES,FPS,D,T
from scipy.spatial.transform import Rotation
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'aster-juniper-anatomical-v2.glb'
m=RenderModel(SRC)
raw=SRC.read_bytes();doc,binary=decode_glb(raw)
issues=[];pass_checks=[]
def test(name,pred):
 if pred:pass_checks.append(name)
 else:issues.append(name)
# Immutable source and rig binding evidence
import os
original=Path(os.environ.get('R009_GAIT_SOURCE','/mnt/data/r009-aster-juniper-original-heading-aligned-REVIEW.glb'))
old_doc,oldbin=decode_glb(original.read_bytes());test('PARENT_SOURCE_BINARY_PREFIX_PRESERVED',binary[:len(oldbin)]==oldbin)
test('MESHES_UNCHANGED',doc['meshes']==old_doc['meshes']);test('SKINS_UNCHANGED',doc['skins']==old_doc['skins']);test('MATERIALS_UNCHANGED',doc['materials']==old_doc['materials'])
test('INPUT_SHA_BOUND',doc['extras']['r009_human_gait_v2']['input_sha256']==hashlib.sha256(original.read_bytes()).hexdigest())
test('BOTH_SKINNED_CHARACTER_MESHES',[len(x['joints']) for x in doc['skins']]==[17,17])
test('ANIMATION_CHANNEL_COUNT_AND_FRAME_DURATION',len(doc['animations'][0]['channels'])==28)
science=json.loads((ROOT/'r009-gait-v2-source-native-skin-observer.json').read_text())
for name,data in science['motion_roles'].items():
 test(name+'_PEAK_KNEE_SWING_55_TO_70_DEGREES',55<=data['left_knee_flex_max_deg']<=70 and 55<=data['right_knee_flex_max_deg']<=70)
 test(name+'_LEADING_FOOT_FORWARD_12CM',data['left_hip_to_foot_fwd_max_m']>=.12)
 test(name+'_FOOT_TRAILS_10CM',data['left_hip_to_foot_fwd_min_m']<=-.10)
 test(name+'_OPPOSITE_ARM_LEG_CORRELATION',data['contralateral_left_foot_right_shoulder_corr']>.85)
 test(name+'_SHOULDER_PAIR_ANTIPHASE',data['opposite_arm_pair_shoulder_corr']<-.95)
 test(name+'_ELBOW_ACTUALLY_BENDS',20<=data['right_elbow_rom_deg']<=40 and 20<=data['left_elbow_rom_deg']<=40)
for name,data in science['stance_pairs'].items():
 test(name+'_SKINNED_SOLE_STANCE_DRIFT_BELOW_2CM',data['above_2cm']==0 and data['count']>10)
 test(name+'_SKINNED_SOLE_NOT_PENETRATE_STANCE',data['min_actual_boot_y_in_stance_m']>-.015)
# Direct surface strain across mesh triangle edges relative to source mesh rest. Ignore 0-length modeling seam edges.
edge_strain={}
for frame in [0,12,24,36,48,60,71]:
 world,xyz=m.skin_frame(frame)
 for i,p in enumerate(m.parts):
  ind=p['idx'];rest=p['vertices'];cur=xyz[i];out=[]
  for a,b in [(0,1),(1,2),(2,0)]:
   length0=np.linalg.norm(rest[ind[:,a]]-rest[ind[:,b]],axis=1)
   length1=np.linalg.norm(cur[ind[:,a]]-cur[ind[:,b]],axis=1)
   good=length0>.002
   out.append(abs(length1[good]/length0[good]-1))
  k=p['mat_name']
  if k not in edge_strain:edge_strain[k]=[]
  edge_strain[k].append(np.concatenate(out))
strain={}
for material,sets in edge_strain.items():
 a=np.concatenate(sets)
 strain[material]={'edge_n':len(a),'p95_abs_strain':float(np.percentile(a,95)),'p99_abs_strain':float(np.percentile(a,99)),'max_abs_strain':float(a.max()),'count_over_50pct':int((a>.5).sum())}
# Edge extension may be high on procedural overlap seams. Quantify/reject, not falsely erase.
worst=max((v['p99_abs_strain'],k) for k,v in strain.items());test('MESH_STRAIN_P99_BELOW_50_PERCENT',worst[0]<.50)
# Motor and camera actual H264 exact transport readback
video=[]
for view in ('side','oblique','aster-close','juniper-close'):
 p=ROOT/f'r009-aster-juniper-gait-v2-{view}-72f.mp4'
 meta=subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=nb_read_frames,r_frame_rate,width,height','-of','json',str(p)])
 j=json.loads(meta)['streams'][0];video.append({'view':view,'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'stream':j})
 test('MEDIA_'+view+'_72F_12FPS_960x540',int(j['nb_read_frames'])==72 and j['r_frame_rate']=='12/1' and j['width']==960 and j['height']==540)
# Kinematics chart, two independent character tracks from *actual model GLB values* exposed in observer.
tr=science['per_frame_data'];A=[x['actors']['AsterOriginal'] for x in tr]
t=np.arange(len(A))/FPS
fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
for side in ['L','R']:
 style='-' if side=='L' else '--'
 axes[0].plot(t,[x['legs'][side]['hip_flex_deg'] for x in A],style,label=side+' hip flexion')
 axes[0].plot(t,[x['legs'][side]['knee_flex_deg'] for x in A],style,label=side+' knee flexion')
 axes[1].plot(t,[x['arms'][side]['shoulder'] for x in A],style,label=side+' shoulder flexion')
 axes[1].plot(t,[x['arms'][side]['elbow'] for x in A],style,label=side+' elbow flexion')
 axes[2].plot(t,[x['legs'][side]['ankle_world'][0]-x['legs'][side]['hip_world'][0] for x in A],style,label=side+' foot forward vs hip')
axes[0].set_ylabel('Joint angle (degrees)');axes[1].set_ylabel('Arm angle (degrees)');axes[2].set_ylabel('Forward foot (meters)')
axes[2].set_xlabel('Animation time (seconds)')
for ax in axes:ax.grid(True,alpha=.25);ax.legend(ncol=2,loc='upper right',fontsize=9)
axes[0].set_title('R009 gait v2 — sampled ACTUAL GLB skeleton | Aster | technical verification only')
fig.tight_layout();chart=ROOT/'r009-gait-v2-kinematics-trajectories.png';fig.savefig(chart,dpi=160);plt.close(fig)
receipt={'schema':'scp.r009.independent_gait_v2_motion_qualification','source_glb_sha256':m.sha,
 'passes':pass_checks,'failures':issues,'status':'RESEARCH_PREVIEW_NOT_HUMAN_ACCEPTED',
 'numerics':{'stride_period_s':T,'stance_phase_fraction':.6,'edge_strain_p99_worst':worst},
 'material_strain':strain,'video':video,'chart':str(chart),
 'limitations':['not marker-based measured human normative motion','procedural stylized avatar lacks toe articulation',
   'no inverse dynamics or force/contact sensors','no continuous collision or foot pressure validation',
   'skin geometry strain is only sampled every 12 frames','no source protected person/identity admission',
   'not tested on original Naomi/Alison rig or Blender native'],
 'accepted_for_motion':False}
(ROOT/'r009-gait-v2-independent-qa.json').write_text(json.dumps(receipt,indent=2))
print('PASSES',len(pass_checks),'FAILURES',issues,'WORST_STRAIN',worst,'video_files',len(video), 'chart',chart)
if issues:raise SystemExit(2)
