#!/usr/bin/env python3
"""Reversible, source-bound vertical-root-only 72-frame GLB diagnostic.

Adjusts exactly two glTF root translation channel outputs on an *independent*
research derivative. This is NOT contact-phase, foot lock, IK, or gait approval.
Original buffer prefix, graph, mesh, material, skeleton and other channels
remain byte-identical. Every lifted-frame correction is a derived source witness.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from costume_garment_v1 import _unpack_glb, _pack_glb, _accessor
from sculpt_human_v1 import _read_accessor
from sole_phase_root_feasibility_v1 import evaluate as verify_sole_witness

SCHEMA='scp.r009.root_y_floor_registration_trial.v1'
SOURCE_SHA256='b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748'
ACTORS=('AsterOriginal','JuniperOriginal')


def derive(raw: bytes, sole_raw: bytes) -> tuple[bytes,dict]:
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise ValueError('GLB_SOURCE_HASH_MISMATCH')
    witness=json.loads(sole_raw)
    verify_sole_witness(witness)
    if witness.get('source_sha256')!=SOURCE_SHA256:
        raise ValueError('SOLE_SOURCE_HASH_MISMATCH')
    doc,b=_unpack_glb(raw)
    source_doc=copy.deepcopy(doc)
    node_ids={n.get('name'):i for i,n in enumerate(doc['nodes'])}
    channels=doc['animations'][0]['channels']
    samplers=doc['animations'][0]['samplers']
    before_bin=bytes(b)
    original_accessors=len(doc['accessors'])
    original_views=len(doc['bufferViews'])
    changed=[]
    for actor in ACTORS:
        root=node_ids[actor+'_SceneRoot']
        matches=[ch for ch in channels if ch['target']=={'node':root,'path':'translation'}]
        if len(matches)!=1:raise ValueError('EXPECTED_ROOT_TRANSLATION_CHANNEL:'+actor)
        ch=matches[0];sampler=samplers[ch['sampler']]
        if sampler.get('interpolation','LINEAR')!='LINEAR':raise ValueError('ROOT_INTERPOLATION_UNSUPPORTED')
        input_acc=doc['accessors'][sampler['input']]
        output_acc=doc['accessors'][sampler['output']]
        if output_acc['type']!='VEC3' or output_acc['componentType']!=5126 or output_acc['count']!=72:
            raise ValueError('ROOT_OUTPUT_V3_72_REQUIRED')
        if input_acc['count']!=72:raise ValueError('ROOT_INPUT_72_REQUIRED')
        values=np.asarray(_read_accessor(doc,b,sampler['output']),dtype=np.float64).reshape(72,3)
        lift=np.asarray(witness['actors'][actor]['required_root_y_clearance_m'],dtype=np.float64)
        if lift.shape!=(72,) or not np.isfinite(lift).all() or lift.min()<0 or lift.max()>.025:
            raise ValueError('SOURCE_LIFT_BOUNDS')
        if float(np.max(np.abs(np.diff(lift))))>.007:
            raise ValueError('SOURCE_LIFT_STEP_BOUNDS')
        updated=values.copy();updated[:,1]+=lift
        if not np.isfinite(updated).all():raise ValueError('NONFINITE_LIFT_OUTPUT')
        new_index=_accessor(doc,b,[float(x) for x in updated.flatten()],comp_type=5126,shape='VEC3',count=72,add_bounds=True)
        sampler['output']=new_index
        changed.append({'actor':actor,'root_node':root,'original_accessor':source_doc['animations'][0]['samplers'][ch['sampler']]['output'],
                        'new_accessor':new_index,'min_lift_m':float(lift.min()),'max_lift_m':float(lift.max()),
                        'max_step_m':float(np.max(np.abs(np.diff(lift))))})
    if len(b)<len(before_bin) or bytes(b[:len(before_bin)])!=before_bin:
        raise ValueError('ORIGINAL_BIN_MUTATED')
    if (doc['accessors'][:original_accessors]!=source_doc['accessors'] or
            doc['bufferViews'][:original_views]!=source_doc['bufferViews']):
        raise ValueError('ORIGINAL_ACCESSORS_CHANGED')
    for key in ('nodes','skins','meshes','materials','textures','images','samplers','scenes','scene'):
        if doc.get(key)!=source_doc.get(key):raise ValueError('SOURCE_GRAPH_CHANGED:'+key)
    if len(doc['animations'])!=len(source_doc['animations']):raise ValueError('CLIP_COUNT_CHANGED')
    source_channels=source_doc['animations'][0]['channels']
    if channels!=source_channels:raise ValueError('ANIMATION_CHANNEL_GRAPH_CHANGED')
    changed_sampler_ids={ch['sampler'] for ch in channels if ch['target'].get('path')=='translation' and ch['target'].get('node') in (node_ids[a+'_SceneRoot'] for a in ACTORS)}
    if len(changed_sampler_ids)!=2:raise ValueError('ROOT_SAMPLER_DUPLICATE')
    for i, (a,c) in enumerate(zip(source_doc['animations'][0]['samplers'],samplers)):
        if i not in changed_sampler_ids and a!=c:raise ValueError('OTHER_CHANNEL_MUTATED')
    receipt={'schema':SCHEMA,'source_sha256':SOURCE_SHA256,'sole_witness_sha256':hashlib.sha256(sole_raw).hexdigest(),
             'root_channels':changed,'source_binary_prefix_equal':True,'all_original_accessors_preserved':True,
             'root_y_only':True,'source_geometry_unchanged':True,'source_skin_unchanged':True,'source_animation_non_root_unchanged':True,
             'root_y_corrected_proxy_only':True,'root_ik_applied':False,'foot_lock_accepted':False,
             'native_blender_evaluated':False,'gait_accepted':False,'release_approved':False}
    result=_pack_glb(doc,b)
    receipt['derived_sha256']=hashlib.sha256(result).hexdigest()
    return result,receipt


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--glb',required=True,type=Path)
    ap.add_argument('--sole',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--receipt',required=True,type=Path)
    a=ap.parse_args()
    if len({a.glb.resolve(),a.sole.resolve(),a.out.resolve(),a.receipt.resolve()})!=4 or a.out.exists() or a.receipt.exists():
        raise ValueError('NO_OVERWRITE')
    raw,receipt=derive(a.glb.read_bytes(),a.sole.read_bytes())
    a.out.write_bytes(raw);a.receipt.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'derived_sha256':receipt['derived_sha256'],'root_channels':len(receipt['root_channels'])}))

if __name__=='__main__':main()
