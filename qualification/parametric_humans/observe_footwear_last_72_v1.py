#!/usr/bin/env python3
"""Exact-byte 72-frame CPU signed shoe/body vertex witness, not native Blender.

Adapts the preexisting source-owned signed garment observer. Preserves a strict
non-approval label even if observed inclusion is zero in all frames.
"""
import argparse,hashlib,json
from pathlib import Path
from observe_makehuman35_garment_v0 import inspect
SCHEMA='scp.r009.makehuman35.shoe_vertex_contact72.v1'
FRAMES=('rest',*tuple(range(72)))

def evaluate(raw,expected_sha):
    if hashlib.sha256(raw).hexdigest()!=expected_sha:raise ValueError('SOURCE_SHA_MISMATCH')
    doc=inspect(raw,expected_sha,frames=FRAMES)
    measurements={}
    for actor,record in doc['actors'].items():
        assert record['all_sign_calibrated']
        measurements[actor]={}
        for slot,rows in record['slots'].items():
            if len(rows)!=73:raise ValueError('INVALID_MOTION_SAMPLE_COUNT')
            vals=[x['negative_gt_5mm_fraction'] for x in rows]
            if any(v is None or not 0<=v<=1 for v in vals):raise ValueError('UNTRUSTED_SIGN')
            measurements[actor][slot]={'rest':vals[0],'mean_72':sum(vals[1:])/72,
              'max_72':max(vals[1:]),'worst_frame':max(range(72),key=lambda i:vals[i+1]),
              'frames_above_one_pct':sum(x>.01 for x in vals[1:])}
    return {'schema':SCHEMA,'source_sha256':expected_sha,'frames_per_actor':72,
      'method':'CPU_animated_vertex_signed_distance_proxy_NOT_triangle_BVH',
      'actors':measurements,'native_blender':False,
      'triangle_collision_accepted':False,'visual_realism_accepted':False,
      'natural_gait_accepted':False,'release_approved':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.input.resolve()==a.out.resolve() or a.out.exists():raise ValueError('NO_OVERWRITE')
    x=evaluate(a.input.read_bytes(),a.sha256)
    a.out.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'sha256':a.sha256,'frames':72,'actors':x['actors'],'motion_accepted':False},sort_keys=True))
if __name__=='__main__':main()
