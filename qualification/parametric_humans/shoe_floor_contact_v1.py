#!/usr/bin/env python3
"""Source-pinned 72-frame glTF shoe/ground diagnostics (CPU LBS only).

Original self-authored Aster/Juniper + owner-admitted CC0 MakeHuman derivative.
This code NEVER claims physical pressure, gait realism, contact, or release.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
from costume_garment_v1 import _unpack_glb
from observe_makehuman35_motion_v0 import (parents_of,worlds,frame_poses,
    matrices_accessor,skin_vertices,mesh_primitive)
from retarget_makehuman_v0 import ACTORS

SCHEMA='scp.r009.shoe_floor_cpu72.v1'
INPUT_SHA256='b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748'
FLOOR_Y_M=0.0  # R009 source-original glTF coordinate system is Y-up.

def analyze(raw:bytes, expected_sha256=INPUT_SHA256):
    actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected_sha256:raise ValueError('SHOE_SOURCE_HASH_MISMATCH')
    doc,b=_unpack_glb(raw); nodes=doc['nodes'];parent=parents_of(nodes)
    names={n.get('name'):i for i,n in enumerate(nodes)}
    poses=list(frame_poses(doc,b))
    if len(poses)!=72:raise ValueError('EXPECTED_72_FRAMES')
    source=[]
    for ai,actor in enumerate(ACTORS):
        ni=names[actor+'_Wardrobe_footwear'];skin=doc['skins'][ai]
        if nodes[ni].get('skin')!=ai or len(skin['joints'])!=35:raise ValueError('EXPECTED_35_JOINT_SHOE')
        positions,joints,weights,faces=mesh_primitive(doc,b,nodes[ni]['mesh'])
        split={'L':positions[:,0]<0,'R':positions[:,0]>0}
        if any(int(mask.sum())<300 for mask in split.values()):raise ValueError('SPLIT_FOOT_SOURCE_MISMATCH')
        source.append((ai,actor,ni,skin,positions,joints,weights,split,matrices_accessor(doc,b,skin['inverseBindMatrices'])))
    rows={actor:[] for actor in ACTORS}
    for f,pose in enumerate(poses):
        world=worlds(nodes,parent,pose)
        for ai,actor,ni,skin,pos,joints,weights,split,ibm in source:
            local_to_world=world[ni];to_local=np.linalg.inv(local_to_world)
            mats=np.stack([to_local@world[k]@ibm[i] for i,k in enumerate(skin['joints'])])
            deformed=skin_vertices(pos,joints,weights,mats)
            # Compute absolute world Y, not mesh-local Y.
            homogeneous=np.column_stack((deformed.astype('float64'),np.ones(len(deformed))))
            world_y=(homogeneous@local_to_world.T)[:,1]
            if not np.isfinite(world_y).all():raise ValueError('NONFINITE_EVALUATED_SHOES')
            for side,mask in split.items():
                ys=world_y[mask];bottom=float(np.min(ys))
                rows[actor].append({'frame':f,'side':side,'min_y_m':bottom,
                    'vertices':int(len(ys)),
                    'vertices_below_minus_1mm':int(np.count_nonzero(ys < FLOOR_Y_M-0.001)),
                    'vertices_below_minus_5mm':int(np.count_nonzero(ys < FLOOR_Y_M-0.005)),
                    'vertices_within_10mm_floor':int(np.count_nonzero(np.abs(ys-FLOOR_Y_M)<=0.010))})
    summary={}
    for actor,fr in rows.items():
        y=np.array([[q['min_y_m'] for q in fr if q['frame']==i] for i in range(72)])
        if y.shape!=(72,2):raise ValueError('SAMPLE_SHAPE_MISMATCH')
        stance_min=y.min(axis=1)
        summary[actor]={'worst_min_y_m':float(y.min()),'stance_min_mean_y_m':float(stance_min.mean()),
            'frames_with_sole_below_minus_1mm':int(np.count_nonzero(stance_min < -0.001)),
            'frames_with_sole_below_minus_5mm':int(np.count_nonzero(stance_min < -0.005)),
            'foot_frame_count_below_minus_1mm':int(np.count_nonzero(y < -0.001)),
            'frames_both_feet_above_plus_10mm':int(np.count_nonzero(np.all(y > 0.010,axis=1))),
            'diagnostic_only_root_clearance_shift_m_min':float(np.min(-stance_min)),
            'diagnostic_only_root_clearance_shift_m_max':float(np.max(-stance_min)),
            'max_root_shift_delta_m_per_frame':float(np.max(np.abs(np.diff(-stance_min))))}
    return {'schema':SCHEMA,'source_sha256':actual,'coordinate_up':'Y','floor_y_m':FLOOR_Y_M,
            'actors':rows,'summary':summary,'frames_evaluated':72,
            'root_shift_applied':False,'native_blender_evaluated':False,
            'physical_contact_accepted':False,'realistic_gait_accepted':False,
            'release_approved':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--glb',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.out.exists() or a.out.resolve()==a.glb.resolve():raise ValueError('NO_OVERWRITE')
    report=analyze(a.glb.read_bytes());a.out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'source_sha256':report['source_sha256'],'summary':report['summary']},sort_keys=True))
if __name__=='__main__':main()
