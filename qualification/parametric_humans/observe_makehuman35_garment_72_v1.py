#!/usr/bin/env python3
"""Exact-source all-72-frame signed garment-vertex diagnostic (NOT cloth validation).

Reuses the original signed-distance evaluator; intentionally does not duplicate
its mesh or skinning implementation. Run with source-original public-safe GLB.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from observe_makehuman35_garment_v0 import inspect

SCHEMA='scp.r009.makehuman35.signed_wardrobe_contact_72_v1'
EXACT_FITTED_SHA='366fc2964e0e156988b0207735d89b8dbba18d6b92d0ac453e0d4fc7846fe99f'
ALL_FRAMES=('rest',*tuple(range(72)))

def evaluate(raw):
    if type(raw) is not bytes or hashlib.sha256(raw).hexdigest()!=EXACT_FITTED_SHA:
        raise ValueError('EXACT_FITTED_SOURCE_SHA_MISMATCH')
    report=inspect(raw,EXACT_FITTED_SHA,frames=ALL_FRAMES)
    summary={}
    for actor,rec in report['actors'].items():
        assert rec['all_sign_calibrated']
        summary[actor]={}
        for slot,rows in rec['slots'].items():
            assert len(rows)==73 and rows[0]['frame']=='rest'
            values=[x['negative_gt_5mm_fraction'] for x in rows[1:]]
            assert all(type(v) in (float,int) and 0<=v<=1 for v in values)
            summary[actor][slot]={
              'frame_count':len(values),
              'mean_fraction_gt_5mm':sum(values)/len(values),
              'max_fraction_gt_5mm':max(values),
              'worst_frame':max(range(72),key=lambda i:values[i]),
              'frames_fraction_gt_1pct':sum(v>.01 for v in values)}
    report['schema']=SCHEMA
    report['full_motion_72_frame_collision_qualified']=False
    report['native_blender_evaluated']=False
    report['cloth_fitting_accepted']=False
    report['signed_sample_count']=73*len(report['actors'])*4
    report['technical_summary']=summary
    report['scope']='all_frame_deformed_vertices_vs_body_only_not_triangle_collision_or_cloth'
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--glb',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    opts=parser.parse_args()
    if opts.out.exists() or opts.glb.resolve()==opts.out.resolve():
        raise ValueError('REFUSE_OVERWRITE')
    report=evaluate(opts.glb.read_bytes())
    opts.out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'schema':SCHEMA,'actors':report['technical_summary'],
      'source_sha256':EXACT_FITTED_SHA},sort_keys=True))

if __name__=='__main__':main()
