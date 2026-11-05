#!/usr/bin/env python3
"""Independent actual GLB weighted-skin renderer, two cameras and per-frame sole witness.

Actual GLB mesh vertices are deformed by full glTF skin matrices, with no reliance on
controller's claims of foot contact. All video frames are rendered and decoded/ffprobed.
"""
import argparse,hashlib,json,math,os,struct,subprocess,sys,time
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from PIL import Image,ImageDraw
import vtkmodules.vtkRenderingOpenGL2  # critical VTK/EGL provider registration
import vtk
from vtk.util.numpy_support import numpy_to_vtk,vtk_to_numpy
from gait_v2 import decode_glb,frame_pose,FPS,FRAMES,D

COMP={5121:np.uint8,5123:np.uint16,5125:np.uint32,5126:np.float32}
SIZE={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}

class RenderModel:
 def __init__(self,path):
  self.path=Path(path);raw=self.path.read_bytes();self.sha=hashlib.sha256(raw).hexdigest()
  self.d,self.buf=decode_glb(raw)
  self.nodes=self.d['nodes'];self.parents={}
  for i,n in enumerate(self.nodes):
   for c in n.get('children',[]):self.parents[c]=i
  self.anim_channels={}
  for ch in self.d['animations'][0]['channels']:
   key=(ch['target']['node'],ch['target']['path'])
   self.anim_channels[key]=self.d['animations'][0]['samplers'][ch['sampler']]
  self.parts=[]
  for i,node in enumerate(self.nodes):
   if 'mesh' not in node:continue
   skin=self.d['skins'][node['skin']];ids=skin['joints']
   mats=self.acc(skin['inverseBindMatrices']).reshape((-1,4,4)).transpose((0,2,1))
   for pi,pr in enumerate(self.d['meshes'][node['mesh']]['primitives']):
    a=pr['attributes'];xyz=self.acc(a['POSITION']).astype(np.float64)
    jj=self.acc(a['JOINTS_0']).astype(np.int32)
    ww=self.acc(a['WEIGHTS_0']).astype(np.float64)
    idx=self.acc(pr['indices']).astype(np.int64).reshape((-1,3))
    matidx=pr['material'];mat=self.d['materials'][matidx]
    rgba=mat['pbrMetallicRoughness']['baseColorFactor']
    p={'node':i,'actor':0 if i<19 else 1,'vertices':xyz,'joints':jj,'weights':ww,'idx':idx,
       'mat_name':mat['name'],'rgba':rgba,'idxmat':matidx,'ids':ids,'ibm':mats,
       'verts_h':np.c_[xyz,np.ones(len(xyz))]}
    self.parts.append(p)
  self.parts_by_actor=[[p for p in self.parts if p['actor']==a] for a in range(2)]
  self.bootparts=[(p,side) for p in self.parts for side in ('L','R') if p['mat_name'] in ('darkBoots','earthBoots')]
 def acc(self,i):
  a=self.d['accessors'][i];v=self.d['bufferViews'][a['bufferView']];comp=COMP[a['componentType']]
  count=SIZE[a['type']];byte=int(v.get('byteOffset',0)+a.get('byteOffset',0))
  arr=np.ndarray((a['count'],count),dtype=np.dtype(comp).newbyteorder('<'),
        buffer=self.buf,offset=byte,strides=(v.get('byteStride',np.dtype(comp).itemsize*count),np.dtype(comp).itemsize)).copy()
  if a['type']=='MAT4':return arr
  return arr.flatten() if count==1 else arr
 def world_mats(self,frame):
  t=[np.array(n.get('translation',[0,0,0]),dtype=float) for n in self.nodes]
  r=[np.array(n.get('rotation',[0,0,0,1]),dtype=float) for n in self.nodes]
  s=[np.array(n.get('scale',[1,1,1]),dtype=float) for n in self.nodes]
  for (ni,k),sp in self.anim_channels.items():
   values=self.acc(sp['output']);kframe=frame # exactly authored 72 ticks
   if k=='rotation':r[ni]=values[kframe]
   elif k=='translation':t[ni]=values[kframe]
   elif k=='scale':s[ni]=values[kframe]
  local=[]
  for i,n in enumerate(self.nodes):
   if 'matrix' in n:m=np.array(n['matrix']).reshape((4,4),order='F')
   else:
    m=np.eye(4);m[:3,:3]=Rotation.from_quat(r[i]).as_matrix() @ np.diag(s[i]);m[:3,3]=t[i]
   local.append(m)
  world=[None]*len(local)
  def rec(i):
   if world[i] is None:world[i]=rec(self.parents[i])@local[i] if i in self.parents else local[i]
   return world[i]
  for i in range(len(local)):rec(i)
  return world
 def skin_frame(self,frame):
  world=self.world_mats(frame)
  out=[]
  for p in self.parts:
   bmats=np.stack([world[j]@m for j,m in zip(p['ids'],p['ibm'])])
   points=np.zeros((len(p['vertices']),4),dtype=np.float64)
   for k in range(4):
    ww=p['weights'][:,k,None]
    if not np.any(ww):continue
    points+=np.einsum('nij,nj->ni',bmats[p['joints'][:,k]],p['verts_h'])*ww
   points=points[:,:3]/np.maximum(points[:,3,None],1e-9)
   out.append(points.astype(np.float32))
  return world,out


