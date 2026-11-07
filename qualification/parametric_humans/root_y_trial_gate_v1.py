#!/usr/bin/env python3
"""Independent hard gate for a 72f root-height candidate; cannot approve gait.

Requires original source-pinned sole witness, a derivative producer receipt and
measured skinned-shoe heights *after* the derivative is executed. Floor proxy
can pass while step/acceleration continuity fails and the clip is rejected.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA='scp.r009.root_y_floor_registration_trial.v1'
AFTER_SCHEMA='scp.r009.root_y_floor_trial_cpu_verification.v1'
ORIGINAL_SHA256='b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748'
ACTORS=('AsterOriginal','JuniperOriginal')
SIDES=('L','R')
MAX_Y_STEP_M=.003
MAX_Y_ACCEL_M=.005
class RootTrialGateError(ValueError):pass

def check(ok,msg):
    if not ok:raise RootTrialGateError(msg)

def num(v):return type(v) in (int,float) and math.isfinite(v)

def evaluate(receipt, after, sole, sole_raw=None):
    check(type(receipt) is dict and receipt.get('schema')==SCHEMA,'RECEIPT_SCHEMA')
    check(type(after) is dict and after.get('schema')==AFTER_SCHEMA,'AFTER_SCHEMA')
    check(type(sole) is dict and sole.get('source_sha256')==ORIGINAL_SHA256 and sole.get('frames')==72,'SOLE_SOURCE')
    check(receipt.get('source_sha256')==ORIGINAL_SHA256,'RECEIPT_SOURCE')
    digest=receipt.get('derived_sha256')
    check(type(digest) is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest),'DERIVED_SHA')
    check(after.get('source_sha256')==digest,'MEASURED_DERIVATIVE_SHA')
    check(after.get('frames')==72,'AFTER_FRAMES')
    if sole_raw is not None:check(hashlib.sha256(sole_raw).hexdigest()==receipt.get('sole_witness_sha256'),'SOLE_BYTES')
    for key in ('source_binary_prefix_equal','all_original_accessors_preserved','root_y_only',
                'source_geometry_unchanged','source_skin_unchanged','source_animation_non_root_unchanged','root_y_corrected_proxy_only'):
        check(receipt.get(key) is True,'MISSING_SOURCE_PRESERVATION:'+key)
    check(after.get('root_y_trial_executed') is True,'DERIVATIVE_NOT_EVALUATED')
    for d in (receipt,after):
        for flag in ('foot_lock_accepted','native_blender_evaluated','gait_accepted','release_approved'):
            if flag in d:check(d.get(flag) is False,'FALSE_GAIT_APPROVAL:'+flag)
        if 'foot_ik_applied' in d:check(d['foot_ik_applied'] is False,'FALSE_IK_APPROVAL')
    check(receipt.get('root_ik_applied') is False if 'root_ik_applied' in receipt else True,'FALSE_ROOT_IK')
    check(type(receipt.get('root_channels')) is list and len(receipt['root_channels'])==2,'TWO_ROOT_CHANNELS')
    check(type(after.get('per_side')) is dict and set(after['per_side'])==set(ACTORS),'AFTER_ACTORS')
    check(type(after.get('summary')) is dict and set(after['summary'])==set(ACTORS),'AFTER_SUMMARY')
    check(type(sole.get('actors')) is dict and set(sole['actors'])==set(ACTORS),'SOLE_ACTORS')
    results={}
    for actor in ACTORS:
        records=[r for r in receipt['root_channels'] if type(r) is dict and r.get('actor')==actor]
        check(len(records)==1,'ROOT_ACTOR_DUPLICATE')
        ch=records[0]
        heights=sole['actors'][actor].get('required_root_y_clearance_m')
        check(type(heights) is list and len(heights)==72 and all(num(x) and 0<=x<=.025 for x in heights),'72_ROOT_Y')
        maxstep=max(abs(heights[i]-heights[i-1]) for i in range(1,72))
        maxacc=max(abs(heights[i+1]-2*heights[i]+heights[i-1]) for i in range(1,71))
        check(all(num(ch.get(k)) for k in ('min_lift_m','max_lift_m','max_step_m')),'PRODUCER_BOUNDS')
        check(abs(ch['min_lift_m']-min(heights))<1e-8 and abs(ch['max_lift_m']-max(heights))<1e-8 and abs(ch['max_step_m']-maxstep)<1e-8,'BOUNDS_FABRICATED')
        check(type(ch.get('root_node')) is int and type(ch.get('original_accessor')) is int and type(ch.get('new_accessor')) is int and ch['new_accessor']!=ch['original_accessor'],'ROOT_ACCESSORS')
        rows=after['per_side'][actor]
        check(type(rows) is list and len(rows)==144,'144_SHOE_SAMPLES')
        seen=set();matrix={}
        for r in rows:
            check(type(r) is dict and set(r)=={'frame','side','min_y_m','vertices_below_minus_5mm','vertices_within_10mm_floor'},'SHOE_SAMPLE_FIELDS')
            f,s=r['frame'],r['side'];check(type(f) is int and 0<=f<72 and s in SIDES,'SAMPLE_LABEL')
            check((f,s) not in seen,'DUPLICATE_SHOE_SAMPLE');seen.add((f,s))
            y=r['min_y_m'];n=r['vertices_below_minus_5mm'];near=r['vertices_within_10mm_floor']
            check(num(y) and -.1<=y<=.2 and type(n) is int and n>=0 and type(near) is int and near>=0,'SAMPLE_NUMERIC')
            check((y<-.005)==(n>0),'COUNTER_MIN_INCONSISTENT')
            check(y<=.01 or near==0,'NEAR_FLOOR_COUNT_INVALID')
            matrix[(f,s)]=y
        stance=[min(matrix[(f,s)] for s in SIDES) for f in range(72)]
        other=after['summary'][actor]
        check(type(other) is dict,'SUMMARY_TYPE')
        expected={'worst_shoe_y_m':min(stance),'mean_stance_min_y_m':sum(stance)/72,
                  'frames_shoe_below_minus_5mm':sum(x<-.005 for x in stance),
                  'frames_both_feet_over_plus_10mm':sum(all(matrix[(f,s)]>.01 for s in SIDES) for f in range(72))}
        for k,v in expected.items():
            check(num(other.get(k)) and abs(other[k]-v)<=1e-7,'SUMMARY_MISMATCH:'+k)
        results[actor]={'worst_shoe_y_m':min(stance),'frames_penetrating_floor':expected['frames_shoe_below_minus_5mm'],
                        'frames_both_feet_hovering':expected['frames_both_feet_over_plus_10mm'],
                        'root_y_step_max_m':maxstep,'root_y_acceleration_max_m_per_frame2':maxacc,
                        'root_y_step_violation':maxstep>MAX_Y_STEP_M,
                        'root_y_acceleration_violation':maxacc>MAX_Y_ACCEL_M}
    penetrating=any(r['frames_penetrating_floor'] for r in results.values())
    hovering=any(r['frames_both_feet_hovering'] for r in results.values())
    jerk=any(r['root_y_step_violation'] or r['root_y_acceleration_violation'] for r in results.values())
    return {'schema':'scp.r009.root_y_trial_dual_gate.v1','source_sha256':ORIGINAL_SHA256,
            'derived_sha256':digest,'actors':results,'verdict':
               'RED_FLOOR_PENETRATION' if penetrating else
               'RED_FOOT_FLOATING' if hovering else
               'RED_ROOT_Y_JERK' if jerk else 'PASS_FLOOR_AND_CONTINUITY_PROXY_ONLY',
            'max_root_y_step_m':MAX_Y_STEP_M,'max_root_y_accel_m_per_frame2':MAX_Y_ACCEL_M,
            'root_only_gait_approved':False,'foot_ik_applied':False,
            'native_blender_evaluated':False,'physical_contact_accepted':False,
            'gait_accepted':False,'release_approved':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--receipt',required=True,type=Path)
    ap.add_argument('--after',required=True,type=Path);ap.add_argument('--sole',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    if a.out.exists() or len({p.resolve() for p in (a.receipt,a.after,a.sole,a.out)})!=4:raise RootTrialGateError('NO_OVERWRITE')
    sole_raw=a.sole.read_bytes()
    out=evaluate(json.loads(a.receipt.read_text()),json.loads(a.after.read_text()),json.loads(sole_raw),sole_raw)
    a.out.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'verdict':out['verdict'],'actors':out['actors']},sort_keys=True))
    if out['verdict']!='PASS_FLOOR_AND_CONTINUITY_PROXY_ONLY':raise SystemExit(12)
if __name__=='__main__':main()
