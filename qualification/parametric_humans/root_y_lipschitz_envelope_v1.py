#!/usr/bin/env python3
"""Source-bound mathematical *diagnostic* root-Y Lipschitz envelope.

A bounded pointwise majorant of the measured sole floor-clearance requirements
is the smallest schedule satisfying per-frame Y lower bounds and a user-chosen
Lipschitz slope. This is NOT gait, IK, phase contact, or force simulation.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path

SOURCE_SHA256='b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748'
ACTORS=('AsterOriginal','JuniperOriginal')
SCHEMA='scp.r009.root_y_lipschitz_envelope.v1'
SLOPE_M_PER_FRAME=.002
MARGIN_M=.0002
MAX_STEP_M=.003
MAX_ACCEL_M=.005

class EnvelopeError(ValueError):pass

def require(ok,msg):
    if not ok:raise EnvelopeError(msg)

def numbers(v):return type(v) is list and len(v)==72 and all(type(x) in (int,float) and math.isfinite(x) and 0<=x<=.025 for x in v)

def envelope(required, slope=SLOPE_M_PER_FRAME, margin=MARGIN_M):
    require(numbers(required),'REQUIRED_72_FINITE_BOUNDS')
    require(type(slope) in (float,int) and math.isfinite(slope) and 0<=slope<=.0024,'SLOPE_POLICY')
    require(type(margin) in (float,int) and math.isfinite(margin) and .0001<=margin<=.001,'MARGIN_POLICY')
    heights=[max(float(required[j])-slope*min(abs(i-j),72-abs(i-j)) for j in range(72))+margin for i in range(72)]
    # Numerical proof of the upper/lower envelope, and continuity budgets.
    assert all(y>=x+margin-1e-12 for x,y in zip(required,heights))
    assert max(abs(heights[i]-heights[(i-1)%72]) for i in range(72))<=slope+1e-12
    assert max(abs(heights[(i+1)%72]-2*heights[i]+heights[(i-1)%72]) for i in range(72))<=2*slope+1e-12
    return heights

def build(sole,mode='minimal_envelope'):
    require(type(sole) is dict and sole.get('source_sha256')==SOURCE_SHA256,'SOURCE_PIN')
    require(sole.get('schema')=='scp.r009.shoe_sole_correspondence_cpu72.v1','SOLE_SCHEMA')
    require(sole.get('frames')==72 and sole.get('coordinate_up')=='Y','FRAMES_AXIS')
    for flag in ('root_shift_applied','native_blender_evaluated','gait_accepted','release_approved'):
        require(sole.get(flag) is False,'FALSE_SOURCE_APPROVAL:'+flag)
    require(type(sole.get('actors')) is dict and set(sole['actors'])==set(ACTORS),'ACTORS')
    require(mode in ('minimal_envelope','constant_upper_bound'),'MODE')
    actors={}
    for a in ACTORS:
        required=sole['actors'][a].get('required_root_y_clearance_m')
        require(numbers(required),'REQUIRED_72')
        proposal=envelope(required) if mode=='minimal_envelope' else [max(required)+MARGIN_M]*72
        step=max(abs(proposal[i]-proposal[(i-1)%72]) for i in range(72))
        accel=max(abs(proposal[(i+1)%72]-2*proposal[i]+proposal[(i-1)%72]) for i in range(72))
        require(step<=MAX_STEP_M+1e-12 and accel<=MAX_ACCEL_M+1e-12,'CONTINUITY_INCONSISTENCY')
        require(all(h>=lo+MARGIN_M-1e-12 for h,lo in zip(proposal,required)),'FLOOR_BOUNDS')
        actors[a]={'proposed_lift_m':proposal,'max_root_y_step_m':step,
            'max_root_y_second_diff_m':accel,'min_floor_margin_m':min(h-x for h,x in zip(proposal,required)),
            'mean_extra_lift_vs_measured_m':sum(h-x for h,x in zip(proposal,required))/72,
            'peak_root_y_lift_m':max(proposal)}
    return {'schema':SCHEMA,'mode':mode,'source_sha256':SOURCE_SHA256,'frames':72,'coordinate_up':'Y',
        'actors':actors,'slope_policy_m_per_frame':SLOPE_M_PER_FRAME,'floor_margin_m':MARGIN_M,
        'root_height_proxy_continuity_pass':True,'root_ik_applied':False,
        'physical_contact_accepted':False,'native_blender_evaluated':False,
        'natural_gait_accepted':False,'release_approved':False,
        'verdict':'PASS_MATHEMATICAL_HEIGHT_ENVELOPE_ONLY'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sole',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mode',choices=('minimal_envelope','constant_upper_bound'),default='minimal_envelope')
    a=ap.parse_args()
    if a.out.exists() or a.out.resolve()==a.sole.resolve():raise EnvelopeError('NO_OVERWRITE')
    r=build(json.loads(a.sole.read_text()),a.mode)
    a.out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'verdict':r['verdict'],'actors':{name:{k:v for k,v in values.items() if k!='proposed_lift_m'} for name,values in r['actors'].items()}},sort_keys=True))
if __name__=='__main__':main()
