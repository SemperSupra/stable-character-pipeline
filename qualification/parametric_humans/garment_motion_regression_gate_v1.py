#!/usr/bin/env python3
"""R009 stdlib-only multi-metric regression gate for 72-frame garment QA.

Relative gate only: cannot certify triangle collision, physiology, native Blender,
cloth, gait, appearance or release. Rejects tempting best-frame improvements
if they worsen rest, average, maximum or frequency on any garment/actor.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
SCHEMA='scp.r009.makehuman35.shoe_vertex_contact72.v1'
OUTPUT_SCHEMA='scp.r009.garment_motion_regression_gate.v1'
ACTORS=('AsterOriginal','JuniperOriginal')
SLOTS=('costume_bottom','costume_top','costume_trim','footwear')
FIELDS=('rest','max_72','mean_72','frames_above_one_pct')
class RegressionError(ValueError):pass

def _validate(data,label):
    if type(data) is not dict or data.get('schema')!=SCHEMA or data.get('frames_per_actor')!=72:
        raise RegressionError(label+':BAD_SCHEMA_OR_FRAME_COUNT')
    if any(data.get(k) is not False for k in ('native_blender','triangle_collision_accepted','visual_realism_accepted','release_approved')):
        raise RegressionError(label+':FALSE_SCIENTIFIC_APPROVAL')
    if type(data.get('source_sha256')) is not str or len(data['source_sha256'])!=64 or any(c not in '0123456789abcdef' for c in data['source_sha256']):
        raise RegressionError(label+':INVALID_SHA256')
    actors=data.get('actors')
    if type(actors) is not dict or set(actors)!=set(ACTORS):raise RegressionError(label+':ACTOR_SET_DRIFT')
    for actor,slots in actors.items():
        if type(slots) is not dict or set(slots)!=set(SLOTS):raise RegressionError(label+':SLOT_SET_DRIFT:'+actor)
        for slot,values in slots.items():
            if type(values) is not dict or set(values)!=set((*FIELDS,'worst_frame')):
                raise RegressionError(label+':METRIC_KEYS:'+actor+':'+slot)
            if any(type(values[k]) not in (float,int) or not math.isfinite(values[k]) or not 0<=values[k]<=1 for k in FIELDS[:3]):
                raise RegressionError(label+':BOUNDED_METRIC:'+actor+':'+slot)
            if not (type(values['frames_above_one_pct']) is int and 0<=values['frames_above_one_pct']<=72):
                raise RegressionError(label+':FRAME_FREQUENCY:'+actor+':'+slot)
            if type(values['worst_frame']) is not int or not 0<=values['worst_frame']<72:
                raise RegressionError(label+':WORST_FRAME:'+actor+':'+slot)
            if values['mean_72']>values['max_72']+1e-10:
                raise RegressionError(label+':BAD_MEAN_MAX:'+actor+':'+slot)
    return True

def compare(baseline,candidate,*,epsilon=1e-10):
    _validate(baseline,'BASELINE');_validate(candidate,'CANDIDATE')
    if baseline['source_sha256']==candidate['source_sha256']:
        raise RegressionError('SAME_SOURCE_SHA_NO_CLAIMABLE_IMPROVEMENT')
    if type(epsilon) not in (float,int) or not math.isfinite(epsilon) or not 0<=epsilon<=1e-6:
        raise RegressionError('INVALID_EPSILON')
    entries={};red=[];gains=[]
    for actor in ACTORS:
        entries[actor]={}
        for slot in SLOTS:
            before=baseline['actors'][actor][slot]
            after=candidate['actors'][actor][slot]
            diffs={k:round(after[k]-before[k],12) for k in FIELDS}
            entries[actor][slot]=diffs
            for k,delta in diffs.items():
                label=f'{actor}/{slot}/{k}'
                if delta>epsilon:red.append({'path':label,'delta':delta})
                elif delta < -epsilon:gains.append({'path':label,'delta':delta})
    verdict='RED_REGRESSION' if red else 'PASS_RELATIVE_ONLY' if gains else 'HOLD_NO_IMPROVEMENT'
    return {'schema':OUTPUT_SCHEMA,'baseline_sha256':baseline['source_sha256'],
      'candidate_sha256':candidate['source_sha256'],'verdict':verdict,
      'regressions':red,'improvements':gains,'deltas':entries,
      'all_72_frames_per_actor_evaluated':True,'triangle_collision_qualified':False,
      'cloth_fitting_accepted':False,'release_approved':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if len({a.baseline.resolve(),a.candidate.resolve(),a.out.resolve()})!=3 or a.out.exists():
        raise RegressionError('NO_OVERWRITE')
    r=compare(json.loads(a.baseline.read_text()),json.loads(a.candidate.read_text()))
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'verdict':r['verdict'],'regression_count':len(r['regressions']),
                      'improvement_count':len(r['improvements'])},sort_keys=True))
    if r['verdict']!='PASS_RELATIVE_ONLY':raise SystemExit(12)

if __name__=='__main__':main()
