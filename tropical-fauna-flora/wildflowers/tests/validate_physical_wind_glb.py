#!/usr/bin/env python3
"""Independent stdlib validator of serialized opt-in wind-physics GLB.

The oracle reads serialized glTF buffers, not Go data structures. It compares
sampled animation weights to a supplied separate fixed-step dynamics receipt.
No claim of measured botanical physics, realistic plant motion or periodicity.
"""
import argparse, json, math, struct, hashlib, pathlib, sys

class AdmissionError(ValueError): pass

def fail(test): raise AdmissionError(test)

def glb_read(path):
    b=pathlib.Path(path).read_bytes()
    if len(b)<32 or b[:4]!=b'glTF' or struct.unpack_from('<II',b,4)!=(2,len(b)):fail('bad GLB header')
    jlen,jtype=struct.unpack_from('<II',b,12)
    if jtype!=0x4e4f534a or jlen>20_000_000 or 20+jlen+8>len(b):fail('invalid JSON chunk')
    d=json.loads(b[20:20+jlen].decode('utf8'))
    bi=20+jlen
    blen,btype=struct.unpack_from('<II',b,bi)
    if btype!=0x004e4942 or bi+8+blen!=len(b):fail('invalid BIN chunk')
    return d,b[bi+8:]

def accessor_f32(d,b,i):
    a=d['accessors'][i]
    if a['componentType']!=5126 or a['type'] not in ('SCALAR','VEC3'):fail('unsupported accessor type')
    n=1 if a['type']=='SCALAR' else 3
    view=d['bufferViews'][a['bufferView']]
    if view['byteLength']<a['count']*4*n:fail('truncated buffer view')
    start=view.get('byteOffset',0)+a.get('byteOffset',0)
    if start<0 or start+a['count']*n*4>len(b):fail('accessor out of bounds')
    vals=struct.unpack_from('<'+'f'*a['count']*n,b,start)
    if any(not math.isfinite(v) for v in vals):fail('nonfinite accessor')
    return vals

def validate(glb,wind):
    d,b=glb_read(glb)
    r=json.loads(pathlib.Path(wind).read_text())
    s=r['samples']
    if r['model_status']!='synthetic-unmeasured-lumped-mass-drag-not-botanical-physics' or len(s)!=481:fail('unsupported trace evidence')
    mesh=d['meshes'][0]
    ex=mesh.get('extras',{})
    if ex.get('wind_type')!='unmeasured-spring-drag-single-lateral-mode':fail('mislabeled wind mode')
    if ex.get('wind_loop_state')!='not-periodic-and-not-seam-qualified':fail('false seamlessness')
    if ex.get('species_id')!=r['plant_id'] or r['parameters']['plant_id']!=r['plant_id']:fail('species mismatch')
    a=d['animations'][0]
    if a['name']!='wind_physics_one_shot' or a['extras']['loop'] is not False:fail('false loop claim')
    if len(a['channels'])!=1 or a['channels'][0]['target']['path']!='weights':fail('animation channel corrupted')
    sm=a['samplers'][0]
    if sm['interpolation']!='LINEAR':fail('wrong interpolator')
    ts=accessor_f32(d,b,sm['input'])
    weights=accessor_f32(d,b,sm['output'])
    if len(ts)!=49 or len(weights)!=4*len(ts):fail('unexpected encoded clock/weight count')
    if ts[0]!=0 or abs(ts[-1]-r['parameters']['duration_s'])>1e-5:fail('clock mismatch')
    if any(ts[i+1]<=ts[i] for i in range(len(ts)-1)):fail('nonmonotone clocks')
    amplitude=ex['wind_target_amplitude_m']
    if not 0<amplitude<=35 or not math.isfinite(amplitude):fail('invalid target amplitude')
    for i in range(len(ts)):
        src=s[i*10]
        if abs(ts[i]-src['time_s'])>5e-7:fail(f'position in time mismatch {i}')
        x=src['tip_displacement_m']/amplitude
        expected=[max(0,x),max(0,-x),0,0]
        actual=weights[4*i:4*i+4]
        if any(abs(actual[k]-expected[k])>2e-6 for k in range(4)):fail(f'wind-to-GLB mismatch {i}')
        if any(v < -1e-6 or v > 1+1e-6 for v in actual):fail('unbounded physical weights')
    if abs(ts[-1]-ts[0]-r['parameters']['duration_s'])>1e-5:fail('invalid duration')
    # Root anchoring from actual VEC3 POSITION deltas, not a synthetic formula.
    near_ground=0
    for p in mesh['primitives']:
        if len(p['targets'])!=4:fail('wrong morph targets')
        loc=accessor_f32(d,b,p['attributes']['POSITION'])
        delta=accessor_f32(d,b,p['targets'][0]['POSITION'])
        if len(loc)!=len(delta):fail('base vs morph mismatch')
        for j in range(0,len(loc),3):
            if loc[j+1]<=.001:
                near_ground+=1
                if abs(delta[j])>.00008 or abs(delta[j+2])>.00008:fail('ground anchor shifted')
    if near_ground<1:fail('no root anchors')
    return {'schema':'scp.flora.independent-physical-glb.v1','species':r['plant_id'],'status':'physical-sidecar-serialized-match-not-botanically-qualified','sha256_glb':hashlib.sha256(pathlib.Path(glb).read_bytes()).hexdigest(),'sha256_receipt':hashlib.sha256(pathlib.Path(wind).read_bytes()).hexdigest(),'animation_sample_count':len(ts),'near_ground_vertices':near_ground,'max_normalized_weight':max(weights),'loop':False}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--glb',required=True);ap.add_argument('--wind',required=True);ap.add_argument('--out')
    args=ap.parse_args()
    try:
        x=validate(args.glb,args.wind)
        b=json.dumps(x,indent=2)+'\n'
        if args.out:pathlib.Path(args.out).write_text(b)
        else:print(b)
    except (AdmissionError,KeyError,IndexError,TypeError,ValueError,struct.error) as e:
        print('PHYSICAL_GLTF_REJECTED: '+str(e),file=sys.stderr)
        sys.exit(1)
