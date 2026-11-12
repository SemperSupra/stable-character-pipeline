#!/usr/bin/env python3
"""Source-independent motion audit and mathematically grounded parameter primitives.

This module is intended to FAIL/ABSTAIN on scientific deficiencies in the original
synthetic corpus, not to claim that a mathematically named motion is biomechanically valid.
No third-party packages are required.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any

G = 9.80665
EPS = 1e-10


def finite_nonbool(x: Any) -> bool:
    return type(x) in (float, int) and math.isfinite(x)


def bounded_scalar(x: Any, lo: float, hi: float) -> float:
    if not finite_nonbool(x) or not lo <= x <= hi:
        raise ValueError("INVALID_DIMENSIONED_PARAMETER")
    return float(x)


def froude(speed_m_s: float, leg_length_m: float, gravity: float = G) -> float:
    v=bounded_scalar(speed_m_s,0,100)
    L=bounded_scalar(leg_length_m,EPS,5)
    g=bounded_scalar(gravity,EPS,100)
    return v*v/(g*L)


def stride_frequency(speed_m_s: float, stride_m: float) -> float:
    # Same-side stride frequency (Hz), not step cadence in steps/min.
    v=bounded_scalar(speed_m_s,0,100)
    s=bounded_scalar(stride_m,EPS,10)
    return v/s


def minimum_jerk(tau: float) -> float:
    t=bounded_scalar(tau,0,1)
    return 10*t**3-15*t**4+6*t**5


def swing_arc(start, end, tau: float, height: float):
    """Planar swing on a quintic time law with a vertical sinusoid.

    This is a C2 position interpolant for horizontal displacement; vertical lift
    needs separate landing boundary verification and is not a force model.
    """
    if len(start)!=3 or len(end)!=3:
        raise ValueError('BAD_SWING_ENDPOINT')
    if any(not finite_nonbool(k) for k in (*start,*end)):
        raise ValueError('BAD_SWING_ENDPOINT')
    h=bounded_scalar(height,0,3)
    u=minimum_jerk(tau)
    return [start[i]+(end[i]-start[i])*u+(h*math.sin(math.pi*tau) if i==2 else 0.0)
            for i in range(3)]


def two_link_knee(hip, ankle, thigh: float, shin: float, bend: int=1):
    """Law-of-cosines planar leg IK; reject unreachable endpoints (no silent clamp)."""
    L1=bounded_scalar(thigh,EPS,5)
    L2=bounded_scalar(shin,EPS,5)
    if bend not in (-1,1) or type(bend) is not int:
        raise ValueError('BEND_POLE_INVALID')
    if len(hip)!=3 or len(ankle)!=3:
        raise ValueError('BAD_JOINT_SHAPE')
    if any(not finite_nonbool(k) for k in (*hip,*ankle)):
        raise ValueError('BAD_JOINT_NUMBER')
    dx=ankle[0]-hip[0];dz=ankle[2]-hip[2]
    d=math.hypot(dx,dz)
    if d >= L1+L2-EPS or d <= abs(L1-L2)+EPS:
        raise ValueError('LEG_IK_UNREACHABLE')
    along=(L1*L1-L2*L2+d*d)/(2*d)
    orth=math.sqrt(max(0.,L1*L1-along*along))
    return [hip[0]+along*dx/d-bend*orth*dz/d,hip[1],hip[2]+along*dz/d+bend*orth*dx/d]


def contact_speed(prev, now, dt:float):
    if len(prev)!=3 or len(now)!=3 or any(not finite_nonbool(v) for v in (*prev,*now)):
        raise ValueError('BAD_WORLD_ANKLE')
    duration=bounded_scalar(dt,EPS,1e3)
    return math.sqrt(sum((now[i]-prev[i])**2 for i in range(3)))/duration


def coordination_index(propulsive_fraction:float):
    # Simplified equal-arm cyclic front-crawl IdC = t_p / T - 1/2.
    p=bounded_scalar(propulsive_fraction,0,1)
    return p-.5


def audit_case(label_path: Path, limb_lengths: dict[str,tuple[float,float]],
               max_limb_error_m: float=.01, max_stance_speed_m_s:float=.025):
    label_path=Path(label_path)
    raw=label_path.read_bytes()
    if len(raw)>5_000_000: raise ValueError('LABEL_TOO_LARGE')
    doc=json.loads(raw)
    frames=doc.get('frames')
    if not isinstance(frames,list) or len(frames)<3:raise ValueError('BAD_FRAMES')
    fps=doc.get('fps')
    if not isinstance(fps,int) or fps<=0:raise ValueError('BAD_FPS')
    body=doc.get('spec',{}).get('sex','unknown')
    if body not in limb_lengths:raise ValueError('UNKNOWN_BODY_MORPHOLOGY')
    thigh,shin=limb_lengths[body]
    issues=[];limb_max=0.;contact_max=0.;contacts=0;total=0
    leg_lengths=[];stance_speeds=[]
    for i,fr in enumerate(frames):
        j=fr['joints'];ground=fr['contact']
        for side in ('left','right'):
            a=j[side+'_hip'];b=j[side+'_knee'];c=j[side+'_ankle']
            if any(len(z)!=3 or any(not finite_nonbool(x) for x in z) for z in (a,b,c)):
                raise ValueError('NONFINITE_JOINT')
            m1=math.dist(a,b);m2=math.dist(b,c)
            err=max(abs(m1-thigh),abs(m2-shin))
            limb_max=max(limb_max,err)
            if err>max_limb_error_m:
                issues.append({'frame':i,'joint':side+'_leg','code':'LIMB_LENGTH_INVARIANT_VIOLATION','magnitude_m':round(err,5)})
            leg_lengths.append(err)
            if type(ground.get(side)) is not bool:raise ValueError('INVALID_CONTACT_LABEL')
            if i and ground[side] and frames[i-1]['contact'][side]:
                contacts+=1
                v=contact_speed(frames[i-1]['joints'][side+'_ankle'],c,1/fps)
                contact_max=max(contact_max,v)
                stance_speeds.append(v)
                if v>max_stance_speed_m_s:
                    issues.append({'frame':i,'joint':side+'_ankle','code':'LABELED_STANCE_FOOT_SLIDE','speed_m_s':round(v,5)})
            total+=1
    # This is strictly targeted geometry/contact validity, not performance or realism.
    status='FAIL' if issues else ('UNKNOWN' if contacts<3 else 'PASS')
    return {
      'schema':'scp.motion-math-case-audit.v1','case':doc.get('case'),
      'motion':doc.get('spec',{}).get('motion'),'morphology_preset':body,
      'footwear':doc.get('spec',{}).get('footwear'),
      'source_sha256':hashlib.sha256(raw).hexdigest(),'frames_checked':len(frames),
      'joint_observations':total,'labeled_contiguous_stance_intervals':contacts,
      'max_limb_length_error_m':round(limb_max,5),
      'peak_labeled_stance_speed_m_s':round(contact_max,5),
      'defect_count':len(issues),'status':status,
      'findings':issues,
      'limitations':['Source-only kinematic/contact checks, no biomechanical or video derived proof',
                     'Sex is a nominal preset label, not a deterministic physical law',
                     'Footwear still needs contact patch, torque and collision dynamics']}


def audit_corpus(root: Path):
    root=Path(root)
    cases=[]
    limb_lengths={'male':(.54,.53),'female':(.52,.51)}
    for batch in ('locomotion','exercise_pose','dance_combat','aquatic'):
        manifest=json.loads((root/batch/'manifest.json').read_text())
        for item in manifest['cases']:
            entry=audit_case(root/batch/(item['case']+'_ground_truth.json'),limb_lengths)
            entry['batch']=batch
            cases.append(entry)
    out={'schema':'scp.motion-math-corpus-audit.v1','case_count':len(cases),
         'counts':{k:sum(c['status']==k for c in cases) for k in ('PASS','FAIL','UNKNOWN')},
         'cases':cases,'verdict':'RESEARCH_GATES_ONLY',
         'limits':['PASS is not a learned-model or realism claim',
                   'All original videos should remain separately viewable in Drive']}
    return out


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--root',required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    report=audit_corpus(Path(a.root))
    Path(a.out).write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print('MOTION_MATH_CASES',report['case_count'],'COUNTS',report['counts'])
