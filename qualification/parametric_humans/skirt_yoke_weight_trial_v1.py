#!/usr/bin/env python3
"""Reversible 35-joint skirt-yoke weight hypotheses, synthetic R009 research only.

The source skirt currently assigns *every vertex* to the spine joint. This
isolated adapter gives controlled pelvis and paired hip influences toward the
hem while retaining exact bind geometry, rig, animation, other actor and the
original skirt mesh library. It does not solve garment intersections or cloth.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
from costume_garment_v1 import _unpack_glb,_pack_glb,_accessor
from sculpt_human_v1 import _read_accessor
from retarget_makehuman_v0 import ACTORS
from skirt_yoke_profile_contract_v1 import validate as validate_profile
SOURCE_SHA256='ae2b809ffa5cf5dfee0adf2f6b88b0a864e3588b95638de4c8b86e83a6e524af'
SCHEMA='scp.r009.skirt_yoke_weight_trial.v1'
class WeightTrialError(ValueError):pass

def smooth(t):
    t=np.clip(t,0.,1.)
    return t*t*(3-2*t)

def make_weights(positions,lower_strength,hip_share):
    if any(type(x) not in (float,int) or not math.isfinite(x) for x in (lower_strength,hip_share)) or not 0<=lower_strength<=.95 or not 0<=hip_share<=.8:
        raise WeightTrialError('BAD_PROFILE')
    p=np.asarray(positions,dtype=np.float64)
    if p.ndim!=2 or p.shape[1]!=3 or len(p)<100 or not np.isfinite(p).all():raise WeightTrialError('BAD_POSITIONS')
    if p[:,1].min()<.5 or p[:,1].max()>1.15:raise WeightTrialError('WRONG_GARMENT_OR_SCALE')
    # Smooth transition: source waist at y~1.03 stays spine anchored; lower
    # front/back hem gains pelvis/left/right hip without discontinuous seam.
    t=smooth((1.01-p[:,1])/.29)*float(lower_strength)
    left=.5*(1.-np.tanh(p[:,0]/.055))
    w=np.column_stack((1-t,t*(1-hip_share),t*hip_share*left,t*hip_share*(1-left)))
    if not np.isfinite(w).all() or np.abs(w.sum(axis=1)-1).max()>1e-12 or np.any(w<0):raise WeightTrialError('WEIGHTS_INVALID')
    return w.astype(np.float32)

def derive(raw,actor,strength,hip_share):
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise WeightTrialError('SOURCE_SHA_MISMATCH')
    if actor not in ACTORS:raise WeightTrialError('WRONG_ACTOR')
    validate_profile(actor,strength,hip_share)
    d,b=_unpack_glb(raw);original_binary=bytes(b)
    nodes=d['nodes'];ai=ACTORS.index(actor)
    names=[nodes[n]['name'].removeprefix(actor+'_') for n in d['skins'][ai]['joints']]
    if len(names)!=35:raise WeightTrialError('INVALID_35_JOINT_SKIN')
    require=('spine','pelvis','hip_L','hip_R')
    if not all(x in names for x in require):raise WeightTrialError('REQUIRED_JOINTS_MISSING')
    ids=[names.index(x) for x in require]
    wardrobe=[n for n in nodes if n.get('name')==actor+'_Wardrobe_costume_bottom']
    if len(wardrobe)!=1 or wardrobe[0].get('skin')!=ai:raise WeightTrialError('WRONG_WARDROBE_NODE')
    n=wardrobe[0];mesh_id=n['mesh'];source=d['meshes'][mesh_id]
    if len(source['primitives'])!=1:raise WeightTrialError('MULTIPRIM_SKIRT_UNSUPPORTED')
    prim=source['primitives'][0];attrs=prim['attributes']
    p=np.asarray(_read_accessor(d,b,attrs['POSITION']),dtype=np.float64).reshape(-1,3)
    origj=np.asarray(_read_accessor(d,b,attrs['JOINTS_0']),dtype=np.int64).reshape(-1,4)
    origw=np.asarray(_read_accessor(d,b,attrs['WEIGHTS_0']),dtype=np.float64).reshape(-1,4)
    # Only admit the diagnosed 100%-spine baseline: prevents applying the same
    # patch twice or silently overwriting an independently reauthored yoke.
    if len(p)!=320 or not np.all(origj[:,1]==ids[0]) or not np.allclose(origw[:,1],1.,atol=1e-6):
        raise WeightTrialError('BASELINE_NOT_SPINE_ONLY')
    weights=make_weights(p,strength,hip_share)
    if np.max(weights[:,1:])<1e-8:raise WeightTrialError('NO_MEASURABLE_WEIGHT_CHANGE')
    newj=np.tile(np.array(ids,dtype=np.uint8),(len(p),1))
    # Preserve exact world bind position; only change JOINTS/WEIGHTS attributes.
    new_prim=json.loads(json.dumps(prim))
    # In this authoring pipeline small <256 joint indices use glTF uint8.
    joff=_accessor(d,b,newj.ravel().tolist(),comp_type=5121,shape='VEC4',count=len(p))
    woff=_accessor(d,b,weights.ravel().tolist(),comp_type=5126,shape='VEC4',count=len(p))
    new_prim['attributes']['JOINTS_0']=joff
    new_prim['attributes']['WEIGHTS_0']=woff
    d['meshes'].append({'name':actor+'_SkirtYokeWeightTrial','primitives':[new_prim]})
    n['mesh']=len(d['meshes'])-1
    n.setdefault('extras',{})['source_mesh_before_yoke_weight_trial']=mesh_id
    if bytes(b[:len(original_binary)])!=original_binary:raise WeightTrialError('SOURCE_BYTES_MODIFIED')
    d.setdefault('extras',{})['skirt_yoke_weight_trial']={
        'schema':SCHEMA,'source_sha256':SOURCE_SHA256,'actor':actor,
        'lower_strength':float(strength),'hip_share':float(hip_share),
        'geometry_preserved':True,'skin_unchanged':True,'animation_unchanged':True,
        'garment_fit_accepted':False,'native_blender_evaluated':False,'release_approved':False}
    packed=_pack_glb(d,b)
    return packed,{'schema':SCHEMA,'source_sha256':SOURCE_SHA256,
        'derived_sha256':hashlib.sha256(packed).hexdigest(), 'actor':actor,
        'max_lower_weight':round(float(np.max(1-weights[:,0])),6),
        'lower_strength':float(strength),'hip_share':float(hip_share),
        'source_mesh_library_preserved':True,'untouched_actor_preserved':True,
        'garment_fit_accepted':False,'native_blender_evaluated':False,'release_approved':False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True)
    ap.add_argument('--actor',default='JuniperOriginal',choices=ACTORS)
    ap.add_argument('--strength',type=float,required=True)
    ap.add_argument('--hip-share',type=float,required=True)
    x=ap.parse_args()
    if len({x.input.resolve(),x.out.resolve(),x.receipt.resolve()})!=3 or x.out.exists() or x.receipt.exists():raise WeightTrialError('NO_OVERWRITE')
    raw,receipt=derive(x.input.read_bytes(),x.actor,x.strength,x.hip_share)
    x.out.write_bytes(raw);x.receipt.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt,sort_keys=True))
if __name__=='__main__':main()
