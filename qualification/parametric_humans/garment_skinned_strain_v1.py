#!/usr/bin/env python3
"""Source-hash-guarded 72-frame skinned skirt strain witness, not cloth physics."""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from costume_garment_v1 import _unpack_glb
from observe_makehuman35_motion_v0 import parents_of,worlds,frame_poses,matrices_accessor,skin_vertices,mesh_primitive
from retarget_makehuman_v0 import ACTORS
SCHEMA='scp.r009.skirt_cpu72_edge_strain.v1'

def measure(raw,expected):
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('SOURCE_HASH_MISMATCH')
    d,b=_unpack_glb(raw);nodes=d['nodes'];names={n.get('name'):i for i,n in enumerate(nodes)}
    par=parents_of(nodes);base=worlds(nodes,par)
    src={}
    for ai,actor in enumerate(ACTORS):
        ni=names[actor+'_Wardrobe_costume_bottom'];skin=d['skins'][ai]
        if len(skin['joints'])!=35 or nodes[ni].get('skin')!=ai:raise ValueError('SKIN_MISMATCH')
        p,j,w,faces=mesh_primitive(d,b,nodes[ni]['mesh'])
        old=np.linalg.norm(p[faces[:,[1,2,0]]]-p[faces[:,[0,1,2]]],axis=2)
        if np.min(old)<=1e-6:raise ValueError('INVALID_REST_EDGE')
        a=np.cross(p[faces[:,1]]-p[faces[:,0]],p[faces[:,2]]-p[faces[:,0]])
        rest_area=np.linalg.norm(a,axis=1)
        if np.min(rest_area)<=1e-9:raise ValueError('INVALID_REST_TRIANGLE')
        src[actor]=(ni,skin,p,j,w,faces,old,rest_area,matrices_accessor(d,b,skin['inverseBindMatrices']))
    rows={actor:[] for actor in ACTORS}
    for fi,pose in enumerate(frame_poses(d,b)):
        world=worlds(nodes,par,pose)
        for actor,(ni,skin,p,j,w,f,old,rest_area,ibm) in src.items():
            inv=np.linalg.inv(world[ni]);mats=np.stack([inv@world[idx]@ibm[k] for k,idx in enumerate(skin['joints'])])
            moved=skin_vertices(p,j,w,mats)
            lengths=np.linalg.norm(moved[f[:,[1,2,0]]]-moved[f[:,[0,1,2]]],axis=2)
            ratios=lengths/old
            tri=np.cross(moved[f[:,1]]-moved[f[:,0]],moved[f[:,2]]-moved[f[:,0]])
            area_ratio=np.linalg.norm(tri,axis=1)/rest_area
            if not np.isfinite(ratios).all() or not np.isfinite(area_ratio).all():raise ValueError('NONFINITE_DEFORMATION')
            rows[actor].append({'frame':fi,'p99_edge_ratio':float(np.quantile(ratios,.99)),
                'max_edge_ratio':float(np.max(ratios)),
                'min_edge_ratio':float(np.min(ratios)),
                'fraction_strained_gt_50pct':float(np.mean((ratios>1.5)|(ratios<2/3))),
                'min_triangle_area_ratio':float(np.min(area_ratio)),
                'fraction_area_lt_quarter':float(np.mean(area_ratio<.25))})
    return {'schema':SCHEMA,'source_sha256':expected,'actors':rows,'frames':72,
        'native_blender_evaluated':False,'physical_cloth_qualified':False,'garment_fit_accepted':False,'release_approved':False}

def compare(a,b):
    if a['schema']!=SCHEMA or b['schema']!=SCHEMA or a['source_sha256']==b['source_sha256'] or a['frames']!=72 or b['frames']!=72:raise ValueError('DIFFERENT_OR_INVALID_CASES')
    check=('p99_edge_ratio','max_edge_ratio','fraction_strained_gt_50pct','fraction_area_lt_quarter')
    worsening=[];improving=[]
    for actor in ACTORS:
        for old,new in zip(a['actors'][actor],b['actors'][actor]):
            if old['frame']!=new['frame']:raise ValueError('FRAME_DRIFT')
            for metric in check:
                delta=new[metric]-old[metric]
                if delta>1e-6:worsening.append({'actor':actor,'frame':old['frame'],'metric':metric,'delta':float(delta)})
                elif delta< -1e-6:improving.append({'actor':actor,'frame':old['frame'],'metric':metric,'delta':float(delta)})
    return {'schema':'scp.r009.skirt_strain_pair_gate.v1','before_sha256':a['source_sha256'],'after_sha256':b['source_sha256'],
        'regression_count':len(worsening),'improvement_count':len(improving),
        'regression_examples':worsening[:20],
        'verdict':'RED_REGRESSION' if worsening else 'PASS_RELATIVE_ONLY' if improving else 'HOLD_NO_GAIN',
        'scientific_fit_accepted':False,'release_approved':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--glb',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists() or a.glb.resolve()==a.out.resolve():raise ValueError('NO_OVERWRITE')
    raw=a.glb.read_bytes();r=measure(raw,hashlib.sha256(raw).hexdigest());a.out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'source_sha256':r['source_sha256'],'actors':{actor:{'p99_max':max(x['p99_edge_ratio'] for x in rr),'strain50_max':max(x['fraction_strained_gt_50pct'] for x in rr)} for actor,rr in r['actors'].items()}},sort_keys=True))
if __name__=='__main__':main()
