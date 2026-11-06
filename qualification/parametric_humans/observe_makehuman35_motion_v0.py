#!/usr/bin/env python3
"""Independent exact-sample CPU LBS deformation diagnostic for source-bound CC0 candidate.

Not native Blender, not biomechanical motion or garment collision acceptance.
Preserves a scientific first-RED for 72-frame edge strain and fit witnesses.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from costume_garment_v1 import _unpack_glb
from sculpt_human_v1 import _read_accessor
from retarget_makehuman_v0 import SCHEMA, ACTORS, CANDIDATE_GLB_SHA256

MOTION_SCHEMA='scp.r009.makehuman35.cpu72_motion_quality.v0'

def to_matrix(n):
    if 'matrix' in n:
        return np.array(n['matrix'],dtype=np.float64).reshape((4,4),order='F')
    m=np.eye(4,dtype=np.float64)
    m[:3,3]=n.get('translation',[0,0,0])
    m[:3,:3]=Rotation.from_quat(n.get('rotation',[0,0,0,1])).as_matrix() @ np.diag(n.get('scale',[1,1,1]))
    return m

def parents_of(nodes):
    parent=[-1]*len(nodes)
    for i,n in enumerate(nodes):
        for c in n.get('children',[]):
            if parent[c]>=0: raise ValueError('MULTIPLE_PARENTS')
            parent[c]=i
    return parent

def worlds(nodes,parents,pose=None):
    matrices=[]
    for i,node in enumerate(nodes):
        if pose and i in pose:
            n=dict(node);n.update(pose[i])
        else:n=node
        matrices.append(to_matrix(n))
    cache={}
    def calc(i):
        if i not in cache:
            p=parents[i]
            cache[i]=calc(p)@matrices[i] if p>=0 else matrices[i]
        return cache[i]
    return [calc(i) for i in range(len(nodes))]

def frame_poses(d,b):
    a=d['animations'][0]
    common=np.array(_read_accessor(d,b,a['samplers'][0]['input']),dtype=np.float64)
    if len(common)!=72 or not np.isfinite(common).all() or np.diff(common).min()<=0:
        raise ValueError('EXPECTED_72_SAMPLE_CLOCK')
    channels=[]
    for c in a['channels']:
        sampler=a['samplers'][c['sampler']]
        times=np.array(_read_accessor(d,b,sampler['input']),dtype=np.float64)
        if len(times)!=72 or np.max(np.abs(times-common))>2e-6:
            raise ValueError('CLOCK_NOT_MATCHED')
        path=c['target']['path']
        if path not in ('translation','rotation') or sampler.get('interpolation') not in ('LINEAR',None):
            raise ValueError('UNSUPPORTED_ANIMATION_CHANNEL')
        vals=np.array(_read_accessor(d,b,sampler['output']),dtype=np.float64).reshape(72,-1)
        if vals.shape[1]!=(4 if path=='rotation' else 3):
            raise ValueError('CHANNEL_SHAPE')
        channels.append((c['target']['node'],path,vals))
    yield from ({idx:{path:vals[f] for ni,path,vals in channels if ni==idx}
                for idx in set(ni for ni,_,_ in channels)} for f in range(72))

def matrices_accessor(d,b,index):
    acc=d['accessors'][index]
    if acc['type']!='MAT4' or acc['componentType']!=5126 or acc['count']!=35:
        raise ValueError('BAD_INVERSE_BIND_ACCESSOR')
    view=d['bufferViews'][acc['bufferView']]
    if view.get('buffer',0)!=0 or 'sparse' in acc:
        raise ValueError('UNSUPPORTED_INVERSE_BIND_FORMAT')
    stride=view.get('byteStride',64)
    if stride!=64:raise ValueError('UNEXPECTED_MATRIX_STRIDE')
    offset=view.get('byteOffset',0)+acc.get('byteOffset',0)
    if offset+35*64>len(b):raise ValueError('INVERSE_BIND_OOB')
    flat=np.frombuffer(b,dtype='<f4',count=35*16,offset=offset).copy()
    return flat.reshape(35,4,4).transpose(0,2,1).astype(np.float64)

def mesh_primitive(d,b,meshid):
    prim=d['meshes'][meshid]['primitives'][0]
    p=np.asarray(_read_accessor(d,b,prim['attributes']['POSITION']),dtype=np.float32).reshape(-1,3)
    j=np.asarray(_read_accessor(d,b,prim['attributes']['JOINTS_0']),dtype=np.int32).reshape(-1,4)
    w=np.asarray(_read_accessor(d,b,prim['attributes']['WEIGHTS_0']),dtype=np.float32).reshape(-1,4)
    faces=np.asarray(_read_accessor(d,b,prim['indices']),dtype=np.int32).reshape(-1,3)
    return p,j,w,faces

def skin_vertices(p,j,w,mats):
    h=np.concatenate((p.astype(np.float64),np.ones((len(p),1))),axis=1)
    verts=np.zeros((len(p),4),dtype=np.float64)
    for k in range(4):
        # Vectorized over all candidate vertices; 35 matrices and 4 influences.
        verts+=(np.einsum('nij,nj->ni',mats[j[:,k]],h))*w[:,k,None]
    if not np.isfinite(verts).all() or np.abs(verts[:,3]-1).max()>5e-4:
        raise ValueError('SKIN_NUMERICAL_INVALID')
    return verts[:,:3].astype(np.float32)

def triangle_metrics(rest,deformed,faces):
    r=rest[faces];p=deformed[faces]
    old=np.linalg.norm(r[:,[1,2,0]]-r[:,[0,1,2]],axis=2)
    new=np.linalg.norm(p[:,[1,2,0]]-p[:,[0,1,2]],axis=2)
    valid=old>1e-5
    ratios=new[valid]/old[valid]
    if len(ratios)<20000 or not np.isfinite(ratios).all():raise ValueError('EDGE_METRICS_INVALID')
    return {
        'valid_edges':int(valid.sum()),
        'edge_stretch_ratio_p99':float(np.quantile(ratios,.99)),
        'edge_stretch_ratio_max':float(np.max(ratios)),
        'edge_compress_ratio_p01':float(np.quantile(ratios,.01)),
        'edge_compress_ratio_min':float(np.min(ratios)),
        'edge_strain_gt_50pct_fraction':float(np.mean((ratios>1.5)|(ratios<2/3))),
        'deformed_bounds_min':p.min(axis=(0,1)).tolist(),
        'deformed_bounds_max':p.max(axis=(0,1)).tolist()}

def inspect(raw,expected_sha256):
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('DERIVATIVE_HASH_MISMATCH')
    d,b=_unpack_glb(raw)
    if d.get('extras',{}).get('makehuman_candidate_v0',{}).get('schema')!=SCHEMA:
        raise ValueError('CANDIDATE_SCHEMA_MISMATCH')
    nodes=d['nodes'];parent=parents_of(nodes)
    restworld=worlds(nodes,parent)
    pairs=[]
    for i,actor in enumerate(ACTORS):
        ni=next(i for i,n in enumerate(nodes) if n['name']==actor+'_Candidate_MakeHuman_35Joint_Body')
        skin=d['skins'][i]
        p,j,w,f=mesh_primitive(d,b,nodes[ni]['mesh'])
        ibm=matrices_accessor(d,b,skin['inverseBindMatrices'])
        # Body mesh node local frame follows its actor SceneRoot transform.
        bind=np.stack([np.linalg.inv(restworld[ni])@restworld[jid]@ibm[k]
                       for k,jid in enumerate(skin['joints'])])
        maxerr=float(np.max(np.abs(bind-np.eye(4))))
        pairs.append((actor,ni,skin,p,j,w,f,ibm,maxerr))
    rows={a:{'frames':[], 'max_bind_rest_error':err,'body_vertices':len(p),'body_triangles':len(f)} for a,ni,skin,p,j,w,f,ibm,err in pairs}
    for fi,pose in enumerate(frame_poses(d,b)):
        animation_world=worlds(nodes,parent,pose)
        for actor,ni,skin,p,j,w,f,ibm,err in pairs:
            mat=np.stack([np.linalg.inv(animation_world[ni])@animation_world[jid]@ibm[k]
                           for k,jid in enumerate(skin['joints'])])
            deformed=skin_vertices(p,j,w,mat)
            row=triangle_metrics(p,deformed,f)
            row['frame']=fi
            rows[actor]['frames'].append(row)
    for actor in ACTORS:
        frames=rows[actor]['frames']
        rows[actor]['global_edge_stretch_p99_max_over_frames']=max(x['edge_stretch_ratio_p99'] for x in frames)
        rows[actor]['worst_edge_strain_gt_50pct_fraction']=max(x['edge_strain_gt_50pct_fraction'] for x in frames)
        rows[actor]['worst_deformed_edge_ratio']=max(x['edge_stretch_ratio_max'] for x in frames)
        rows[actor]['skin_rest_aligned_to_inverse_bind']=rows[actor]['max_bind_rest_error']<1e-4
        rows[actor]['motion_accepted']=False
    return {'schema':MOTION_SCHEMA,'candidate_sha256':expected_sha256,
            'eval_backend':'CPU glTF native accessor + quaternion linear-sample LBS',
            'actual_72_frames_evaluated':all(len(rows[a]['frames'])==72 for a in ACTORS),
            'actors':rows,'native_blender_evaluated':False,
            'geometry_penetration_qualified':False,
            'cloth_collision_accepted':False,'realistic_motion_accepted':False,
            'release_approved':False}

def main():
    q=argparse.ArgumentParser()
    q.add_argument('--glb',required=True,type=Path)
    q.add_argument('--out',required=True,type=Path)
    a=q.parse_args()
    if a.out.exists() or a.out.resolve()==a.glb.resolve(): raise ValueError('NO_OVERWRITE')
    src=a.glb.read_bytes()
    result=inspect(src,CANDIDATE_GLB_SHA256)
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'72_frames':result['actual_72_frames_evaluated'],
            'actors':{x:{'rest_bind_err':round(r['max_bind_rest_error'],5),
                      'p99_stretch_max':round(r['global_edge_stretch_p99_max_over_frames'],3),
                      'worst_50pct_edge_strain_frac':round(r['worst_edge_strain_gt_50pct_fraction'],4)}
                 for x,r in result['actors'].items()}}))

if __name__=='__main__':main()
