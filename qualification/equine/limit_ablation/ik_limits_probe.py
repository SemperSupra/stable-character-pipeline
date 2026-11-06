"""Diagnostic-only ablation: disable provisional IK-axis guards in sealed source copy.

Do NOT integrate or release this unconstrained leg controller. Its purpose is
only to test whether temporary axis limits explain measured swing residuals.
"""
import argparse,hashlib,json
from pathlib import Path
FLAGS=('x','y','z')

def ablate(original:Path,destination:Path):
    if original.resolve()==destination.resolve():raise ValueError('source mutation forbidden')
    content=original.read_text()
    updated=content
    for axis in FLAGS:
        src=f'bone.use_ik_limit_{axis}=True'
        dst=f'bone.use_ik_limit_{axis}=False'
        if content.count(src)!=1 or dst in content:
            raise ValueError('unexpected or already modified IK guard')
        updated=updated.replace(src,dst)
    if updated==content:raise ValueError('ablation did nothing')
    if destination.exists():raise ValueError('candidate overwrite forbidden')
    if updated.replace('=False','=True')!=content:
        raise ValueError('unbounded source operation')
    destination.write_text(updated)
    return {'schema':'equine.ik.source-axis-limit-ablation.v1','source_sha256':hashlib.sha256(content.encode()).hexdigest(),
            'candidate_sha256':hashlib.sha256(updated.encode()).hexdigest(),
            'only_three_ik_axis_guard_flags_changed':True,
            'candidate_anatomical_limits_validated':False,
            'candidate_production_eligible':False,'owner_source_modified':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    report=ablate(a.source,a.candidate)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print('IK_PROVISIONAL_LIMITS_DISABLED_ONLY_IN_DISPOSABLE_SOURCE; PRODUCTION_INELIGIBLE')
if __name__=='__main__':main()
