#!/usr/bin/env python3
"""Source-bound zero-area triangle repair of provisional Aster/Juniper sculpt GLBs.

Only glTF index accessors for each actor's body primitive are redirected.
No source binary changes, no bone/animation/face acceptance is asserted.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from sculpt_human_v1 import _unpack_glb, _read_accessor
from costume_garment_v1 import _accessor, _pack_glb

ACTORS=('AsterOriginal','JuniperOriginal')
SCHEMA='scp.r009.original_human.triangle_repair.v1'

class RepairError(ValueError): pass

def repair(raw,expected_sha256):
    if not isinstance(expected_sha256,str) or len(expected_sha256)!=64 or hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise RepairError('SOURCE_SHA256_MISMATCH')
    d,buf=_unpack_glb(raw)
    if d.get('extras',{}).get('source_class')!='ORIGINAL_SELF_AUTHORED_SYNTHETIC' or 'source_original_sculpt_v1' not in d.get('extras',{}):
        raise RepairError('NOT_ADMITTED_ORIGINAL_SCULPT')
    if len(d.get('skins',[]))!=2 or any(len(s['joints'])!=35 for s in d['skins']):
        raise RepairError('SKIN_MISMATCH')
    names={n.get('name'):n for n in d['nodes']}
    rows={}
    for a in ACTORS:
        node=names.get(a+'_Wardrobe_body')
        if not node:raise RepairError('BODY_MISSING')
        prim=d['meshes'][node['mesh']]['primitives'][0]
        p=_read_accessor(d,buf,prim['attributes']['POSITION'])
        ix=_read_accessor(d,buf,prim['indices'])
        if len(ix)%3 or len(p)%3:raise RepairError('INVALID_MESH_ARITY')
        keep=[];drop=0;degenerate_other=0
        for i in range(0,len(ix),3):
            a0,b,c=ix[i:i+3]
            if min(a0,b,c)<0 or max(a0,b,c)>=len(p)//3:
                raise RepairError('INDEX_OUT_OF_RANGE')
            if len({a0,b,c})<3:drop+=1;continue
            ax,ay,az=p[3*a0:3*a0+3];bx,by,bz=p[3*b:3*b+3];cx,cy,cz=p[3*c:3*c+3]
            u=(bx-ax,by-ay,bz-az);v=(cx-ax,cy-ay,cz-az)
            area2=sum(q*q for q in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]))
            if not math.isfinite(area2):raise RepairError('NONFINITE_TRIANGLE')
            if area2<=1e-22:drop+=1
            else:keep.extend((a0,b,c))
        if drop>200 or len(keep)<12000:
            raise RepairError('REPAIR_BUDGET_EXCEEDED')
        prim['indices']=_accessor(d,buf,keep,comp_type=5125,shape='SCALAR',count=len(keep))
        rows[a]={'source_triangles':len(ix)//3,'retained_triangles':len(keep)//3,
                 'removed_zero_area_triangles':drop,'source_bytes_immutable':True}
    d['extras']['sculpt_triangle_repair_v1']={'schema':SCHEMA,'source_sha256':expected_sha256,
        'actors':rows,'human_anatomy_accepted':False,'mesh_continuity_accepted':False,
        'cloth_collision_qualified':False,'release_approved':False}
    return _pack_glb(d,buf),d['extras']['sculpt_triangle_repair_v1']

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--receipt',required=True,type=Path)
    a=p.parse_args()
    if len({a.input.resolve(),a.out.resolve(),a.receipt.resolve()})<3 or a.out.exists() or a.receipt.exists():
        raise RepairError('NO_OVERWRITE')
    final,r=repair(a.input.read_bytes(),a.expected_sha256)
    a.out.write_bytes(final)
    a.receipt.write_text(json.dumps({'output_sha256':hashlib.sha256(final).hexdigest(),**r},sort_keys=True,indent=2)+'\n')
    print(json.dumps({'output_sha256':hashlib.sha256(final).hexdigest(),'removed':{k:v['removed_zero_area_triangles'] for k,v in r['actors'].items()}},sort_keys=True))

if __name__=='__main__':main()
