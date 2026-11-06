"""Non-certifying scientific A/B comparator for exact native 30-joint GLB evidence.

Operational tests may succeed even when the scientific result is a rejection.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

FEET=('front_L_hoof','front_R_hoof','hind_L_hoof','hind_R_hoof')

def read_json(path):
    data=Path(path).read_bytes()
    if not data or len(data)>4*1024*1024:raise ValueError('unbounded report')
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out:raise ValueError('duplicate JSON key '+k)
            out[k]=v
        return out
    return json.loads(data,object_pairs_hook=unique)

def side_report(science):
    if science.get('schema')!='equine.foot.science.v1' or science.get('frames')!=48:
        raise ValueError('wrong observed native hoof schema')
    if science.get('source')!='native_evaluated_skin_mesh':
        raise ValueError('not native observed hoof evidence')
    by=science.get('feet',{})
    if set(by)!=set(FEET):raise ValueError('missing/extra hoof')
    result={}
    for name in FEET:
        f=by[name]
        for k in ('skate_pairs_over_3cm','max_near_ground_displacement_m','max_ground_penetration_m','frames_above_swing_clearance'):
            if k not in f or not math.isfinite(float(f[k])) or float(f[k])<0:raise ValueError('invalid physical proxy '+k)
        result[name]={'skate_pairs':int(f['skate_pairs_over_3cm']),
                      'max_frame_displacement_m':float(f['max_near_ground_displacement_m']),
                      'max_penetration_m':float(f['max_ground_penetration_m']),
                      'frames_with_swing_clearance':int(f['frames_above_swing_clearance'])}
    return result

def compare(baseline_hoof,candidate_hoof,baseline_rom,candidate_rom,baseline_reach,candidate_reach,
            baseline_sha,candidate_sha):
    for sha in (baseline_sha,candidate_sha):
        if len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):raise ValueError('missing model SHA')
    if baseline_sha==candidate_sha:raise ValueError('candidate model unchanged')
    a,b=side_report(baseline_hoof),side_report(candidate_hoof)
    for r in (baseline_rom,candidate_rom):
        if r.get('schema')!='equine.rom.science.v1' or r.get('observed_frames')!=48:
            raise ValueError('missing independent 48-frame joint observer')
        if set(r.get('joint_reports',{}))!=set(('front_L','front_R','hind_L','hind_R')):
            raise ValueError('missing joint metrics')
    for r in (baseline_reach,candidate_reach):
        if r.get('schema')!='equine.ik.reachability-hypothesis.v1':raise ValueError('wrong source reach report')
    base_fail=sum(baseline_reach['baseline'][f]['infeasible_frame_count'] for f in ('front_L','front_R'))
    new_fail=sum(candidate_reach['baseline'][f]['infeasible_frame_count'] for f in ('front_L','front_R'))
    base_skate=sum(a[f]['skate_pairs'] for f in ('front_L_hoof','front_R_hoof'))
    new_skate=sum(b[f]['skate_pairs'] for f in ('front_L_hoof','front_R_hoof'))
    front_swing=sum(b[f]['frames_with_swing_clearance']>0 for f in ('front_L_hoof','front_R_hoof'))
    baseline_rom_fail=set(baseline_rom['failure_codes'])
    new_rom_fail=set(candidate_rom['failure_codes'])
    novel_rom=sorted(new_rom_fail-baseline_rom_fail)
    hind_skate_before=sum(a[f]['skate_pairs'] for f in ('hind_L_hoof','hind_R_hoof'))
    hind_skate_after=sum(b[f]['skate_pairs'] for f in ('hind_L_hoof','hind_R_hoof'))
    improves=(new_fail<base_fail and new_skate<base_skate and front_swing==2 and
              not novel_rom and hind_skate_after<=hind_skate_before)
    return {'schema':'equine.ik.native-ab.noncertifying.v1',
      'source_class':'PUBLIC_ORIGINAL_SYNTHETIC','comparison':'EXACT_30J_NATIVE_EVALUATED_GLBS',
      'baseline_glb_sha256':baseline_sha,'candidate_glb_sha256':candidate_sha,
      'baseline_front_unreachable_target_samples':base_fail,
      'candidate_front_unreachable_target_samples':new_fail,
      'baseline_front_skate_pairs':base_skate,'candidate_front_skate_pairs':new_skate,
      'baseline_hind_skate_pairs':hind_skate_before,'candidate_hind_skate_pairs':hind_skate_after,
      'candidate_front_hooves_with_swing':front_swing,
      'baseline_rom_failure_codes':sorted(baseline_rom_fail),
      'candidate_rom_failure_codes':sorted(new_rom_fail),
      'new_rom_failures':novel_rom,
      'candidate_anatomy_veterinary_acceptance':False,
      'candidate_contact_force_accepted':False,
      'candidate_visual_accepted':False,'merge_release_CPE_authorized':False,
      'outcome':'CANDIDATE_PROXY_IMPROVEMENT_NOT_ACCEPTED' if improves else 'REJECT_OR_INCONCLUSIVE_CANDIDATE',
      'per_foot_baseline':a,'per_foot_candidate':b}

def main():
    ap=argparse.ArgumentParser()
    for name in ('baseline-hoof','candidate-hoof','baseline-rom','candidate-rom','baseline-reach','candidate-reach'):
        ap.add_argument('--'+name,required=True,type=Path)
    ap.add_argument('--baseline-glb',required=True,type=Path)
    ap.add_argument('--candidate-glb',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args()
    def hash_file(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    result=compare(*[read_json(getattr(a,name.replace('-','_'))) for name in ('baseline-hoof','candidate-hoof','baseline-rom','candidate-rom','baseline-reach','candidate-reach')],
        hash_file(a.baseline_glb),hash_file(a.candidate_glb))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('INDEPENDENT_EXPORTED_NATIVE_A_B',result['outcome'])
if __name__=='__main__':main()
