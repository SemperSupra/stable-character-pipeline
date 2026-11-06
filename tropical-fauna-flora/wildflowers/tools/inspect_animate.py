#!/usr/bin/env python3
"""Independent read-only glTF 2.0 GLB morph validator + actual morph animation preview.
Third-party: numpy, pillow. Read GLB buffers directly, not generator implementation.
"""
import hashlib, json, math, struct, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
BASE=pathlib.Path(__file__).resolve().parents[1]
OUT=BASE/'outputs'
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
    assert len(times)==13 and len(weights)==13 and len(meshes)>=3
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

results=[]; loaded=[]
for name in IDS:
    meta,mesh,doc=load_glb(OUT/(name+'.glb'))
    results.append(meta);loaded.append(mesh)
(OUT/'validation_report.json').write_text(json.dumps({'kind':'independent_binary_glb_morph_check','result':'PASS','species':results,'scope':'Structural/animation contract only; NOT botanical accuracy or validated fluid/elastic physics.'},indent=2)+'\n')

# Rasterize actual morph-applied triangular geometry, same animation channels and weights as GLB.
# Fixed projected framing + depth ordering for a controlled visual contact comparison.
W,H=1024,924
frames=[]
for frame in range(20):
    t=4.0*frame/20.0
    im=Image.new('RGB',(W,H),(231,235,232)); draw=ImageDraw.Draw(im)
    draw.text((24,16),'Four parametric wildflower specimens — actual GLB wind morph targets',fill=(27,46,35))
    draw.text((24,40),f'Wind loop: {t:.2f} / 4.00 s   •   deterministic specimen seeds',fill=(58,83,67))
    for k,(meshes,name) in enumerate(zip(loaded,NAMES)):
        xoff=(k%2)*512;yoff=72+(k//2)*420
        draw.rounded_rectangle((xoff+8,yoff+5,xoff+504,yoff+413),radius=12,fill=(197,211,203))
        draw.text((xoff+18,yoff+12),name,fill=(25,45,35))
        center=xoff+260; floor=yoff+379; scale=500
        drawable=[]
        wa=weights_at(t)
        for mesh in meshes:
            pos=mesh['pos']+np.einsum('k,kij->ij',wa,mesh['morph'])
            xx=center+(pos[:,0]*.84+pos[:,2]*.48)*scale
            yy=floor-(pos[:,1]+pos[:,2]*.13)*scale
            depth=pos[:,2]
            tris=mesh['inds']
            # Fixed face stride; stable sampled faces preserve shapes across frames.
            step=max(1,math.ceil(len(tris)/6500))
            for ids in tris[::step]:
                # skip tiny sub-pixel fragments, but keep many dense flowers
                coords=[(float(xx[v]),float(yy[v])) for v in ids]
                if max(z[0] for z in coords)<xoff+10 or min(z[0] for z in coords)>xoff+502:continue
                drawable.append((float(np.mean(depth[ids])),coords,mesh['color']))
        # painter sort: farther first
        drawable.sort(key=lambda it:-it[0])
        for _,coords,color in drawable:draw.polygon(coords,fill=color)
        draw.line([(xoff+16,floor+3),(xoff+495,floor+3)],fill=(117,133,113),width=2)
    draw.text((24,H-18),'Original synthetic geometry; botanical morphology and elastic physics remain research prototypes.',fill=(54,75,62))
    frames.append(im)
frames[0].save(OUT/'wind_morph_frame_00.png')
frames[0].save(OUT/'wildflowers_wind_preview.gif',save_all=True,append_images=frames[1:],duration=200,loop=0,optimize=True)
print('Validated',len(results),'GLBs; preview GIF frames',len(frames))
for x in results:print(x['id'],x['vertices'],'vertices',x['triangles'],'triangles','root max',x['rooted_morph_max'])
