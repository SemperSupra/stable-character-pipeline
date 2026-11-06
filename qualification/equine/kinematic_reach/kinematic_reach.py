#!/usr/bin/env python3
"""Source-exact upper-bound IK reachability falsifier for synthetic equine walk.

Validates only the triangle-inequality maximum-reach condition for three linked
bones. A reachable target is NOT proof that IK constraints, contacts, pose or
anatomy can realize it. Source-original synthetic figures only.
"""
import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

PARENT_SHA = 'b83187e7237186ded84989064de146be85a3cdc0'
FRAME_COUNT = 48
HORSE_FOOT_NAMES = ('front_L','front_R','hind_L','hind_R')


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_source(name, path):
    spec = importlib.util.spec_from_file_location('scp_kinematic_'+name, str(path))
    if spec is None or spec.loader is None:
        raise ValueError('source module is unavailable')
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def reachability(specs, targets, *, carpus_shift=0.0):
    if not (math.isfinite(carpus_shift) and 0 <= carpus_shift <= .06):
        raise ValueError('bounded, nonnegative carpus hypothesis required')
    result={}
    for foot in HORSE_FOOT_NAMES:
        chain=specs[foot]
        if len(chain)!=3:
            raise ValueError('exact three joint links required')
        # Each segment is a (head_xyz, tail_xyz). The first joint is the hip/shoulder.
        links=[(tuple(h),tuple(t)) for h,t in chain]
        if foot.startswith('front') and carpus_shift:
            # Bounded, reversible HYPOTHESIS only: move common carpus joint
            # posterior by delta X; source bones and meshes remain untouched.
            joint=(links[0][1][0],links[1][1][1],links[1][1][2])
            joint=(links[1][1][0]-carpus_shift,links[1][1][1],links[1][1][2])
            links[1]=(links[1][0],joint)
            links[2]=(joint,links[2][1])
        for idx,(h,t) in enumerate(links):
            if not all(math.isfinite(v) for v in h+t) or math.dist(h,t)<.04:
                raise ValueError('invalid rest bone')
            if idx and math.dist(links[idx-1][1],h)>1e-6:
                raise ValueError('broken link continuity')
        lengths=[math.dist(h,t) for h,t in links]
        max_len=sum(lengths)
        min_len=max(0,2*max(lengths)-max_len)
        observations=targets[foot]
        if len(observations)!=FRAME_COUNT:
            raise ValueError('incomplete exact 48-frame target plan')
        failures=[]
        worst=0.0
        lowest_margin=1e9
        for frame, root_x, xyz in observations:
            if frame<1 or frame>FRAME_COUNT or not all(math.isfinite(v) for v in (root_x,*xyz)):
                raise ValueError('invalid target sample')
            hip=links[0][0]
            # Armature carries actual world root translation, target is world-space.
            distance=math.dist((hip[0]+root_x,hip[1],hip[2]),xyz)
            margin=min(max_len-distance,distance-min_len)
            lowest_margin=min(lowest_margin,margin)
            if margin < -1e-7:
                failures.append({'frame':frame,'over_extension_m':round(max(0,distance-max_len),7),
                                 'under_extension_m':round(max(0,min_len-distance),7)})
                worst=max(worst,-margin)
        if len({x[0] for x in observations})!=FRAME_COUNT:
            raise ValueError('duplicate or missing source frames')
        result[foot]={'links_m':[round(v,7) for v in lengths],
                      'max_reach_m':round(max_len,7), 'min_reach_m':round(min_len,7),
                      'min_margin_m':round(lowest_margin,7),
                      'infeasible_frame_count':len(failures),
                      'worst_excess_m':round(worst,7),
                      'infeasible_frames':failures}
    return result


def load_source_plan(source_dir):
    source_dir=Path(source_dir).resolve()
    anatomy_path=source_dir/'equine_anatomy.py'
    footpaths_path=source_dir/'footpaths.py'
    if not anatomy_path.is_file() or not footpaths_path.is_file():
        raise ValueError('missing exact source modules')
    anatomy=load_source('anatomy',anatomy_path)
    footpaths=load_source('footpaths',footpaths_path)
    if footpaths.CYCLE_FRAMES!=FRAME_COUNT or footpaths.STRIDE_M!=.16 or footpaths.ANKLE_BASE_Z_M!=.252:
        raise ValueError('source motion contract changed; recalibrate instead of silent pass')
    specs={}
    targets={}
    for foot in HORSE_FOOT_NAMES:
        prefix,side=foot.split('_')
        x=.4 if prefix=='front' else -.48
        y=-.2 if side=='L' else .2
        height=.81 if prefix=='front' else .78
        bones=anatomy.chain(prefix,side,x,y,height)
        if len(bones)!=5 or [q[0] for q in bones[:3]] != [f'{foot}_upper', f'{foot}_forearm' if prefix=='front' else f'{foot}_stifle', f'{foot}_lower']:
            raise ValueError('source anatomy has changed; fail closed')
        specs[foot]=[(q[2],q[3]) for q in bones[:3]]
        samples=[]
        for frame in range(1,FRAME_COUNT+1):
            t=footpaths.target(frame,foot)
            if t.frame!=frame or t.foot!=foot:
                raise ValueError('mismatched original target')
            samples.append((frame,t.root_x,(t.ankle_x,t.ankle_y,t.ankle_z)))
        targets[foot]=samples
    return specs,targets,{'equine_anatomy.py':sha256(anatomy_path),'footpaths.py':sha256(footpaths_path)}


def run(source_dir):
    specs, targets, source_shas=load_source_plan(source_dir)
    baseline=reachability(specs,targets)
    candidates=[]
    for delta_mm in range(0,61,5):
        delta=delta_mm/1000
        trial=reachability(specs,targets,carpus_shift=delta)
        candidates.append({'candidate_posterior_carpus_shift_mm':delta_mm,
            'front_infeasible_total':sum(trial[f]['infeasible_frame_count'] for f in ('front_L','front_R')),
            'front_min_margin_m':round(min(trial[f]['min_margin_m'] for f in ('front_L','front_R')),7),
            'candidate_only_not_implemented':True})
    report={'schema':'equine.ik.reachability-hypothesis.v1',
            'authority_parent_source_sha':PARENT_SHA,'source_file_shas':source_shas,
            'scope':'PUBLIC_ORIGINAL_SYNTHETIC_30J_48F',
            'method':'TRIANGLE_INEQUALITY_UPPER_BOUND_NOT_CONSTRAINED_IK',
            'biomechanical_acceptance':False,'animal_joint_limits':'UNVALIDATED_ENGINEERING',
            'baseline':baseline,'candidate_sweep':candidates,
            'source_mutation':False}
    return report


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-dir',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args()
    report=run(args.source_dir)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('INDEPENDENT_KINEMATIC_REACHABILITY',
          {f:report['baseline'][f]['infeasible_frame_count'] for f in HORSE_FOOT_NAMES},
          'candidate_only; physics acceptance UNKNOWN')

if __name__=='__main__':main()