def v_actor(poly,color):
 mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(poly)
 actor=vtk.vtkActor();actor.SetMapper(mapper)
 actor.GetProperty().SetColor(*color);actor.GetProperty().SetAmbient(.35)
 actor.GetProperty().SetDiffuse(.7);actor.GetProperty().SetSpecular(.1)
 return actor

def cube(x,y,z,sx,sy,sz,color,ren):
 c=vtk.vtkCubeSource();c.SetXLength(sx);c.SetYLength(sy);c.SetZLength(sz);c.SetCenter(x,y,z)
 map_=vtk.vtkPolyDataMapper();map_.SetInputConnection(c.GetOutputPort());a=vtk.vtkActor();a.SetMapper(map_);a.GetProperty().SetColor(*color);a.GetProperty().SetAmbient(.45);ren.AddActor(a)

def sphere(x,y,z,rx,ry,rz,color,ren):
 s=vtk.vtkSphereSource();s.SetThetaResolution(10);s.SetPhiResolution(8)
 map_=vtk.vtkPolyDataMapper();map_.SetInputConnection(s.GetOutputPort());a=vtk.vtkActor();a.SetMapper(map_);a.SetPosition(x,y,z);a.SetScale(rx,ry,rz);a.GetProperty().SetColor(*color);a.GetProperty().SetAmbient(.5);ren.AddActor(a)

def make_renderer(model,view,W,H,diagnostic=False):
 w=vtk.vtkRenderWindow();w.SetOffScreenRendering(1);w.SetSize(W,H);w.SetMultiSamples(0)
 ren=vtk.vtkRenderer();w.AddRenderer(ren);ren.SetBackground(.79,.84,.87)
 ren.GradientBackgroundOn();ren.SetBackground2(.94,.97,.98)
 cube(0,-.13,0,13,.23,8,(.22,.39,.25),ren)
 cube(0,-.005,0,11.1,.025,1.55,(.56,.50,.42),ren)
 # tree row behind model, not an occluder
 for x,z in ([] if view.endswith('close') else [(-4.7,-2.8),(-3.0,-3.0),(-.6,-3.1),(2.5,-3.1),(4.7,-2.9)]):
  cube(x,.68,z,.12,1.4,.12,(.36,.24,.14),ren)
  sphere(x,1.60,z,.56,.60,.56,(.20,.42,.27),ren)
  sphere(x+.25,1.75,z-.12,.37,.40,.37,(.23,.47,.29),ren)
 # source glTF meshes: stable VTK topology + independently updated weighted vertices
 actors=[]
 for p in model.parts:
  poly=vtk.vtkPolyData();v=vtk.vtkPoints();v.SetData(numpy_to_vtk(p['vertices'].astype(np.float32),deep=True));poly.SetPoints(v)
  cells=vtk.vtkCellArray();flat=np.c_[np.full(len(p['idx']),3,dtype=np.int64),p['idx']].astype(np.int64)
  cells.SetCells(len(p['idx']),numpy_to_vtk(flat.flatten(),deep=True,array_type=vtk.VTK_ID_TYPE))
  poly.SetPolys(cells)
  act=v_actor(poly,p['rgba'][:3]);ren.AddActor(act)
  actors.append((p,poly,act))
 # lights and camera
 lt=vtk.vtkLight();lt.SetPosition(-2,9,9);lt.SetFocalPoint(0,1,0);lt.SetIntensity(.8);ren.AddLight(lt)
 cam=ren.GetActiveCamera();cam.ParallelProjectionOn();cam.SetViewUp(0,1,0)
 if view=='side':cam.SetPosition(0,2.1,12);cam.SetFocalPoint(0,.87,0);cam.SetParallelScale(2.15)
 elif view=='oblique':cam.SetPosition(6.8,3.4,9.3);cam.SetFocalPoint(0,.92,0);cam.SetParallelScale(2.25)
 else:cam.SetPosition(0,1.0,9.);cam.SetFocalPoint(0,.94,0);cam.SetParallelScale(1.09)
 ren.ResetCameraClippingRange()
 font=vtk.vtkTextActor();font.SetInput('GAIT V2 | HIP + KNEE + ANKLE | OPPOSITE-ARM SWING | RESEARCH ONLY')
 font.GetTextProperty().SetFontSize(14);font.GetTextProperty().SetColor(.14,.20,.24);font.SetPosition(18,H-28);ren.AddActor2D(font)
 clock=vtk.vtkTextActor();clock.GetTextProperty().SetFontSize(15);clock.GetTextProperty().SetColor(.20,.27,.35);clock.SetPosition(18,18);ren.AddActor2D(clock)
 return w,ren,actors,clock

