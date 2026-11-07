#!/usr/bin/env python3
"""Independent source-free 72f root envelope and CPU floor *proxy* gate.

Does not certify planted feet, IK, contact mechanics, physical cloth or gait.
"""
from __future__ import annotations
import json, math, hashlib, argparse
from pathlib import Path
from root_y_lipschitz_envelope_v1 import (
    build, SOURCE_SHA256, ACTORS, MAX_STEP_M, MAX_ACCEL_M,
    EnvelopeError, require,
)
SCHEMA='scp.r009.root_y_envelope_dual_gate.v1'
AFTER_SCHEMA='scp.r009.root_y_floor_trial_cpu_verification.v1'
RECEIPT_SCHEMA='scp.r009.root_y_envelope_glb_trial.v1'

def finite(v):return type(v) in (int,float) and math.isfinite(v)

def evaluate(sole,receipt,after,sole_raw=None):
    require(type(receipt) is dict and receipt.get('schema')==RECEIPT_SCHEMA,'PRODUCER_SCHEMA')
    require(type(after) is dict and after.get('schema')==AFTER_SCHEMA,'CPU_SCHEMA')
    mode=receipt.get('mode')
    expected=build(sole,mode)
    require(receipt.get('source_sha256')==SOURCE_SHA256,'SOURCE_SHA')
    if sole_raw is not None:require(receipt.get('sole_witness_sha256')==hashlib.sha256(sole_raw).hexdigest(),'SOLE_RAW_SHA')
    require(receipt.get('schedule')==expected,'SCHEDULE_FORGED')
    digest=receipt.get('derived_sha256')
    require(type(digest) is str and len(digest)==64 and all(x in '0123456789abcdef' for x in digest),'DERIVED_HASH')
    require(after.get('source_sha256')==digest and after.get('root_y_trial_executed') is True and after.get('frames')==72,'AFTER_SOURCE_FRAMES')
    for flag in ('source_original_bin_prefix_preserved','original_accessors_preserved','non_root_animations_preserved','rig_material_mesh_preserved'):
        require(receipt.get(flag) is True,'ORIGINAL_PRESERVATION:'+flag)
    for record in (receipt,after,expected):
        for k in ('native_blender_evaluated','natural_gait_accepted','gait_accepted','release_approved','physical_contact_accepted','foot_ik_applied','leg_ik_applied','root_ik_applied'):
            if k in record:require(record[k] is False,'FALSE_ACCEPTANCE:'+k)
    require(type(receipt.get('root_channels')) is list and len(receipt['root_channels'])==2,'ROOT_CHANNELS')
    require(type(after.get('per_side')) is dict and set(after['per_side'])==set(ACTORS),'ACTORS')
    require(type(after.get('summary')) is dict and set(after['summary'])==set(ACTORS),'AFTER_SUMMARIES')
    result={}
    for actor in ACTORS:
        records=[r for r in receipt['root_channels'] if type(r) is dict and r.get('actor')==actor]
        require(len(records)==1,'ROOT_ACTOR')
        ch=records[0]
        require(all(type(ch.get(k)) is int for k in ('root_node','sampler','original_accessor','new_accessor')),'ROOT_INDEX')
        require(ch['new_accessor']!=ch['original_accessor'],'ROOT_ORIGINAL_OVERWRITE')
        schedule=expected['actors'][actor]['proposed_lift_m']
        for k,reference in (('min_lift_m',min(schedule)),('max_lift_m',max(schedule)),('max_step_m',expected['actors'][actor]['max_root_y_step_m'])):
            require(finite(ch.get(k)) and abs(ch[k]-reference)<1e-9,'PRODUCER_BOUNDS:'+k)
        rows=after['per_side'][actor]
        require(type(rows) is list and len(rows)==144,'SHOE_SAMPLES')
        samples={}
        for row in rows:
            require(type(row) is dict,'ROW_TYPE')
            f=row.get('frame');side=row.get('side');y=row.get('min_y_m')
            require(type(f) is int and 0<=f<72 and side in ('L','R') and (f,side) not in samples,'FRAME_SIDE_UNIQUE')
            require(finite(y) and -.2<y<.2,'NONFINITE_Y')
            c5=row.get('vertices_below_minus_5mm');c10=row.get('vertices_within_10mm_floor')
            require(type(c5) is int and c5>=0 and type(c10) is int and c10>=0,'CONTACT_COUNTERS')
            require((y<-.005)==(c5>0),'MIN_COUNT_MISMATCH')
            if y>.010:require(c10==0,'NEAR_FLOOR_COUNT')
            samples[f,side]=y
        floor_by_frame=[min(samples[f,s] for s in ('L','R')) for f in range(72)]
        summary=after['summary'][actor]
        checks={'worst_shoe_y_m':min(floor_by_frame),'mean_stance_min_y_m':sum(floor_by_frame)/72,
            'frames_shoe_below_minus_5mm':sum(x<-.005 for x in floor_by_frame),
            'frames_both_feet_over_plus_10mm':sum(all(samples[f,s]>.010 for s in ('L','R')) for f in range(72))}
        for k,v in checks.items():require(finite(summary.get(k)) and abs(summary[k]-v)<=1e-7,'AFTER_SUMMARY:'+k)
        # Actual CPU witness should match the original Y-up sole minima translated by the proposal.
        source_y=[-x for x in sole['actors'][actor]['required_root_y_clearance_m']]
        for f in range(72):
            require(abs(floor_by_frame[f]-(source_y[f]+schedule[f]))<.00001,'CPU_FLOOR_DELTA_MISMATCH')
        height=expected['actors'][actor]
        require(height['max_root_y_step_m']<=MAX_STEP_M and height['max_root_y_second_diff_m']<=MAX_ACCEL_M,'CONTINUITY_BUDGET')
        result[actor]={'worst_shoe_y_m':checks['worst_shoe_y_m'],'frames_penetrating':checks['frames_shoe_below_minus_5mm'],
            'frames_dual_hover':checks['frames_both_feet_over_plus_10mm'],'max_root_y_step_m':height['max_root_y_step_m'],
            'max_root_y_second_diff_m':height['max_root_y_second_diff_m']}
    red=any(x['frames_penetrating'] or x['frames_dual_hover'] for x in result.values())
    return {'schema':SCHEMA,'source_sha256':SOURCE_SHA256,'derived_sha256':digest,
            'actors':result,'verdict':'RED_FLOOR_OR_HOVER' if red else 'PASS_FLOOR_AND_CONTINUITY_PROXY_ONLY',
            'leg_ik_applied':False,'native_blender_evaluated':False,'physical_contact_accepted':False,
            'natural_gait_accepted':False,'release_approved':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sole',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--after',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    require(len({p.resolve() for p in (a.sole,a.receipt,a.after,a.out)})==4 and not a.out.exists(),'NO_OVERWRITE')
    sole_raw=a.sole.read_bytes();r=evaluate(json.loads(sole_raw),json.loads(a.receipt.read_text()),json.loads(a.after.read_text()),sole_raw)
    a.out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n');print(json.dumps(r,sort_keys=True))
    if r['verdict']!='PASS_FLOOR_AND_CONTINUITY_PROXY_ONLY':raise SystemExit(12)
if __name__=='__main__':main()
