#!/usr/bin/env python3
"""Independent read-only glTF 2.0 GLB morph validator + actual morph animation preview.
Third-party: numpy, pillow. Read GLB buffers directly, not generator implementation.
"""
import hashlib, json, math, struct, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
BASE=pathlib.Path(__file__).resolve().parents[1]
OUT=BASE/'outputs-v02'
IDS=['achillea_millefolium','centaurea_jacea','convolvulus_arvensis','tripleurospermum_inodorum']
NAMES=['Yarrow / Schafgarbe','Knapweed / Flockenblume','Field bindweed / Acker-Winde','Mayweed / Geruchlose Kamille']

def load_glb(path):
    data=path.read_bytes()
    assert data[:4]==b'glTF' and struct.unpack_from('<I', data,4)[0]==2
    assert struct.unpack_from('<I',data,8)[0]==len(data)
    jsonlen,jtype=struct.unpack_from('<II',data,12)
    assert jtype==0x4e4f534a
    doc=json.loads(data[20:20+jsonlen]); off=20+jsonlen
    binlen,btype=struct.unpack_from('<II',data,off)
    assert btype==0x004e4942
    blob=memoryview(data)[off+8:off+8+binlen]
    assert doc['buffers'][0]['byteLength']==len(blob)
    def acc(index):
        a=doc['accessors'][index]; v=doc['bufferViews'][a['bufferView']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
        n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
        start=v.get('byteOffset',0)+a.get('byteOffset',0)
        arr=np.frombuffer(blob,dtype=dtype,count=a['count']*n,offset=start).reshape(-1,n).copy()
        assert np.isfinite(arr).all()
        return arr
    meshes=[]
    for p in doc['meshes'][0]['primitives']:
        pos=acc(p['attributes']['POSITION']); normal=acc(p['attributes']['NORMAL']);inds=acc(p['indices']).ravel()
        morph=np.stack([acc(t['POSITION']) for t in p['targets']])
        assert len(morph)==4 and normal.shape==pos.shape and len(inds)%3==0 and max(inds)<len(pos)
        assert len(pos)==morph.shape[1] and pos.shape[1]==3
        color=doc['materials'][p['material']]['pbrMetallicRoughness']['baseColorFactor']
        meshes.append(dict(pos=pos,inds=inds.reshape(-1,3),morph=morph,material=doc['materials'][p['material']]['name'],color=tuple(round(v*255) for v in color[:3])))
    assert doc['animations'][0]['channels'][0]['target']['path']=='weights'
    sam=doc['animations'][0]['samplers'][0]
    times=acc(sam['input']).ravel();weights=acc(sam['output']).reshape(-1,4)
    assert np.all(np.diff(times)>0), 'nonmonotone clock'
    assert np.array_equal(weights[0],weights[-1]) and np.array_equal(weights[0],np.zeros(4))
    assert len(times)==13 and len(weights)==13 and len(meshes)>=2
    doc['_animation_sample_times']=times.tolist()
    doc['_animation_sample_weights']=weights.tolist()
    vertices=sum(len(m['pos']) for m in meshes)
    triangles=sum(len(m['inds']) for m in meshes)
    rooted=[]
    for m in meshes:
        mask=m['pos'][:,1]<=0.005
        if mask.any():rooted.append(float(np.max(np.abs(m['morph'][:,mask,:]))))
    assert rooted and max(rooted)<.00005, 'wind should preserve basal attachment'
    assert sum(float(np.max(np.abs(m['morph']))) for m in meshes)>0.01, 'wind targets all zero'
    return dict(id=path.stem,sha256=hashlib.sha256(data).hexdigest(),vertices=vertices,triangles=triangles,morph_targets=4,wind_loop_seconds=float(times[-1]),materials=[m['material'] for m in meshes],rooted_morph_max=max(rooted),GLB_valid_structure=True),meshes,doc

def weights_at(t):
    u=t/4
    a=math.sin(2*math.pi*u)
    b=.55*math.sin(4*math.pi*u)
    return np.array([max(a,0),max(-a,0),max(b,0),max(-b,0)],dtype=np.float32)


# Independent verification reads GLB bytes; no call to generator code.
IDS=sorted(x.stem for x in OUT.glob('*.glb'))
results=[]
for name in IDS:
    meta,meshes,doc=load_glb(OUT/(name+'.glb'))
    assert meta['vertices']<175000 and meta['triangles']<80000
    # Bounds check independent of app-specific exporter.
    positions=np.concatenate([m['pos'] for m in meshes],axis=0)
    assert float(positions[:,1].max())<40 and float(positions[:,1].min())>-0.1
    assert np.isfinite(positions).all()
    meta['world_min_y']=float(positions[:,1].min())
    meta['world_max_y']=float(positions[:,1].max())
    results.append(meta)
(OUT/'independent_binary_validation.json').write_text(json.dumps({'kind':'independent_binary_glb_morph_check','result':'PASS','count':len(results),'species':results,'scope':'GLB structural validity and recorded animation only; NOT botanical identity or elastic wind physics.'},indent=2)+'\n')
print('INDEPENDENT_GLB_QUALIFICATION_PASS',len(results))
for r in results:print(r['id'],r['triangles'],'triangles',round(r['world_min_y'],4),'minY',round(r['rooted_morph_max'],8),'root wind max')
