#!/usr/bin/env python3
"""Independent numerical 72-frame shoe-floor witness for root-Y research GLB.

CPU skinned world-space positions only. Does not assert physical foot-lock.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from costume_garment_v1 import _unpack_glb
from observe_makehuman35_motion_v0 import parents_of, worlds, frame_poses, mesh_primitive, matrices_accessor, skin_vertices

ACTORS=('AsterOriginal','JuniperOriginal')

def inspect(raw,expected_sha256):
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=expected_sha256:raise ValueError('DERIVED_SHA_MISMATCH')
    doc,b=_unpack_glb(raw);nodes=doc['nodes'];parents=parents_of(nodes)
    names={n.get('name'):i for i,n in enumerate(nodes)}
    rig=[]
    for ai,actor in enumerate(ACTORS):
        ni=names[actor+'_Wardrobe_footwear'];skin=doc['skins'][ai]
        if nodes[ni].get('skin')!=ai or len(skin['joints'])!=35:
            raise ValueError('SHOE_SKIN_CONTRACT')
        p,j,w,face=mesh_primitive(doc,b,nodes[ni]['mesh'])
        split={side:np.where((p[:,0]<0) if side=='L' else (p[:,0]>0))[0] for side in ('L','R')}
        if any(len(ids)<300 for ids in split.values()):raise ValueError('FOOT_SPLIT')
        rig.append((actor,ni,skin,p,j,w,split,matrices_accessor(doc,b,skin['inverseBindMatrices'])))
    rows={actor:[] for actor in ACTORS}
    frames=0
    for pose in frame_poses(doc,b):
        world=worlds(nodes,parents,pose)
        for actor,ni,skin,p,j,w,split,ibm in rig:
            local_to_world=world[ni];inv=np.linalg.inv(local_to_world)
            mats=np.stack([inv@world[n]@ibm[k] for k,n in enumerate(skin['joints'])])
            local=skin_vertices(p,j,w,mats)
            vec=np.column_stack((local.astype('float64'),np.ones(len(local))))
            y=(vec@local_to_world.T)[:,1]
            if not np.isfinite(y).all():raise ValueError('NONFINITE_SHOE_Y')
            for side,idx in split.items():
                z=y[idx];rows[actor].append({'frame':frames,'side':side,'min_y_m':float(z.min()),
                                             'vertices_below_minus_5mm':int(np.count_nonzero(z<-.005)),
                                             'vertices_within_10mm_floor':int(np.count_nonzero(np.abs(z)<=.010))})
        frames+=1
    if frames!=72:raise ValueError('FRAMES_NOT_72')
    summary={}
    for actor in ACTORS:
        vals=np.array([[next(r['min_y_m'] for r in rows[actor] if r['frame']==f and r['side']==s)
                        for s in ('L','R')] for f in range(72)])
        summary[actor]={'worst_shoe_y_m':float(vals.min()),'mean_stance_min_y_m':float(vals.min(axis=1).mean()),
                        'frames_shoe_below_minus_5mm':int(np.count_nonzero((vals<-.005).any(axis=1))),
                        'frames_both_feet_over_plus_10mm':int(np.count_nonzero((vals>.010).all(axis=1)))}
    return {'schema':'scp.r009.root_y_floor_trial_cpu_verification.v1','source_sha256':digest,
            'frames':72,'summary':summary,'per_side':rows,
            'root_y_trial_executed':True,'foot_ik_applied':False,
            'root_ik_applied':False,'native_blender_evaluated':False,
            'gait_accepted':False,'release_approved':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--glb',type=Path,required=True)
    ap.add_argument('--sha',required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists() or a.out.resolve()==a.glb.resolve():raise ValueError('NO_OVERWRITE')
    r=inspect(a.glb.read_bytes(),a.sha)
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps(r['summary'],sort_keys=True))
if __name__=='__main__':main()
