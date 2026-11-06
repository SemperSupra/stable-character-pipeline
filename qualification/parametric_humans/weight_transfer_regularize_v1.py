#!/usr/bin/env python3
"""R009 source-pinned MakeHuman 35-joint skin-weight regularization (technical only).

Preserves both original actors' geometry, UVs, nodes, scene, rig, animation,
materials and source binary prefix. Appends replacement JOINTS_0/WEIGHTS_0
accessors only to two previously built, source-pinned candidate body meshes.
Does not qualify anatomical accuracy, motion, facial likeness or cloth fit.
Requires NumPy/SciPy; source-free adversarial tests can run without assets.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = 'scp.r009.makehuman35.skin_weight_regularization.v1'
SOURCE_SHA = '57a4cfd1d9df7e6e2f7c2e44e68765a8ca4357895d5b075f9229b78a5bbcd36a'
ACTORS = ('AsterOriginal', 'JuniperOriginal')
ALPHA = .5
ITERATIONS = 4

class SkinGateError(ValueError):
    pass

def check_sha(raw, digest=SOURCE_SHA):
    if type(raw) is not bytes or type(digest) is not str or len(digest) != 64:
        raise SkinGateError('SOURCE_FORMAT_INVALID')
    if any(ch not in '0123456789abcdef' for ch in digest):
        raise SkinGateError('SOURCE_DIGEST_INVALID')
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise SkinGateError('SOURCE_SHA_MISMATCH')
    return actual

def regularize(pos, faces, joints, weights, *, alpha=ALPHA, iterations=ITERATIONS):
    import numpy as np
    from scipy import sparse
    if type(iterations) is not int or iterations not in (1,2,3,4,5,6,7,8):
        raise SkinGateError('ITERATION_BOUND')
    if type(alpha) not in (float,int) or not .05 <= alpha <= .75:
        raise SkinGateError('ALPHA_BOUND')
    p = np.asarray(pos, dtype=np.float64)
    f = np.asarray(faces, dtype=np.int64)
    j = np.asarray(joints)
    w = np.asarray(weights, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 3 or len(p) < 4 or not np.isfinite(p).all() or np.max(np.abs(p)) > 10:
        raise SkinGateError('POSITION_INVALID')
    if f.ndim != 2 or f.shape[1] != 3 or len(f) < 2 or f.min() < 0 or f.max() >= len(p):
        raise SkinGateError('FACE_INVALID')
    if j.shape != (len(p),4) or w.shape != (len(p),4) or j.dtype.kind not in 'ui' or j.min() < 0 or j.max() >= 35:
        raise SkinGateError('JOINT_INVALID')
    if not np.isfinite(w).all() or (w < 0).any() or np.max(np.abs(w.sum(axis=1)-1)) > 2e-4:
        raise SkinGateError('WEIGHT_INVALID')
    if (f[:,0] == f[:,1]).any() or (f[:,1]==f[:,2]).any() or (f[:,0]==f[:,2]).any():
        raise SkinGateError('TOPOLOGY_DEGENERATE')
    masses = np.zeros((len(p),35), dtype=np.float64)
    rows = np.arange(len(p))
    for k in range(4):
        np.add.at(masses,(rows,j[:,k]),w[:,k])
    # The OBJ deliberately splits UV seams. Weld ONLY coincident rest vertices
    # for *weight smoothing*; preserve all geometry/UV indices unchanged.
    _, labels, counts = np.unique(np.round(p,5),axis=0,return_inverse=True,return_counts=True)
    g = sparse.coo_matrix((np.ones(len(p),dtype=np.float64),(rows,labels)),shape=(len(p),len(counts))).tocsr()
    seam = g @ sparse.diags(1./counts) @ g.T
    mass = seam @ masses
    # Source mesh has a known continuous anatomical surface, not disconnected
    # floaters. Laplacian applies only to neighboring topological edges.
    starts = np.concatenate((f[:,0],f[:,1],f[:,1],f[:,2],f[:,2],f[:,0]))
    ends   = np.concatenate((f[:,1],f[:,0],f[:,2],f[:,1],f[:,0],f[:,2]))
    edges = sparse.coo_matrix((np.ones(len(starts)),(starts,ends)),shape=(len(p),len(p))).tocsr()
    edges.data[:]=1
    edges.setdiag(0);edges.eliminate_zeros()
    degrees=np.asarray(edges.sum(axis=1)).reshape(-1)
    if (degrees == 0).any(): raise SkinGateError('ISOLATED_VERTEX')
    transition=sparse.diags(1/degrees)@edges
    for _ in range(iterations):
        mass = (1-alpha)*mass + alpha*(transition@mass)
        mass = seam@mass
    if not np.isfinite(mass).all() or (mass < -1e-10).any():
        raise SkinGateError('SMOOTHING_NUMERICAL_INVALID')
    rank = np.argsort(-mass,axis=1,kind='stable')[:,:4]
    selected = np.take_along_axis(mass,rank,axis=1)
    denom=selected.sum(axis=1,keepdims=True)
    if (denom[:,0] <= 0).any():raise SkinGateError('WEIGHT_MASS_LOST')
    selected=(selected/denom).astype(np.float32)
    old_max = np.max(np.abs(masses-(seam@masses)))
    new_mass=np.zeros_like(masses)
    for k in range(4):np.add.at(new_mass,(rows,rank[:,k]),selected[:,k])
    new_max = np.max(np.abs(new_mass-(seam@new_mass)))
    if new_max > 2e-5 or np.max(np.abs(selected.sum(axis=1)-1)) > 2e-5:
        raise SkinGateError('SEAM_OR_SUM_INCONSISTENT')
    # Differential is a research record, not necessarily a geometric benefit.
    changed=float(np.mean(np.linalg.norm(masses-new_mass,axis=1)>1e-5))
    witness={'vertex_count':len(p),'face_count':len(f),
             'uv_seam_duplicates':len(p)-len(counts),
             'original_seam_max_mass_delta':float(old_max),
             'output_seam_max_mass_delta':float(new_max),
             'altered_weight_vertex_fraction':changed,
             'iterations':iterations,'alpha':alpha,
             'numerically_normalized':True,
             'motion_acceptance':False,'anatomical_weight_acceptance':False}
    return rank.astype(np.uint8),selected,witness

def derive(raw: bytes):
    from costume_garment_v1 import _unpack_glb,_pack_glb,_accessor
    from sculpt_human_v1 import _read_accessor
    import numpy as np
    source_sha=check_sha(raw)
    doc, buf=_unpack_glb(raw)
    c=doc.get('extras',{}).get('makehuman_candidate_v0',{})
    if c.get('schema')!='scp.r009.makehuman35.retarget_candidate.v0' or len(doc.get('skins',[]))!=2 or any(len(s['joints'])!=35 for s in doc['skins']):
        raise SkinGateError('NOT_EXPECTED_CC0_RIG_CANDIDATE')
    if len(doc.get('animations',[]))!=1:
        raise SkinGateError('ANIMATION_MISSING')
    notes={}
    for i,actor in enumerate(ACTORS):
        nodes=[n for n in doc['nodes'] if n.get('name')==actor+'_Candidate_MakeHuman_35Joint_Body']
        if len(nodes)!=1 or nodes[0].get('skin')!=i:
            raise SkinGateError('CANDIDATE_NODE_OR_SKIN_MISMATCH')
        prims=doc['meshes'][nodes[0]['mesh']]['primitives']
        if len(prims)!=1:raise SkinGateError('CANDIDATE_NOT_SINGLE_PRIMITIVE')
        prim=prims[0]; attrs=prim['attributes']
        pos=np.asarray(_read_accessor(doc,buf,attrs['POSITION']),dtype=np.float32).reshape(-1,3)
        faces=np.asarray(_read_accessor(doc,buf,prim['indices']),dtype=np.int64).reshape(-1,3)
        j=np.asarray(_read_accessor(doc,buf,attrs['JOINTS_0']),dtype=np.uint8).reshape(-1,4)
        w=np.asarray(_read_accessor(doc,buf,attrs['WEIGHTS_0']),dtype=np.float32).reshape(-1,4)
        if len(pos)!=14517 or len(faces)!=26756:
            raise SkinGateError('EXPECTED_CC0_BODY_MESH_TOPOLOGY')
        joints,weights,notes[actor]=regularize(pos,faces,j,w)
        attrs['JOINTS_0']=_accessor(doc,buf,joints.reshape(-1).astype(int).tolist(),comp_type=5121,shape='VEC4',count=len(pos))
        attrs['WEIGHTS_0']=_accessor(doc,buf,weights.reshape(-1).tolist(),comp_type=5126,shape='VEC4',count=len(pos))
    doc.setdefault('extras',{})['makehuman_weight_regularization_v1']={
        'schema':SCHEMA,'source_candidate_sha256':source_sha,
        'method':'bounded_graph_laplacian_with_UV_seam_weight_coincidence',
        'iterations':ITERATIONS,'alpha':ALPHA,'morphology_accepted':False,
        'weight_fidelity_accepted':False,'motion_accepted':False,
        'cloth_collision_accepted':False,'visual_realism_accepted':False,
        'release_approved':False}
    output=_pack_glb(doc,buf)
    receipt={'schema':SCHEMA,'source_sha256':source_sha,
        'derived_sha256':hashlib.sha256(output).hexdigest(),
        'source_data_binary_prefix_preserved':True,
        'original_skin_and_animation_documents_unchanged':True,
        'body_vertex_and_face_geometry_unchanged':True,
        'actor_quality':notes,'tests_are_technical_only':True,
        'anatomical_realism_accepted':False,'cloth_fit_accepted':False,
        'motion_accepted':False,'release_approved':False}
    return output,receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--candidate-glb',required=True,type=Path)
    p.add_argument('--out-glb',required=True,type=Path)
    p.add_argument('--receipt',required=True,type=Path)
    a=p.parse_args()
    paths=[a.candidate_glb.resolve(),a.out_glb.resolve(),a.receipt.resolve()]
    if len(set(paths))!=3 or a.out_glb.exists() or a.receipt.exists():
        raise SkinGateError('NO_OVERWRITE_OR_ALIAS')
    derived,receipt=derive(a.candidate_glb.read_bytes())
    a.out_glb.write_bytes(derived)
    a.receipt.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'output_sha256':receipt['derived_sha256'],'actors':
       {k:{'seams':v['uv_seam_duplicates'],'weight_changed_pct':round(100*v['altered_weight_vertex_fraction'],2)} for k,v in receipt['actor_quality'].items()}}))

if __name__ == '__main__':main()
