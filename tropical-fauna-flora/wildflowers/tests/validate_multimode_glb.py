#!/usr/bin/env python3
"""Independent stdlib binary GLB witness for source-original experimental 3-mode wind.

Not a botanical, leaf mechanics, environmental or Blender pixel validator.
"""
import argparse, hashlib, json, math, pathlib, struct, sys

class Reject(ValueError):
    pass

def check(condition, message):
    if not condition:
        raise Reject(message)

def read_glb(path):
    data = pathlib.Path(path).read_bytes()
    check(len(data) >= 32 and data[:4] == b'glTF', 'invalid header')
    version,length=struct.unpack_from('<II',data,4)
    check(version == 2 and length == len(data), 'invalid GLB length/version')
    jlen,jtype=struct.unpack_from('<II',data,12)
    check(0 < jlen <= 20_000_000 and jtype == 0x4e4f534a and jlen+28 <= len(data),'invalid JSON chunk')
    doc=json.loads(data[20:20+jlen].decode('utf-8'))
    blen,btype=struct.unpack_from('<II',data,20+jlen)
    check(btype == 0x004e4942 and 28+jlen+blen == len(data),'invalid binary chunk')
    return doc,data[28+jlen:],hashlib.sha256(data).hexdigest()

def accessor(doc, binary, idx):
    a=doc['accessors'][idx]
    check(a['componentType']==5126 and a['type'] in ('SCALAR','VEC3'),'unsupported accessor')
    n=3 if a['type']=='VEC3' else 1
    v=doc['bufferViews'][a['bufferView']]
    size=a['count']*n*4
    start=v.get('byteOffset',0)+a.get('byteOffset',0)
    check(0 <= start and start+size<=len(binary) and a.get('byteOffset',0)+size<=v['byteLength'],'accessor bounds')
    values=struct.unpack_from('<'+'f'*(a['count']*n),binary,start)
    check(all(math.isfinite(x) for x in values),'nonfinite accessor')
    return values

def verify(glb, receipt):
    d, raw, glb_sha = read_glb(glb)
    r=json.loads(pathlib.Path(receipt).read_text())
    check(r.get('schema')=='scp.flora.synthetic-three-mode.v1','unqualified multiwind source')
    ex=d['meshes'][0].get('extras',{})
    a=d['animations'][0]
    check(ex.get('wind_type')=='synthetic-independent-2axis-tip-and-one-foliage-mode','unexpected wind model')
    check(ex.get('species_id')==r.get('plant_id'),'species mismatch')
    check(ex.get('wind_loop_state')=='nonperiodic-not-seam-qualified','false seamlessness')
    check(a['name']=='wind_multimode_one_shot' and a.get('extras',{}).get('loop') is False,'unexpected looping/animation')
    check(a['channels'][0]['target']['path']=='weights' and len(a['channels'])==1,'animation channel')
    sm=a['samplers'][0]
    check(sm.get('interpolation')=='LINEAR','interpolation')
    ts=accessor(d,raw,sm['input'])
    weights=accessor(d,raw,sm['output'])
    check(len(ts)==49 and len(weights)==6*49,'clock or weight count')
    amp=ex['wind_target_amplitudes_m']
    check(len(amp)==3 and all(isinstance(x,(float,int)) and 0<x<=35 and math.isfinite(x) for x in amp),'amplitudes')
    check(len(d['meshes'][0]['weights'])==6,'default weights count')
    series=[r['x'],r['z'],r['leaf']]
    for s in series:
        check(s.get('model_status')=='synthetic-unmeasured-lumped-mass-drag-not-botanical-physics','source model status')
        check(s['plant_id']==r['plant_id'] and s['parameters']['plant_id']==r['plant_id'],'source identity')
        check(len(s['samples'])==481,'source sample count')
    check(abs(ts[0])<1e-8 and abs(ts[-1]-4.)<1e-5,'clock endpoints')
    check(all(ts[i+1]>ts[i] for i in range(48)),'nonmonotonic times')
    max_errors=[0,0,0]
    for i,t in enumerate(ts):
        ws=weights[6*i:6*(i+1)]
        check(all(-1e-6<=w<=1+1e-6 for w in ws),'out of range weight')
        for j,s in enumerate(series):
            sample=s['samples'][i*10]
            check(abs(t-sample['time_s'])<5e-7,f'source clock divergence {i}:{j}')
            x=sample['tip_displacement_m']/amp[j]
            target=(max(0,x),max(0,-x))
            e=max(abs(ws[2*j+k]-target[k]) for k in (0,1))
            max_errors[j]=max(max_errors[j],e)
            check(e<2e-6,f'source motion mismatch {i}:{j}')
            check(ws[2*j]*ws[2*j+1]<1e-8,'positive-negative overlap')
    leaf_moved=False
    rooted=0
    leaf_vertices=0
    for prim in d['meshes'][0]['primitives']:
        check(len(prim['targets'])==6,'missing morph targets')
        material=d['materials'][prim['material']]['name']
        positions=accessor(d,raw,prim['attributes']['POSITION'])
        deltas=[accessor(d,raw,tr['POSITION']) for tr in prim['targets']]
        check(all(len(delta)==len(positions) for delta in deltas),'morph target size')
        for k in range(0,len(positions),3):
            if positions[k+1]<=.001:
                rooted+=1
                check(all(abs(deltas[j][k+c])<8e-5 for j in range(6) for c in (0,2)),'unanchored ground X/Z')
                check(all(abs(deltas[j][k+1])<8e-5 for j in (4,5)),'unanchored leaf Y')
            if material != 'leaf':
                check(all(abs(deltas[j][k+c])<1e-8 for j in (4,5) for c in (0,1,2)),'leaf flutter leaked into nonleaf geometry')
            else:
                leaf_vertices+=1
                for c in (0,1,2):
                    check(abs(deltas[4][k+c]+deltas[5][k+c])<2e-7,'leaf sign symmetry')
                if abs(deltas[4][k+1])>1e-5:leaf_moved=True
    check(rooted>0 and leaf_vertices>0 and leaf_moved,'no actual rooted leaf flutter')
    return dict(schema='scp.flora.wind-multimode-independent-v1',plant_id=r['plant_id'],status='source-bound-animation-match-not-botanical-physics',glb_sha256=glb_sha,receipt_sha256=hashlib.sha256(pathlib.Path(receipt).read_bytes()).hexdigest(),keyframes=49,morph_targets=6,rooted_vertices=rooted,leaf_vertices=leaf_vertices,max_error_per_mode=max_errors,loop=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--glb',required=True)
    parser.add_argument('--wind',required=True)
    parser.add_argument('--out')
    args=parser.parse_args()
    try:
        result=verify(args.glb,args.wind)
    except (Reject,KeyError,IndexError,TypeError,ValueError,struct.error) as exc:
        print('MULTIMODE_GLTF_REJECTED: '+str(exc),file=sys.stderr)
        sys.exit(1)
    output=json.dumps(result,indent=2)+'\n'
    if args.out:pathlib.Path(args.out).write_text(output)
    else:print(output)
