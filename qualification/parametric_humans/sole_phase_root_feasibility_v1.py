#!/usr/bin/env python3
"""Fail-closed 72-frame bilateral sole correspondence/root-only feasibility gate.

The necessary lower bound on maximum remaining lateral foot slip under any
*single rigid root translation* is half the relative displacement of two
persistent sole vertex sets. This does not constrain rotational root moves,
per-leg IK, floor forces, or biomechanical gait, and can NEVER approve gait.
"""
from __future__ import annotations
import json, math
from pathlib import Path
SCHEMA='scp.r009.shoe_sole_correspondence_cpu72.v1'
OUT_SCHEMA='scp.r009.root_only_footlock_feasibility.v1'
SOURCE_SHA256='b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748'
ACTORS=('AsterOriginal','JuniperOriginal')
CONFLICT_THRESHOLD_M=.020  # geometric disagreement = 2x chosen 10mm slip budget
class FeasibilityError(ValueError):pass

def require(ok,reason):
    if not ok:raise FeasibilityError(reason)

def number(x,low=None,high=None):
    return (type(x) in (int,float) and math.isfinite(x)
            and (low is None or x>=low) and (high is None or x<=high))

def evaluate(doc):
    require(type(doc) is dict and doc.get('schema')==SCHEMA,'BAD_SCHEMA')
    require(doc.get('source_sha256')==SOURCE_SHA256,'SOURCE_PIN')
    require(doc.get('frames')==72 and doc.get('coordinate_up')=='Y','COORDINATE_OR_FRAMES')
    for flag in ('root_shift_applied','native_blender_evaluated','gait_accepted','release_approved'):
        require(doc.get(flag) is False,'FALSE_APPROVAL:'+flag)
    require(type(doc.get('actors')) is dict and set(doc['actors'])==set(ACTORS),'ACTOR_SET')
    results={}
    for actor in ACTORS:
        row=doc['actors'][actor]
        require(type(row) is dict,'ACTOR_RECORD')
        heights=row.get('required_root_y_clearance_m')
        require(type(heights) is list and len(heights)==72 and all(number(x,-.1,.1) for x in heights),'CLEARANCE_72')
        transitions=row.get('transitions')
        require(type(transitions) is list and len(transitions)==71,'TRANSITIONS_71')
        dual=[];persistent=0;conflicts=[]
        for frame,rec in enumerate(transitions,1):
            require(type(rec) is dict and type(rec.get('frame_to')) is int and rec['frame_to']==frame,'NONCONTIGUOUS_FRAME')
            foot=rec.get('feet')
            require(type(foot) is dict and set(foot)=={'L','R'},'MISSING_FOOT')
            vectors={}
            for side in ('L','R'):
                s=foot[side]
                require(type(s) is dict,'FOOT_RECORD')
                n=s.get('persistent_vertices')
                require(type(n) is int and 0<=n<=20000,'PERSISTENT_VERTEX_COUNT')
                if n>=5:
                    require(set(s)=={'persistent_vertices','median_xz_motion_m','p95_rigid_translation_residual_m','median_sliding_m'},'FOOT_FIELDS')
                    vec=s['median_xz_motion_m']
                    require(type(vec) is list and len(vec)==2 and all(number(v,-1,1) for v in vec),'FOOT_MOTION_VECTOR')
                    require(number(s['p95_rigid_translation_residual_m'],0,1) and number(s['median_sliding_m'],0,1),'FOOT_MOTION_METRICS')
                    vectors[side]=vec; persistent+=1
                else:
                    require(set(s)=={'persistent_vertices'},'SPURIOUS_FOOT_METRICS')
            observed=rec.get('dual_support_root_motion_disagreement_m')
            if len(vectors)==2:
                expected=math.dist(vectors['L'],vectors['R'])
                require(number(observed,0,2) and abs(observed-expected)<=1e-8,'DUAL_DISAGREEMENT_MISMATCH')
                dual.append(expected)
                if expected>CONFLICT_THRESHOLD_M:
                    conflicts.append({'frame_to':frame,'opposing_root_motion_m':round(expected,9),
                                      'unavoidable_best_case_foot_slip_m':round(expected/2,9)})
            else:
                require(observed is None,'FORGED_DUAL_CONTACT')
        require(row.get('dual_contact_transitions')==len(dual),'DUAL_COUNT')
        require(row.get('persistent_foot_transitions')==persistent,'PERSISTENT_COUNT')
        maxdual=max(dual) if dual else None
        p95=sorted(dual)[int(math.ceil(.95*len(dual)))-1] if dual else None
        # Original witness used NumPy quantile's linear interpolation; verify
        # against the exact order-statistic interpolation, not a nearest-rank.
        if dual:
            sortedvals=sorted(dual);position=.95*(len(dual)-1);j=int(position)
            q=sortedvals[j]*(1-(position-j))+sortedvals[min(j+1,len(dual)-1)]*(position-j)
            require(number(row.get('dual_root_xz_disagreement_max_m'),0,2) and abs(row['dual_root_xz_disagreement_max_m']-maxdual)<=1e-8,'MAX_DUAL_MISMATCH')
            require(number(row.get('dual_root_xz_disagreement_p95_m'),0,2) and abs(row['dual_root_xz_disagreement_p95_m']-q)<=1e-8,'P95_DUAL_MISMATCH')
        else:
            require(row.get('dual_root_xz_disagreement_max_m') is None and row.get('dual_root_xz_disagreement_p95_m') is None,'EMPTY_DUAL_MISMATCH')
        require(number(row.get('root_y_clearance_periodic_jump_m'),0,.2) and abs(row['root_y_clearance_periodic_jump_m']-abs(heights[-1]-heights[0]))<=1e-8,'PERIODIC_JUMP_MISMATCH')
        results[actor]={'dual_contact_transitions':len(dual),'persistent_foot_transitions':persistent,
            'root_y_clearance_min_m':min(heights),'root_y_clearance_max_m':max(heights),
            'root_y_clearance_max_step_m':max(abs(heights[i]-heights[i-1]) for i in range(1,72)),
            'dual_root_motion_disagreement_max_m':maxdual,
            'root_translation_only_lower_bound_max_slip_m':maxdual/2 if dual else None,
            'conflicting_dual_support_transitions':len(conflicts),
            'conflict_examples':conflicts[:12]}
    conflict=any(x['conflicting_dual_support_transitions'] for x in results.values())
    enough=all(x['dual_contact_transitions'] for x in results.values())
    return {'schema':OUT_SCHEMA,'source_sha256':SOURCE_SHA256,'frames':72,
        'verdict':'RED_ROOT_TRANSLATION_ONLY_CONFLICT' if conflict else
                   'HOLD_NO_DUAL_CONTACT_EVIDENCE' if not enough else
                   'PASS_ROOT_TRANSLATION_FEASIBILITY_PROXY_ONLY',
        'root_translation_only':True,'conflict_threshold_m':CONFLICT_THRESHOLD_M,
        'actors':results,'root_shift_applied':False,
        'native_blender_evaluated':False,'physical_cloth_qualified':False,
        'foot_lock_accepted':False,'gait_accepted':False,'release_approved':False}

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--witness',required=True,type=Path);ap.add_argument('--out',required=True,type=Path)
    args=ap.parse_args()
    require(args.witness.resolve()!=args.out.resolve() and not args.out.exists(),'NO_OVERWRITE')
    result=evaluate(json.loads(args.witness.read_text()))
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'verdict':result['verdict'],'actors':{a:{'dual':v['dual_contact_transitions'],'conflicts':v['conflicting_dual_support_transitions']} for a,v in result['actors'].items()}},sort_keys=True))
    if result['verdict']!='PASS_ROOT_TRANSLATION_FEASIBILITY_PROXY_ONLY':raise SystemExit(12)
if __name__=='__main__':main()