def capture(w,W,H):
 w.Render();grab=vtk.vtkWindowToImageFilter();grab.SetInput(w);grab.ReadFrontBufferOff();grab.Update()
 vtkimg=grab.GetOutput();raw=vtk_to_numpy(vtkimg.GetPointData().GetScalars()).reshape((H,W,-1));return raw[::-1,:,:3].copy()

def overlay_joints(img,model,world,ren,actor,frame):
    # Independently observed world-space joint positions from the animated skin hierarchy.
    from PIL import ImageDraw,ImageFont
    image=Image.fromarray(img).convert('RGBA')
    layer=Image.new('RGBA',image.size,(0,0,0,0));draw=ImageDraw.Draw(layer)
    coord=vtk.vtkCoordinate();coord.SetCoordinateSystemToWorld()
    name=('AsterOriginal','JuniperOriginal')[actor]
    names={n['name']:i for i,n in enumerate(model.nodes)}
    def xy(key):
        point=world[names[name+'_'+key]][:3,3]
        coord.SetValue(*[float(v) for v in point]);x,y=coord.GetComputedDoubleDisplayValue(ren)
        return (round(x),round(image.height-y))
    for side,color in [('L',(50,115,225,205)),('R',(240,112,48,210))]:
        for a,b in [('hip_'+side,'knee_'+side),('knee_'+side,'ankle_'+side),
                    ('shoulder_'+side,'elbow_'+side),('elbow_'+side,'wrist_'+side)]:
            draw.line([xy(a),xy(b)],fill=color,width=4)
        for joint in ['hip_'+side,'knee_'+side,'ankle_'+side,'shoulder_'+side,'elbow_'+side,'wrist_'+side]:
            x,y=xy(joint);draw.ellipse((x-6,y-6,x+6,y+6),fill=(*color[:3],160),outline=(255,255,255,200),width=2)
    p=frame_pose(frame,actor);labels=[]
    for side in ('L','R'):
        v=p['legs'][side];labels.append(f'{side}: {v["stage"]}, knee {math.degrees(-v["angles"]["knee"]):.0f} deg, hip {math.degrees(v["angles"]["hip"]):.0f} deg')
    draw.rectangle((12,45,550,111),fill=(255,255,255,205))
    draw.text((20,51),name+'    |    BLUE left side / ORANGE right side',fill=(20,30,45,255))
    draw.text((20,72),labels[0],fill=(35,60,110,255))
    draw.text((20,91),labels[1],fill=(130,60,20,255))
    return np.asarray(Image.alpha_composite(image,layer).convert('RGB')).copy()

