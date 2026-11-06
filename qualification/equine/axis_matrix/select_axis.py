"""Source-only one-axis IK restriction diagnostic for public synthetic Shetland.

Select only one axis from x/y/z. Never authorizes release of an unrestricted rig.
"""
import argparse,hashlib,json
from pathlib import Path

AXES=('x','y','z')
def alter(source:Path,destination:Path,axis:str):
    if axis not in AXES:raise ValueError('axis allowlist x/y/z')
    if source.resolve()==destination.resolve():raise ValueError('refuse source modification')
    text=source.read_text()
    src=f'bone.use_ik_limit_{axis}=True'
    dst=f'bone.use_ik_limit_{axis}=False'
    if text.count(src)!=1 or dst in text:raise ValueError('source drift or repeated flag')
    updated=text.replace(src,dst)
    if updated.replace(dst,src)!=text:raise ValueError('multiple operations detected')
    if destination.exists():raise ValueError('refuse overwrite')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(updated)
    return {'schema':'equine.ik.single-axis-research-ablation.v1',
            'axis':axis,'source_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'candidate_sha256':hashlib.sha256(updated.encode()).hexdigest(),
            'changed_ik_axes':[axis],'source_original_modified':False,
            'axis_production_eligible':False,'veterinary_anatomy_accepted':False}
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path)
    p.add_argument('--candidate',required=True,type=Path)
    p.add_argument('--axis',required=True,choices=AXES)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();r=alter(a.source,a.candidate,a.axis)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('NONRELEASABLE_SINGLE_AXIS_IK_EXPERIMENT',a.axis)
if __name__=='__main__':main()
