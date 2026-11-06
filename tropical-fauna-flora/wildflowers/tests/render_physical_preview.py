#!/usr/bin/env python3
"""Optional flat-color software preview from *actual* serialized GLB morph weights.
Pillow/NumPy are visualization-only dependencies, not deployed Go dependencies.
This is not Blender, measured physics, or botanical realism qualification.
"""
from pathlib import Path
import argparse, json, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont

LABELS={'triticum_aestivum':'Wheat / Weizen','zea_mays':'Maize / Mais','helianthus_annuus':'Sunflower / Sonnenblume','phyllostachys_aurea':'Bamboo / Bambus'}

def load(path):
 b=path.read_bytes(); jlen=struct.unpack_from('<I',b,12)[0];d=json.loads(b[20:20+jlen]);bo=20+jlen+8
 def acc(idx):
  a=d['accessors'][idx];v=d['bufferViews'][a['bufferView']];n={'SCALAR':1,'VEC3':3}[a['type']]
  dt={5126:'<f4',5125:'<u4'}[a['componentType']]
  return np.frombuffer(b,dtype=dt,count=a['count']*n,offset=bo+v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,n).copy()
 meshes=[]
 for p in d['meshes'][0]['primitives']:
  mat=d['materials'][p['material']]['pbrMetallicRoughness']['baseColorFactor']
  meshes.append((acc(p['attributes']['POSITION']),np.stack([acc(t['POSITION']) for t in p['targets']]),acc(p['indices']).ravel().reshape(-1,3),tuple(int(round(255*q)) for q in mat[:3])))
 sm=d['animations'][0]['samplers'][0]
 return meshes,acc(sm['input']).ravel(),acc(sm['output']).reshape(-1,4)

def panel(id,model,t,width=390,height=345):
 meshes,times,weights=model
 w=np.array([np.interp(t,times,weights[:,k]) for k in range(4)],dtype=np.float32)
 raw=[]
 for base,morph,idx,color in meshes:
  points=base+np.einsum('k,kij->ij',w,morph)
  x=points[:,0]*.85+points[:,2]*.52
  y=points[:,1]+points[:,2]*.12
  z=-points[:,0]*.52+points[:,2]*.85
  raw.append((x,y,z,idx,color))
 xmin=min(float(x.min()) for x,y,z,idx,color in raw);xmax=max(float(x.max()) for x,y,z,idx,color in raw)
 ymin=min(float(y.min()) for x,y,z,idx,color in raw);ymax=max(float(y.max()) for x,y,z,idx,color in raw)
 scale=min((width-55)/max(.01,xmax-xmin),(height-90)/max(.01,ymax-ymin))
 center=(xmin+xmax)/2; baseline=height-22
 im=Image.new('RGB',(width,height),(236,242,235));dr=ImageDraw.Draw(im)
 dr.text((15,12),LABELS[id],fill=(30,48,33))
 dr.text((15,30),f'{t:.2f}s | GLB-decoded 1-DOF motion',fill=(80,92,82))
 poly=[]
 for x,y,z,idx,color in raw:
  xs=((x-center)*scale+width/2).astype(int)
  ys=((ymin-y)*scale+baseline).astype(int)
  for tri in idx:
   if (xs[tri].max()-xs[tri].min())+(ys[tri].max()-ys[tri].min())<2:continue
   poly.append((float(z[tri].mean()),[(int(xs[i]),int(ys[i])) for i in tri],color))
 poly.sort(key=lambda o:-o[0])
 for _,coords,col in poly:dr.polygon(coords,fill=col)
 dr.line((12,baseline+2,width-12,baseline+2),fill=(110,134,117),width=2)
 return im

def render(root,out):
 models={id:load(root/(id+'.physical.glb')) for id in LABELS}
 frames=[]
 for k in range(16):
  t=4*k/16
  im=Image.new('RGB',(780,690),(246,250,247))
  for i,id in enumerate(LABELS):im.paste(panel(id,models[id],t),((i%2)*390,(i//2)*345))
  frames.append(im)
 frames[0].save(out,save_all=True,append_images=frames[1:],duration=250,loop=0,optimize=False)
 return {'frames':len(frames),'species':list(LABELS),'source':'serialized physical GLB 49-frame weights, linearly interpolated; no separate sine animation'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 print(json.dumps(render(a.input,a.out),indent=2))
