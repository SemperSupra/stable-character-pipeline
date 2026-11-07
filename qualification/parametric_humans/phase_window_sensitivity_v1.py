#!/usr/bin/env python3
"""R009 source-pinned, stdlib-only transition sensitivity witness.

This produces *proxy* stance/swing/ambiguous intervals, NOT gait/ground-force
truth, IK targets, or a publishable animation. Real ankle + sole evidence is
required and the exact prior persistent-vertex correspondence is validated.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from foot_phase_reclassification_gate_v1 import (
    evaluate as validate_prior, SCHEMA, OLD_SCHEMA, SOURCE_SHA256,
    ACTORS, SIDES, PhaseEvidenceError,
)

OUT_SCHEMA='scp.r009.phase_window_sensitivity.v1'
SCENARIOS=((.004,.004,2),(.006,.006,2),(.008,.008,2),(.012,.012,2),(.008,.008,3))

def require(condition, why):
    if not condition: raise PhaseEvidenceError(why)

def distance_xz(a,b):
    return math.hypot(a[0]-b[0],a[2]-b[2])

def classify(ankle,shoes,lifts,prior_transitions,stationary,proximity,minimum_run):
    require(0<stationary<=.012 and 0<proximity<=.012 and 2<=minimum_run<=5,'SENSITIVITY_LIMITS')
    label=[]
    for t in range(1,72):
        persistent=prior_transitions[t-1]['persistent_vertices']>=5
        motion=distance_xz(ankle[t],ankle[t-1])
        ground=max(shoes[t]+lifts[t],shoes[t-1]+lifts[t-1])
        near=ground<=proximity
        if persistent and near and motion<=stationary:label.append('stance_candidate')
        elif motion>2*stationary or ground>2*proximity:label.append('swing_proxy')
        else:label.append('ambiguous')
    # Avoid accepting one-transition planted contacts: require contiguous support.
    result=label[:]
    for i,lab in enumerate(label):
        if lab!='stance_candidate':continue
        l=i;r=i
        while l>0 and label[l-1]=='stance_candidate':l-=1
        while r+1<len(label) and label[r+1]=='stance_candidate':r+=1
        if r-l+1<minimum_run:result[i]='ambiguous'
        else:result[i]='stance_proxy'
    return result

def evaluate(witness,prior,prior_raw=None):
    validated=validate_prior(witness,prior,prior_raw)
    require(validated.get('root_only_impossibility_proven') is False,'INVALID_PRIOR_GATE')
    rows=[]
    for ankle_m,ground_m,minrun in SCENARIOS:
        actor_rows={}
        for actor in ACTORS:
            observed=witness['actors'][actor]; old=prior['actors'][actor]
            per_side={}
            for side in SIDES:
                per_side[side]=classify(observed['ankle_world_xyz_m'][side],observed['shoe_min_y_m'][side],
                    observed['diagnostic_root_lift_m'],[r['feet'][side] for r in old['transitions']],
                    ankle_m,ground_m,minrun)
            dual=sum(per_side['L'][i]=='stance_proxy' and per_side['R'][i]=='stance_proxy' for i in range(71))
            actor_rows[actor]={'counts':{side:{status:per_side[side].count(status) for status in ('stance_proxy','swing_proxy','ambiguous')} for side in SIDES},
                               'dual_proxy_transitions':dual, 'labels':per_side}
        rows.append({'ankle_max_m_per_transition':ankle_m,'floor_proximity_max_m':ground_m,
                     'minimum_run_transitions':minrun,'actors':actor_rows})
    # If a transition's status changes when thresholds change, it is uncertain.
    sensitivity={}
    for actor in ACTORS:
        sensitivity[actor]={}
        for side in SIDES:
            vectors=[[scenario['actors'][actor]['labels'][side][f] for scenario in rows] for f in range(71)]
            stable=[i+1 for i,v in enumerate(vectors) if len(set(v))==1 and v[0]=='stance_proxy']
            variable=[i+1 for i,v in enumerate(vectors) if len(set(v))>1]
            sensitivity[actor][side]={'robust_stance_proxy_transition_count':len(stable),
                                      'threshold_sensitive_transition_count':len(variable),
                                      'robust_stance_transition_to_frames':stable,
                                      'threshold_sensitive_transition_to_frames':variable}
    return {'schema':OUT_SCHEMA,'source_sha256':SOURCE_SHA256,'witness_schema':SCHEMA,
            'prior_schema':OLD_SCHEMA,'witness_sha256':None,'prior_sha256':hashlib.sha256(prior_raw).hexdigest() if prior_raw is not None else None,
            'scenarios':rows,'sensitivity':sensitivity,
            'held_out_heel_ball_toe_tracking':False,'persistent_shoe_vertex_ids_present':False,
            'stance_physics_certified':False,'foot_ik_applied':False,'root_shift_applied':False,
            'native_blender_evaluated':False,'natural_gait_accepted':False,'release_approved':False,
            'verdict':'STANCE_SWING_AMBIGUITY_RESEARCH_ONLY'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--witness',type=Path,required=True);ap.add_argument('--prior',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists() or len({x.resolve() for x in (a.witness,a.prior,a.out)})!=3:raise PhaseEvidenceError('NO_OVERWRITE')
    w=a.witness.read_bytes();p=a.prior.read_bytes();out=evaluate(json.loads(w),json.loads(p),p)
    out['witness_sha256']=hashlib.sha256(w).hexdigest()
    a.out.write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'verdict':out['verdict'],'sensitivity':{a:{s:{k:v for k,v in row.items() if k.endswith('_count')} for s,row in ss.items()} for a,ss in out['sensitivity'].items()}},sort_keys=True))
if __name__=='__main__':main()
