#!/usr/bin/env python3
"""Contact sheet from independent glTF parser, not generated render claims.
CPU silhouette/painter preview only (unlit flat colors, no texture/lighting/physics)."""
from pathlib import Path
import sys,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).parent))
from validate_extended import load_glb,OUT,weights_at
NAMES={
 'festuca_pratensis':'Meadow fescue / Gras', 'triticum_aestivum':'Wheat / Weizen',
 'avena_sativa':'Oats / Hafer','zea_mays':'Corn / Mais',
 'helianthus_annuus':'Sunflower / Sonnenblume','vitis_vinifera':'Grapevine / Weinrebe',
 'phyllostachys_aurea':'Bamboo / Bambus','corylus_avellana':'Hazel shrub / Hasel',
 'quercus_robur':'Oak / Eiche','picea_abies':'Spruce / Fichte',
 'secale_cereale':'Rye / Roggen','malus_domestica':'Apple tree / Apfelbaum',
}
ORDER=list(NAMES)
def font(size):
 for name in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']:
  if Path(name).exists():return ImageFont.truetype(name,size)
 return ImageFont.load_default()
F1,F2=font(19),font(13)

def panel(name,w=420,h=400,t=0):
 meta,meshes,doc=load_glb(OUT/(name+'.glb'))
 img=Image.new('RGB',(w,h),(241,244,240));d=ImageDraw.Draw(img)
 d.rounded_rectangle((6,6,w-6,h-6),radius=15,fill=(224,234,226))
 d.text((20,14),NAMES[name],fill=(22,46,34),font=F1)
 d.text((20,42),name+'   •   '+f"{meta['triangles']:,} triangles",fill=(64,82,69),font=F2)
 weights=np.array([np.interp(t,doc['_animation_sample_times'],[w[k] for w in doc['_animation_sample_weights']]) for k in range(4)],dtype=np.float32)
 points=[]
 for mesh in meshes:
  p=mesh['pos']+np.einsum('k,kij->ij',weights,mesh['morph'])
  # horizontal camera yaw: +X and +Z visible; depth from -X + Z
  x=p[:,0]*.84+p[:,2]*.53
  y=p[:,1]+p[:,2]*.14
  dep=-p[:,0]*.53+p[:,2]*.84
  points.append((x,y,dep,mesh))
 xmin=min(float(p[0].min()) for p in points);xmax=max(float(p[0].max()) for p in points)
 ymin=min(float(p[1].min()) for p in points);ymax=max(float(p[1].max()) for p in points)
 dx=max(0.001,xmax-xmin);dy=max(0.001,ymax-ymin)
 scale=min((w-55)/dx,(h-112)/dy)
 xcenter=(xmin+xmax)/2
 ybottom=ymin
 baseline=h-24
 polys=[]
 for xx,yy,dep,mesh in points:
  xp=((xx-xcenter)*scale+w/2).astype(int)
  yp=((ybottom-yy)*scale+baseline).astype(int)
  tris=mesh['inds']
  # Small faces may be subpixel. Skip only such faces, not random samples.
  xtri=xp[tris];ytri=yp[tris]
  draw_mask=((xtri.max(axis=1)-xtri.min(axis=1))+(ytri.max(axis=1)-ytri.min(axis=1)))>=2
  for ids in tris[draw_mask]:
   coords=[(int(xp[z]),int(yp[z])) for z in ids]
   polys.append((float(dep[ids].mean()),coords,mesh['color']))
 polys.sort(key=lambda z:-z[0]);
 for _,xy,color in polys:d.polygon(xy,fill=color)
 d.line((20,baseline+2,w-20,baseline+2),fill=(116,136,120),width=2)
 d.text((20,h-18),'Synthetic v0.2 · flat-shaded preview, not botanical validation',fill=(66,79,65),font=font(10))
 return img

if __name__=='__main__':
 out=Image.new('RGB',(4*420,3*400),(250,251,248))
 for i,name in enumerate(ORDER):
  tile=panel(name)
  out.paste(tile,((i%4)*420,(i//4)*400))
 out.save(OUT/'expanded_plant_contact_sheet.png')
 print('SAVED',OUT/'expanded_plant_contact_sheet.png')
 # Four species exposed over time: rendered from actual GLB morph targets.
 ids=['triticum_aestivum','zea_mays','helianthus_annuus','phyllostachys_aurea']
 frames=[]
 for frame in range(16):
  im=Image.new('RGB',(840,800),(242,246,243))
  for i,name in enumerate(ids):im.paste(panel(name,420,400,frame*.25),((i%2)*420,(i//2)*400))
  frames.append(im)
 frames[0].save(OUT/'expanded_wind_from_glb.gif',save_all=True,append_images=frames[1:],duration=250,loop=0,optimize=True)
 print('SAVED',OUT/'expanded_wind_from_glb.gif')
