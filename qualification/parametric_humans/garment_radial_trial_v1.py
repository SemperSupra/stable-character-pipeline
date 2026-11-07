#!/usr/bin/env python3
"""Additive bounded top or skirt radial-ease trial on original-only MakeHuman35.

Research ONLY: evaluated-source scene stays unchanged; old garment mesh stays in
GLB library; new garment mesh node retains inherited skin, weights, animation.
Changing vertex positions in bind pose is not a cloth solver.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from costume_garment_v1 import _unpack_glb,_pack_glb,_accessor
from sculpt_human_v1 import _read_accessor
from retarget_makehuman_v0 import ACTORS

BASE_SHA256='a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739'
SCHEMA='scp.r009.makehuman35.garment_radial_trial.v1'
SLOTS=('costume_top','costume_bottom')
class TrialError(ValueError):pass

def grade(positions,faces,amount):
    if type(amount) not in (int,float) or not math.isfinite(amount) or not 0<=amount<=.2:
        raise TrialError('INVALID_RADIAL_GRADE')
    p=np.asarray(positions,dtype=np.float64).reshape(-1,3)
    f=np.asarray(faces,dtype=np.int64).reshape(-1,3)
    if len(p)<20 or len(f)<20 or f.min()<0 or f.max()>=len(p) or not np.isfinite(p).all():
        raise TrialError('INVALID_SURFACE')
    if amount==0:return p.copy(),None,{'max_edge_ratio':1,'reversed_fraction':0,'changed':False}
    q=p.copy();q[:,(0,2)]*=1+amount
    a=np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    b=np.cross(q[f[:,1]]-q[f[:,0]],q[f[:,2]]-q[f[:,0]])
    if (np.linalg.norm(b,axis=1)<1e-12).any():raise TrialError('DEGENERATE_FACE')
    reversed_fraction=float(np.mean((a*b).sum(axis=1)<0))
    if reversed_fraction>0:raise TrialError('REVERSED_FACES')
    before=np.linalg.norm(p[f[:,[1,2,0]]]-p[f[:,[0,1,2]]],axis=2)
    after=np.linalg.norm(q[f[:,[1,2,0]]]-q[f[:,[0,1,2]]],axis=2)
    stretch=float((after/np.maximum(before,1e-12)).max())
    if stretch>1.21:raise TrialError('OVERSTRETCH')
    normal=np.zeros_like(q)
    for k in range(3):np.add.at(normal,f[:,k],b)
    mag=np.linalg.norm(normal,axis=1)
    if (mag<1e-10).any():raise TrialError('NORMALS_UNDEFINED')
    normal/=mag[:,None]
    return q,normal,{'max_edge_ratio':stretch,'reversed_fraction':reversed_fraction,'changed':True}

def derive(raw,base_sha,slot,amount):
    if hashlib.sha256(raw).hexdigest()!=base_sha or base_sha!=BASE_SHA256:
        raise TrialError('SOURCE_SHA_MISMATCH')
    if slot not in SLOTS:raise TrialError('INVALID_SLOT')
    d,b=_unpack_glb(raw);prefix=bytes(b)
    for ai,who in enumerate(ACTORS):
        ni=next((i for i,n in enumerate(d['nodes']) if n.get('name')==who+'_Wardrobe_'+slot),None)
        if ni is None:raise TrialError('MISSING_GARMENT_NODE')
        node=d['nodes'][ni]
        if node.get('skin')!=ai or len(d['skins'][ai]['joints'])!=35:raise TrialError('WRONG_SKIN')
        prim=d['meshes'][node['mesh']]['primitives'][0]
        p=np.asarray(_read_accessor(d,b,prim['attributes']['POSITION']),dtype=np.float64).reshape(-1,3)
        f=np.asarray(_read_accessor(d,b,prim['indices']),dtype=np.int64).reshape(-1,3)
        out,n,metrics=grade(p,f,amount)
        if metrics['changed']:
            replacement=json.loads(json.dumps(prim))
            replacement['attributes']['POSITION']=_accessor(d,b,out.ravel().tolist(),comp_type=5126,shape='VEC3',count=len(out),add_bounds=True)
            replacement['attributes']['NORMAL']=_accessor(d,b,n.ravel().tolist(),comp_type=5126,shape='VEC3',count=len(out))
            oldid=node['mesh'];newid=len(d['meshes'])
            d['meshes'].append({'name':who+'_'+slot+'_RadialTrial','primitives':[replacement]})
            node['mesh']=newid
            node.setdefault('extras',{})['pretrial_mesh_index']=oldid
            node['extras']['fit_accepted']=False
    if bytes(b[:len(prefix)])!=prefix:raise TrialError('SOURCE_BINARY_CHANGED')
    d.setdefault('extras',{})['garment_radial_trial']={'schema':SCHEMA,'source_sha256':base_sha,
        'slot':slot,'amount':amount,'cloth_simulated':False,'fit_accepted':False,'release_approved':False}
    out=_pack_glb(d,b)
    return out,{'source_sha256':base_sha,'derived_sha256':hashlib.sha256(out).hexdigest(),
            'slot':slot,'amount':amount,'source_preserved':True,'motion_fit_accepted':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--slot',choices=SLOTS,required=True)
    ap.add_argument('--amount',type=float,required=True)
    args=ap.parse_args()
    if args.output.exists() or args.input.resolve()==args.output.resolve():raise TrialError('NO_OVERWRITE')
    out,receipt=derive(args.input.read_bytes(),BASE_SHA256,args.slot,args.amount)
    args.output.write_bytes(out)
    print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__':main()
