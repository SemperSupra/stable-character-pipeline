#!/usr/bin/env python3
"""GLB structural inspection only. Does NOT qualify anatomical fidelity."""
import argparse, json, os, struct
from pathlib import Path

def load_glb(path):
    with open(path, 'rb') as f:
        h=f.read(12)
        if len(h)!=12: raise ValueError('short header')
        magic,ver,length=struct.unpack('<4sII',h)
        if magic!=b'glTF' or ver!=2: raise ValueError('not GLB v2')
        if length!=os.fstat(f.fileno()).st_size: raise ValueError('invalid GLB length')
        typ=None; doc=None; pos=12
        while pos<length:
            head=f.read(8)
            if len(head)!=8: raise ValueError('short chunk header')
            size,kind=struct.unpack('<I4s',head)
            if size%4 or pos+8+size>length: raise ValueError('invalid chunk size')
            data=f.read(size)
            if len(data)!=size: raise ValueError('short chunk')
            if pos==12:
                if kind!=b'JSON': raise ValueError('missing JSON chunk')
                doc=json.loads(data.decode('utf-8'))
            elif kind!=b'BIN\x00': raise ValueError('unexpected chunk')
            pos+=8+size
    return doc

def qualify(doc,require_animation=True):
    e=[]; meshes=doc.get('meshes',[]);skins=doc.get('skins',[])
    nodes=doc.get('nodes',[]);acc=doc.get('accessors',[])
    anims=doc.get('animations',[]);n=0;morphs=0;skinprims=0
    for mesh in meshes:
        for p in mesh.get('primitives',[]):
            n+=1;a=p.get('attributes',{});targets=p.get('targets',[])
            morphs=max(morphs,len(targets))
            if not isinstance(a.get('POSITION'),int) or not 0<=a['POSITION']<len(acc):e.append('invalid POSITION')
            if ('JOINTS_0' in a)!=('WEIGHTS_0' in a):e.append('incomplete weights')
            if 'JOINTS_0' in a and 'WEIGHTS_0' in a:
                skinprims+=1
                for k in ('JOINTS_0','WEIGHTS_0'):
                    if not isinstance(a[k],int) or not 0<=a[k]<len(acc):e.append('invalid '+k)
            for target in targets:
                for i in target.values():
                    if not isinstance(i,int) or not 0<=i<len(acc):e.append('invalid morph accessor')
    if not n:e.append('no meshes')
    if not skinprims:e.append('no skinned primitives')
    if not skins:e.append('no skin')
    if not morphs:e.append('no morph')
    for skin in skins:
        js=skin.get('joints',[])
        if not js:e.append('empty skin')
        if any(not isinstance(j,int) or not 0<=j<len(nodes) for j in js):e.append('invalid joint')
        ib=skin.get('inverseBindMatrices')
        if ib is not None and (not isinstance(ib,int) or not 0<=ib<len(acc) or acc[ib].get('count')!=len(js)):
            e.append('invalid inverse bind matrices')
    if require_animation and not anims:e.append('no animation')
    for anim in anims:
        for ch in anim.get('channels',[]):
            t=ch.get('target',{}).get('node');si=ch.get('sampler')
            if not isinstance(t,int) or not 0<=t<len(nodes):e.append('invalid animation node')
            if not isinstance(si,int) or not 0<=si<len(anim.get('samplers',[])):e.append('invalid animation sampler')
    return {'status':'FAIL' if e else 'PASS_STRUCTURAL_ONLY','errors':sorted(set(e)),
            'counts':{'primitives':n,'skins':len(skins),'skinned_primitives':skinprims,
                      'max_morphs':morphs,'animations':len(anims)},
            'NOT_QUALIFIED':['anatomy','face','hands','soft_tissue_physics','render_realism','source_rights']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('glb',type=Path);p.add_argument('--receipt',type=Path);args=p.parse_args()
    try:r=qualify(load_glb(args.glb))
    except Exception as ex:r={'status':'FAIL','errors':[type(ex).__name__+': '+str(ex)]}
    print(json.dumps(r,sort_keys=True,indent=2))
    if args.receipt:args.receipt.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    raise SystemExit(r['status']=='FAIL')
