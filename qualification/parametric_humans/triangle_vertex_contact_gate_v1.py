#!/usr/bin/env python3
"""Stdlib no-regression gate joining *paired* CPU triangle and signed-vertex witnesses.

Rejects any frame/actor/slot regression, false scientific acceptance or unequal
sampling. Relative-only: no candidate can earn true clothing/physics/release
acceptance from sampled surface tests, even when all metrics improve.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

SCHEMA='scp.r009.dual_triangle_vertex_contact_gate.v1'
BVH='scp.r009.makehuman35.triangle_bvh_contact.v1'
SIGNED='scp.r009.makehuman35.signed_wardrobe_contact_sample.v0'
SLOTS=('costume_top','costume_bottom','costume_trim','footwear')
ACTORS=('AsterOriginal','JuniperOriginal')
class GateError(ValueError):pass

def validate(bvh,signed):
    if type(bvh) is not dict or bvh.get('schema')!=BVH or type(signed) is not dict or signed.get('schema')!=SIGNED:
        raise GateError('WRONG_INPUT_SCHEMA')
    if type(bvh.get('source_sha256')) is not str or len(bvh['source_sha256'])!=64 or any(x not in '0123456789abcdef' for x in bvh['source_sha256']):
        raise GateError('BAD_SHA256')
    if bvh['source_sha256']!=signed.get('source_sha256'):
        raise GateError('MISMATCHED_BVH_SIGNED_SOURCE')
    for k in ('native_blender_evaluated','cloth_physics_qualified','no_triangle_crossing_proven','wearable_fit_accepted','release_approved'):
        if bvh.get(k) is not False:raise GateError('FALSE_BVH_APPROVAL:'+k)
    for k in ('native_blender_evaluated','cloth_fitting_accepted','release_approved'):
        if signed.get(k) is not False:raise GateError('FALSE_SIGNED_APPROVAL:'+k)
    fr=bvh.get('frames')
    if type(fr) is not list or len(fr)<2 or len(fr)>73 or len(set(map(str,fr)))!=len(fr):
        raise GateError('BAD_FRAMES')
    if fr!=signed.get('witness_frames'):
        raise GateError('UNPAIRED_WITNESS_FRAMES')
    if bvh.get('frame_count')!=len(fr):raise GateError('WRONG_FRAME_COUNT')
    if set(bvh.get('actors',{}))!=set(ACTORS) or set(signed.get('actors',{}))!=set(ACTORS):
        raise GateError('ACTOR_DRIFT')
    metrics={}
    for actor in ACTORS:
        a=bvh['actors'][actor]['slots'];s=signed['actors'][actor]['slots']
        if set(a)!=set(SLOTS) or set(s)!=set(SLOTS):raise GateError('SLOT_DRIFT')
        metrics[actor]={}
        for slot in SLOTS:
            x=a[slot];y=s[slot]
            if len(x)!=len(fr) or len(y)!=len(fr):raise GateError('SAMPLE_SIZE_DRIFT')
            rows=[]
            for frame,triangle,vertex in zip(fr,x,y):
                count=triangle.get('triangle_contact_pairs')
                frac=vertex.get('negative_gt_5mm_fraction')
                if triangle.get('frame')!=frame or vertex.get('frame')!=frame:
                    raise GateError('SAMPLE_CLOCK_DRIFT')
                if type(count) is not int or count<0:raise GateError('INVALID_TRIANGLE_COUNT')
                if type(frac) not in (int,float) or not math.isfinite(frac) or not 0<=frac<=1 or vertex.get('sign_calibrated') is not True:
                    raise GateError('UNQUALIFIED_SIGNED_SAMPLE')
                rows.append((count,float(frac)))
            metrics[actor][slot]=rows
    return metrics

def compare(base_bvh,base_signed,test_bvh,test_signed,epsilon=1e-10):
    base=validate(base_bvh,base_signed);test=validate(test_bvh,test_signed)
    if base_bvh['source_sha256']==test_bvh['source_sha256']:
        raise GateError('IDENTICAL_SOURCE_NOT_AN_IMPROVEMENT')
    if base_bvh['frames']!=test_bvh['frames']:
        raise GateError('DIFFERENT_BASE_TEST_FRAMES')
    if type(epsilon) not in (int,float) or not math.isfinite(epsilon) or not 0<=epsilon<=1e-6:
        raise GateError('INVALID_EPSILON')
    red=[];wins=[];counts={}
    for actor in ACTORS:
        counts[actor]={}
        for slot in SLOTS:
            old=base[actor][slot];new=test[actor][slot]
            counts[actor][slot]={'triangles_before':sum(x[0] for x in old),
                'triangles_after':sum(x[0] for x in new),
                'vertex_mean_before':sum(x[1] for x in old)/len(old),
                'vertex_mean_after':sum(x[1] for x in new)/len(new)}
            for i,(a,b) in enumerate(zip(old,new)):
                for metric,prev,current in zip(('triangles','signed_fraction'),a,b):
                    delta=current-prev
                    ref=f'{actor}/{slot}/{base_bvh["frames"][i]}/{metric}'
                    if delta>epsilon:red.append({'metric':ref,'delta':round(delta,12)})
                    elif delta< -epsilon:wins.append({'metric':ref,'delta':round(delta,12)})
    verdict='RED_REGRESSION' if red else 'PASS_RELATIVE_ONLY' if wins else 'HOLD_NO_GAIN'
    return {'schema':SCHEMA,'baseline_sha256':base_bvh['source_sha256'],
        'candidate_sha256':test_bvh['source_sha256'],'frame_count':len(base_bvh['frames']),
        'verdict':verdict,'regressions':red,'improvements':wins,
        'per_actor_slot':counts,'scientific_first_red':bool(red),
        'all_72_frames_evaluated':base_bvh['frames']==['rest',*range(72)],
        'native_blender_evaluated':False,'physical_cloth_qualified':False,
        'triangle_collision_free_accepted':False,'wearable_fit_accepted':False,
        'release_approved':False}

def main():
    a=argparse.ArgumentParser()
    for n in ('base_bvh','base_signed','candidate_bvh','candidate_signed','receipt'):
        a.add_argument('--'+n.replace('_','-'),type=Path,required=True)
    q=a.parse_args()
    paths=(q.base_bvh,q.base_signed,q.candidate_bvh,q.candidate_signed,q.receipt)
    if len(set(p.resolve() for p in paths))!=len(paths) or q.receipt.exists():raise GateError('NO_OVERWRITE')
    result=compare(*(json.loads(p.read_text()) for p in paths[:4]))
    q.receipt.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':result['verdict'],'regressions':len(result['regressions']),
                      'improvements':len(result['improvements'])},sort_keys=True))
    if result['verdict']!='PASS_RELATIVE_ONLY':raise SystemExit(12)
if __name__=='__main__':main()
