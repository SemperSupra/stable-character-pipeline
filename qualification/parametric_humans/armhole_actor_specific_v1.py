#!/usr/bin/env python3
"""Actor-specific armhole trial, original-only 35-joint garment bind-pose derivative.

Preserves all source body nodes, skeleton, animation and old garment meshes. This
trial is not an accepted wardrobe, cloth solver, or native Blender validation.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from costume_garment_v1 import _unpack_glb,_pack_glb,_accessor
from sculpt_human_v1 import _read_accessor
from retarget_makehuman_v0 import ACTORS,_vertex_normals
from armhole_profile_contract_v1 import ACTORS as PROFILE_ACTORS,validate_amounts,delta_x
BASE_SHA256='a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739'
class TrialError(ValueError):pass
SCHEMA='scp.r009.makehuman35.actor_armhole_trial.v1'

def derive(raw,amounts):
    if hashlib.sha256(raw).hexdigest()!=BASE_SHA256:raise TrialError('SOURCE_SHA_MISMATCH')
    validate_amounts(amounts)
    if ACTORS!=PROFILE_ACTORS:raise TrialError('ACTOR_MAP_DRIFT')
    d,b=_unpack_glb(raw);prefix=bytes(b);results={}
    for ai,actor in enumerate(ACTORS):
        nodes=[n for n in d['nodes'] if n.get('name')==actor+'_Wardrobe_costume_top']
        if len(nodes)!=1 or nodes[0].get('skin')!=ai or len(d['skins'][ai]['joints'])!=35:raise TrialError('WRONG_SKIN_OR_NODE')
        node=nodes[0];oldmesh=node['mesh'];prim=d['meshes'][oldmesh]['primitives'][0]
        if amounts[actor]==0:
            # Byte-preserving true no-op: do not append an accessor, recompute
            # normals, touch the mesh/node, or alter another actor's skin.
            results[actor]={'amplitude_m':0.,'max_edge_stretch':1.,'inverted_faces':0,
                            'changed_vertices':0,'source_mesh_retained':True}
            continue
        p=np.asarray(_read_accessor(d,b,prim['attributes']['POSITION']),dtype=np.float64).reshape(-1,3)
        faces=np.asarray(_read_accessor(d,b,prim['indices']),dtype=np.int64).reshape(-1,3)
        dr=np.zeros_like(p)
        dr[:,0]=[delta_x(float(x),float(y),float(z),amounts[actor]) for x,y,z in p]
        q=p+dr
        a=np.cross(p[faces[:,1]]-p[faces[:,0]],p[faces[:,2]]-p[faces[:,0]])
        c=np.cross(q[faces[:,1]]-q[faces[:,0]],q[faces[:,2]]-q[faces[:,0]])
        if np.any(np.einsum('ij,ij->i',a,c)<=1e-15):raise TrialError('INVERTED_TRIANGLE')
        before=np.linalg.norm(p[faces[:,[1,2,0]]]-p[faces[:,[0,1,2]]],axis=2)
        after=np.linalg.norm(q[faces[:,[1,2,0]]]-q[faces[:,[0,1,2]]],axis=2)
        stretch=float(np.max(after/np.maximum(before,1e-12)))
        if stretch>1.15:raise TrialError('UNBOUNDED_EDGE_STRETCH')
        changed=json.loads(json.dumps(prim))
        changed['attributes']['POSITION']=_accessor(d,b,q.ravel().tolist(),comp_type=5126,shape='VEC3',count=len(q),add_bounds=True)
        changed['attributes']['NORMAL']=_accessor(d,b,_vertex_normals(q,faces).ravel().tolist(),comp_type=5126,shape='VEC3',count=len(q))
        newmesh=len(d['meshes']);d['meshes'].append({'name':actor+'_ArmholeEaseTrial','primitives':[changed]})
        node['mesh']=newmesh;node.setdefault('extras',{})['source_mesh_before_armhole_trial']=oldmesh
        results[actor]={'amplitude_m':amounts[actor],'max_edge_stretch':stretch,'inverted_faces':0,
                       'changed_vertices':int(np.count_nonzero(np.linalg.norm(dr,axis=1)>1e-7))}
    if bytes(b[:len(prefix)])!=prefix:raise TrialError('SOURCE_BINARY_CHANGED')
    d.setdefault('extras',{})['actor_armhole_trial']={'schema':SCHEMA,'source_sha256':BASE_SHA256,'actors':results,
        'triangle_contact_qualified':False,'cloth_qualified':False,'visual_accepted':False,'release_approved':False}
    derived=_pack_glb(d,b)
    return derived,{'schema':SCHEMA,'source_sha256':BASE_SHA256,'derived_sha256':hashlib.sha256(derived).hexdigest(),
        'actors':results,'source_preserved':True,'garment_fit_accepted':False,'native_blender_evaluated':False,
        'release_approved':False}
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--aster',type=float,default=.005);ap.add_argument('--juniper',type=float,default=.010)
    a=ap.parse_args()
    if len({a.input.resolve(),a.out.resolve(),a.receipt.resolve()})!=3 or a.out.exists() or a.receipt.exists():raise TrialError('NO_OVERWRITE')
    raw,receipt=derive(a.input.read_bytes(),{ACTORS[0]:a.aster,ACTORS[1]:a.juniper});a.out.write_bytes(raw)
    a.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,sort_keys=True))
