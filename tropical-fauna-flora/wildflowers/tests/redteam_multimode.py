#!/usr/bin/env python3
"""Five local negative controls against a real serialized W07 GLB.

No alteration to production source or reference baseline is permitted.
"""
import argparse,copy,json,pathlib,struct,tempfile,sys
from validate_multimode_glb import verify,read_glb,Reject

def write_glb(path,doc,binary):
    raw=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    raw+=b' '*((-len(raw))%4)
    data=b'glTF'+struct.pack('<II',2,12+8+len(raw)+8+len(binary))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary
    pathlib.Path(path).write_bytes(data)

def must_reject(glb,wind):
    try:verify(glb,wind)
    except (Reject,ValueError,TypeError,KeyError,IndexError,struct.error):return True
    return False

def main(glb,wind):
    doc,bin0,_=read_glb(glb)
    original=json.loads(pathlib.Path(wind).read_text())
    with tempfile.TemporaryDirectory() as td:
        g=pathlib.Path(td)/'bad.glb';r=pathlib.Path(td)/'bad.wind.json'
        results={}
        changed=copy.deepcopy(original);changed['z']['samples'][10]['tip_displacement_m']+=.05
        r.write_text(json.dumps(changed));results['source_z_tamper']=must_reject(glb,r)
        changed=copy.deepcopy(original);changed['plant_id']='foreign'
        r.write_text(json.dumps(changed));results['species_swap']=must_reject(glb,r)
        r.write_text(json.dumps(original))
        d=copy.deepcopy(doc);d['animations'][0]['extras']['loop']=True
        write_glb(g,d,bin0);results['false_loop_claim']=must_reject(g,wind)
        d=copy.deepcopy(doc);b=bytearray(bin0)
        accessor=d['accessors'][d['animations'][0]['samplers'][0]['output']]
        view=d['bufferViews'][accessor['bufferView']]
        offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)+4*(6*20+2)
        x=struct.unpack_from('<f',b,offset)[0]
        struct.pack_into('<f',b,offset,x+.2)
        write_glb(g,d,bytes(b));results['z_animation_tamper']=must_reject(g,wind)
        d=copy.deepcopy(doc);b=bytearray(bin0)
        leaf=next(p for p in d['meshes'][0]['primitives'] if d['materials'][p['material']]['name']=='leaf')
        v=d['bufferViews'][d['accessors'][leaf['targets'][4]['POSITION']]['bufferView']]
        offset=v.get('byteOffset',0)
        struct.pack_into('<f',b,offset,float('nan'))
        write_glb(g,d,bytes(b));results['nonfinite_leaf_morph']=must_reject(g,wind)
    if not all(results.values()):raise RuntimeError('adversarial validator failure '+str(results))
    return {'schema':'scp.flora.multimode-redteam.v1','tests':results,'passed':len(results)}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--glb',required=True);a.add_argument('--wind',required=True);a.add_argument('--out');p=a.parse_args()
    result=main(p.glb,p.wind);text=json.dumps(result,indent=2)+'\n'
    if p.out:pathlib.Path(p.out).write_text(text)
    else:print(text)
