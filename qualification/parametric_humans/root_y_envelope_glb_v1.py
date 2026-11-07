#!/usr/bin/env python3
"""Source-original R009 reversible Y-only envelope diagnostic GLB generator.

All original GLB BIN bytes, original accessors, scene/mesh/rig/wardrobe and
other animation channels remain unchanged. Does not implement IK or gait.
"""
from __future__ import annotations
import argparse, copy, hashlib, json
from pathlib import Path
import numpy as np
from costume_garment_v1 import _unpack_glb, _pack_glb, _accessor
from sculpt_human_v1 import _read_accessor
from sole_phase_root_feasibility_v1 import evaluate as validate_sole
from root_y_lipschitz_envelope_v1 import build, SOURCE_SHA256, ACTORS, EnvelopeError

SCHEMA='scp.r009.root_y_envelope_glb_trial.v1'

def require(cond, reason):
    if not cond:raise EnvelopeError(reason)

def derive(raw:bytes, sole_raw:bytes,mode='minimal_envelope'):
    require(hashlib.sha256(raw).hexdigest()==SOURCE_SHA256,'ORIGINAL_GLB_SHA')
    sole=json.loads(sole_raw)
    validate_sole(sole)
    schedule=build(sole,mode)
    doc,b=_unpack_glb(raw)
    original=copy.deepcopy(doc); original_bin=bytes(b)
    original_count=len(doc['accessors']);views_count=len(doc['bufferViews'])
    names={node.get('name'):i for i,node in enumerate(doc['nodes'])}
    channels=doc['animations'][0]['channels'];samplers=doc['animations'][0]['samplers']
    changed=[]
    for actor in ACTORS:
        nid=names[actor+'_SceneRoot']
        matches=[ch for ch in channels if ch['target']=={'node':nid,'path':'translation'}]
        require(len(matches)==1,'ROOT_CHANNEL:'+actor)
        ch=matches[0];sid=ch['sampler'];sampler=samplers[sid]
        require(sampler.get('interpolation','LINEAR')=='LINEAR','ROOT_INTERPOLATION')
        output=doc['accessors'][sampler['output']];timer=doc['accessors'][sampler['input']]
        require(output['type']=='VEC3' and output['componentType']==5126 and output['count']==72 and timer['count']==72,'ROOT_CHANNEL_FORMAT')
        values=np.asarray(_read_accessor(doc,b,sampler['output']),dtype=np.float64).reshape(72,3)
        new_values=values.copy()
        shifts=np.asarray(schedule['actors'][actor]['proposed_lift_m'],dtype=np.float64)
        new_values[:,1]+=shifts
        require(np.all(np.isfinite(new_values)),'NONFINITE_ROOT')
        index=_accessor(doc,b,new_values.astype('float32').flatten().tolist(),comp_type=5126,shape='VEC3',count=72,add_bounds=True)
        before_idx=sampler['output'];sampler['output']=index
        changed.append({'actor':actor,'root_node':nid,'sampler':sid,'original_accessor':before_idx,'new_accessor':index,'min_lift_m':float(shifts.min()),'max_lift_m':float(shifts.max()),
                        'max_step_m':float(np.max(np.abs(np.diff(shifts))))})
    require(bytes(b[:len(original_bin)])==original_bin,'SOURCE_BINARY_CHANGED')
    require(doc['accessors'][:original_count]==original['accessors'] and doc['bufferViews'][:views_count]==original['bufferViews'],'SOURCE_ACCESSOR_CHANGED')
    for key in ('nodes','skins','meshes','materials','textures','images','samplers','scenes','scene'):
        require(doc.get(key)==original.get(key),'SOURCE_GRAPH_CHANGED:'+key)
    require(doc['animations'][0]['channels']==original['animations'][0]['channels'],'ANIMATION_CHANNELS_CHANGED')
    mod={c['sampler'] for c in channels if c['target']['path']=='translation' and c['target']['node'] in [names[a+'_SceneRoot'] for a in ACTORS]}
    require(len(mod)==2,'ROOT_SAMPLERS')
    for idx,(o,n) in enumerate(zip(original['animations'][0]['samplers'],samplers)):
        if idx not in mod: require(o==n,'UNRELATED_ANIMATION_MUTATION')
    result=_pack_glb(doc,b)
    receipt={'schema':SCHEMA,'source_sha256':SOURCE_SHA256,'derived_sha256':hashlib.sha256(result).hexdigest(),
             'sole_witness_sha256':hashlib.sha256(sole_raw).hexdigest(),'mode':mode,
             'schedule':schedule,'root_channels':changed,'source_original_bin_prefix_preserved':True,
             'original_accessors_preserved':True,'non_root_animations_preserved':True,'rig_material_mesh_preserved':True,
             'root_ik_applied':False,'leg_ik_applied':False,'native_blender_evaluated':False,
             'physical_contact_accepted':False,'natural_gait_accepted':False,'release_approved':False}
    return result,receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('--glb',required=True,type=Path);p.add_argument('--sole',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);p.add_argument('--receipt',required=True,type=Path)
    p.add_argument('--mode',choices=['minimal_envelope','constant_upper_bound'],default='minimal_envelope')
    a=p.parse_args()
    require(len({x.resolve() for x in (a.glb,a.sole,a.out,a.receipt)})==4 and not a.out.exists() and not a.receipt.exists(),'NO_OVERWRITE')
    raw,receipt=derive(a.glb.read_bytes(),a.sole.read_bytes(),a.mode)
    a.out.write_bytes(raw);a.receipt.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'mode':a.mode,'derived_sha256':receipt['derived_sha256'],'source_preserved':True},sort_keys=True))
if __name__=='__main__':main()
