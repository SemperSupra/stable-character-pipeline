#!/usr/bin/env python3
"""Cross-modal synthetic case adjudication with pinned *independent* judge sources.
No shared metric can override an observed FAIL of another modality.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

GEOMETRY_COMMIT = 'bcccffbc016b980974fb46397e6eaa6e6f6d0b45'
TEMPORAL_COMMIT = '8ed8ad31e4438fd2e537dc8903a4b85291e1ab68'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for part in iter(lambda: f.read(1024*1024),b''):
            h.update(part)
    return h.hexdigest()


def load(path, name):
    spec=importlib.util.spec_from_file_location(name,str(path))
    if spec is None or spec.loader is None: raise ValueError('UNCERTAIN_JUDGE_IMPORT')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def aggregate(verdicts):
    if not verdicts or any(v not in ('PASS','FAIL','UNKNOWN') for v in verdicts):
        raise ValueError('INCOMPLETE_OR_INVALID_JUDGE')
    if 'FAIL' in verdicts: return 'FAIL'
    if 'UNKNOWN' in verdicts: return 'UNKNOWN'
    return 'PASS'


def valid_pose():
    length=math.hypot(.1,.45)
    return {'schema':'scp.gait-geometry.v1',
            'approved_bend_pole':[0,1,0],
            'segment_lengths_m':[.5,length],
            'frames':[{'time_s':i/12,'hip':[0,0,1],
                       'knee':[0,0,.5],'ankle':[.1,0,.05]} for i in range(8)]}


def case_map():
    return [
        {'id':'clean','video':'stable','reverse_knee':False,
         'want':{'temporal':'PASS','geometry':'PASS','overall':'PASS'}},
        {'id':'knee_reversal','video':'stable','reverse_knee':True,
         'want':{'temporal':'PASS','geometry':'FAIL','overall':'FAIL'}},
        {'id':'luma_flicker','video':'flicker','reverse_knee':False,
         'want':{'temporal':'FAIL','geometry':'PASS','overall':'FAIL'}},
        {'id':'scene_cut_abstain','video':'cut','reverse_knee':False,
         'want':{'temporal':'UNKNOWN','geometry':'PASS','overall':'UNKNOWN'}},
        {'id':'black_video','video':'black','reverse_knee':False,
         'want':{'temporal':'FAIL','geometry':'PASS','overall':'FAIL'}},
        {'id':'both_defects','video':'flicker','reverse_knee':True,
         'want':{'temporal':'FAIL','geometry':'FAIL','overall':'FAIL'}},
    ]


def execute(temporal_root, geometry_root, out_dir):
    temporal_root=Path(temporal_root).resolve()
    geometry_root=Path(geometry_root).resolve()
    out_dir=Path(out_dir).resolve();out_dir.mkdir(parents=True,exist_ok=True)
    video_dir=out_dir/'clips'
    geom_path=geometry_root/'qualification/video_physics_bakeoff/kinematic_geometry/kinematic_oracle.py'
    temporal_path=temporal_root/'qualification/video_physics_bakeoff/temporal_pixels/temporal_pixels.py'
    generate=temporal_root/'qualification/video_physics_bakeoff/temporal_pixels/make_cases.py'
    for p in (geom_path,temporal_path,generate):
        if not p.is_file() or p.is_symlink():
            raise ValueError('PINNED_JUDGE_FILE_UNAVAILABLE')
    geom=load(geom_path,'independent_skeleton_judge')
    temporal=load(temporal_path,'independent_video_pixel_judge')
    subprocess.run([sys.executable,str(generate),str(video_dir)],
                   check=True,timeout=90)
    records=[]
    for c in case_map():
        pose=valid_pose()
        if c['reverse_knee']:
            pose['frames'][3]['ankle'][0]=-.1
        video=video_dir/(c['video']+'.mp4')
        observed_pose=geom.analyze(pose)
        observed_video=temporal.analyze(video)
        seen={'temporal':observed_video['verdict'],
              'geometry':observed_pose['status']}
        seen['overall']=aggregate(list(seen.values()))
        input_bytes=json.dumps(pose,sort_keys=True,separators=(',',':')).encode('utf-8')
        records.append({'case':c['id'],'expected':c['want'],'observed':seen,
                        'matches':seen==c['want'],
                        'input_pose_sha256':hashlib.sha256(input_bytes).hexdigest(),
                        'video_sha256':sha(video),
                        'geometry_findings':[x['code'] for x in observed_pose['findings']],
                        'video_findings':observed_video['findings'],
                        'uncertainties':observed_video['uncertainties']})
    passed=sum(r['matches'] for r in records)
    receipt={'schema':'scp.modal-matrix.v1','research_scope':'public-original-synthetic',
             'source_commits':{'geometry':GEOMETRY_COMMIT,'temporal':TEMPORAL_COMMIT},
             'judge_file_sha256':{'geometry':sha(geom_path),'temporal':sha(temporal_path),
                                  'video_generator':sha(generate)},
             'expected_cases':len(records),'matched_cases':passed,
             'observations':records,
             'generalization_limits':['Independent fabricated pose and pixel observations are not a synchronized rendered humanoid',
               'No 3D/pixel registration, verified contact label, human appearance or pose extraction',
               'Multi-judge disagreement is recorded, not reconciled by score averaging',
               'PASS means only this synthetic test matched a fixed expected verdict']}
    (out_dir/'modal-matrix.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    if passed!=len(records):raise ValueError('CROSS_MODAL_ORACLE_MISMATCH')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--temporal-root',required=True)
    p.add_argument('--geometry-root',required=True)
    p.add_argument('--out-dir',required=True)
    a=p.parse_args()
    try:
        receipt=execute(a.temporal_root,a.geometry_root,a.out_dir)
        print(f"MODAL_MATRIX_MATCHED={receipt['matched_cases']}/{receipt['expected_cases']}")
    except Exception as exc:
        print('MODAL_MATRIX_INVALID='+type(exc).__name__+':'+str(exc)[:160],file=sys.stderr)
        sys.exit(2)