def make_movie(model,view,dir_,W,H,frames=FRAMES):
 w,ren,actors,clock=make_renderer(model,view,W,H)
 target=dir_/f'r009-aster-juniper-gait-v2-{view}-{FRAMES}f.mp4'
 cmd=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-f','rawvideo','-vcodec','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','-','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p',str(target)]
 ff=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 samples={};t0=time.monotonic()
 try:
  for frame in range(frames):
   world,coords=model.skin_frame(frame)
   focus=0 if view=='aster-close' else 1 if view=='juniper-close' else None
   if focus is not None:
    anchor=float(world[0 if focus==0 else 19][0,3]);cam=ren.GetActiveCamera()
    cam.SetPosition(anchor,1.05,9.0);cam.SetFocalPoint(anchor,.94,0.0);cam.SetParallelScale(1.10)
    for (part,poly,act) in actors:act.SetVisibility(1 if part['actor']==focus else 0)
   for (p,poly,act),points in zip(actors,coords):
    poly.GetPoints().SetData(numpy_to_vtk(points,deep=True));poly.GetPoints().Modified();poly.Modified()
   clock.SetInput(f'VIEW: {view.upper()}  |  t={frame/FPS:.2f}s  |  FRAME {frame+1}/72  |  NOT HUMAN APPROVED')
   img=capture(w,W,H)
   if focus is not None:img=overlay_joints(img,model,world,ren,focus,frame)
   ff.stdin.write(img.tobytes())
   if frame in [0,6,12,18,24,30,36,42,48,54,60,66,71]:samples[frame]=img
 finally:
  ff.stdin.close();err=ff.stderr.read();rc=ff.wait()
  if rc:raise RuntimeError(f'FFMPEG_{view}_FAILED:{err[:500]!r}')
  w.Finalize()
 out=dir_/f'r009-aster-juniper-gait-v2-{view}-review-strip.png'
 picks=list(samples.items());cols=4;tw=350;th=197;rows=math.ceil(len(picks)/cols)
 sheet=Image.new('RGB',(cols*tw,rows*(th+28)),(245,248,250));draw=ImageDraw.Draw(sheet)
 for i,(f,img) in enumerate(picks):
  col=i%cols;row=i//cols;px=col*tw;py=row*(th+28)
  sheet.paste(Image.fromarray(img).resize((tw,th),Image.Resampling.BICUBIC),(px,py))
  draw.text((px+9,py+th+5),f'FRAME {f:02d}   /  {f/FPS:.2f}s',(25,35,45))
 sheet.save(out)
 return {'video':str(target),'review_sheet':str(out),'frames':frames,'fps':FPS,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes':target.stat().st_size,'render_seconds':round(time.monotonic()-t0,2)}

def science(model,dir_):
 track=[]
 for frame in range(FRAMES):
  world,coords=model.skin_frame(frame)
  row={'frame':frame,'actors':{}}
  for actor,name in enumerate(('AsterOriginal','JuniperOriginal')):
   data={'legs':{},'arms':{}}
   pose=frame_pose(frame,actor)
   for side in ('L','R'):
    # Identify actual shoe material + first bone influence from immutable input mesh.
    prim=next((i for i,p in enumerate(model.parts) if p['actor']==actor and p['mat_name'] in ('darkBoots','earthBoots')),None)
    if prim is None:raise RuntimeError('MISSING_ORIGINAL_BOOT_MATERIAL')
    part=model.parts[prim];pts=coords[prim]
    targetjoint=7 if side=='L' else 10
    mask=part['joints'][:,0]==targetjoint
    xyz=part['vertices'][mask];pworld=pts[mask]
    bottom=np.percentile(xyz[:,1],15)
    masksole=xyz[:,1] < bottom+.004
    sole=pworld[masksole]
    if len(sole)<5:raise RuntimeError('INSUFFICIENT_SHOE_SOLE_GEOMETRY')
    centroid=sole.mean(axis=0)
    hipnode=next(i for i,n in enumerate(model.nodes) if n['name']==name+'_hip_'+side)
    kneenode=next(i for i,n in enumerate(model.nodes) if n['name']==name+'_knee_'+side)
    anklenode=next(i for i,n in enumerate(model.nodes) if n['name']==name+'_ankle_'+side)
    # Genuinely evaluated world-space joint positions, not just planned controller values.
    xyznode=lambda i:[float(v) for v in world[i][:3,3]]
    pp=pose['legs'][side]
    data['legs'][side]={'phase':pp['phase'],'stage':pp['stage'],'hip_world':xyznode(hipnode),
       'knee_world':xyznode(kneenode),'ankle_world':xyznode(anklenode),
       'foot_sole_world':[float(v) for v in centroid],'foot_min_y_m':float(np.min(pworld[:,1])),
       'knee_flex_deg':math.degrees(-pp['angles']['knee']),
       'hip_flex_deg':math.degrees(pp['angles']['hip']),
       'ankle_rotation_deg':math.degrees(pp['angles']['ankle'])}
   for side in ('L','R'):
    data['arms'][side]={k:math.degrees(v) for k,v in pose['arms'][side].items()}
   row['actors'][name]=data
  track.append(row)
 metrics={'schema':'scp.r009.actual_glb_skin_observer.v2','input_sha256':model.sha,
  'source_mesh':'actual independently decoded glTF weighted mesh and IBM matrices',
  'stance_pairs':{},'motion_roles':{},'proxies_not_force_sensors':True,
  'per_frame_data':track,'accepted':False}
 for name in ('AsterOriginal','JuniperOriginal'):
  for side in ('L','R'):
   k=name+'/'+side;sample=[x['actors'][name]['legs'][side] for x in track]
   pairs=[]
   for i in range(1,len(sample)):
    a,b=sample[i-1],sample[i]
    # Physical stance-only subphase; exclude heel strike, toe-off, mode transitions and independent root phases.
    valid=(a['stage']==b['stage']=='stance' and .10<=a['phase']<=.43 and .10<=b['phase']<=.43 and b['phase']>a['phase'])
    if valid:
     v=np.asarray(b['foot_sole_world'])-np.asarray(a['foot_sole_world']);pairs.append(float(np.linalg.norm(v[[0,2]])))
   stance=np.array([x['foot_min_y_m'] for x in sample if x['stage']=='stance'],dtype=float)
   metrics['stance_pairs'][k]={'count':len(pairs),'above_2cm':sum(x>.02 for x in pairs),
    'max_xy_displacement_m_per_frame':float(max(pairs) if pairs else float('nan')),
    'mean_xy_displacement_m_per_frame':float(np.mean(pairs) if pairs else float('nan')),
    'min_actual_boot_y_in_stance_m':float(stance.min()),
    'max_actual_boot_y_in_stance_m':float(stance.max())}
  l=[x['actors'][name]['legs']['L'] for x in track]
  r=[x['actors'][name]['legs']['R'] for x in track]
  right=[x['actors'][name]['arms']['R'] for x in track]
  left=[x['actors'][name]['arms']['L'] for x in track]
  # Correlation within strides for lead leg's fwd ankle displacement and opposite arm shoulder flexion.
  root_direction=1 if name=='AsterOriginal' else -1
  hipL=np.array([x['hip_world'][0] for x in l]);footL=np.array([x['ankle_world'][0] for x in l])
  lfwd=root_direction*(footL-hipL)
  drive=np.array([x['shoulder'] for x in right])
  metrics['motion_roles'][name]={'left_hip_to_foot_fwd_min_m':float(lfwd.min()),'left_hip_to_foot_fwd_max_m':float(lfwd.max()),
   'left_knee_flex_max_deg':float(max(x['knee_flex_deg'] for x in l)),
   'right_knee_flex_max_deg':float(max(x['knee_flex_deg'] for x in r)),
   'right_elbow_rom_deg':float(max(x['elbow'] for x in right)-min(x['elbow'] for x in right)),
   'left_elbow_rom_deg':float(max(x['elbow'] for x in left)-min(x['elbow'] for x in left)),
   'contralateral_left_foot_right_shoulder_corr':float(np.corrcoef(lfwd,drive)[0,1]),
   'opposite_arm_pair_shoulder_corr':float(np.corrcoef([x['shoulder'] for x in left],drive)[0,1])}
 (dir_/'r009-gait-v2-source-native-skin-observer.json').write_text(json.dumps(metrics,indent=2))
 short={k:v for k,v in metrics.items() if k!='per_frame_data'}
 return short

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--glb',required=True);ap.add_argument('--out',required=True)
 ap.add_argument('--width',type=int,default=960);ap.add_argument('--height',type=int,default=540)
 args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 m=RenderModel(args.glb)
 s=science(m,out);print('SCIENCE',json.dumps(s,indent=2),flush=True)
 videos=[]
 for view in ['side','oblique','aster-close','juniper-close']:
  print('RENDER',view,flush=True)
  z=make_movie(m,view,out,args.width,args.height);print('RENDER_DONE',json.dumps(z),flush=True)
  videos.append(z)
 rec={'schema':'scp.r009.human_gait_v2_actual_video_receipt.v1','source_sha256':m.sha,'science':s,'videos':videos,
      'original_identity_not_applicable':True,'visual_human_acceptance':'PENDING','product_accepted':False}
 (out/'r009-gait-v2-real-video-receipt.json').write_text(json.dumps(rec,indent=2))
