#!/usr/bin/env python3
"""Rights-original articulated 3-D humanoid/glTF animation and camera-rendered H.264 QA set.

A deterministic procedural mannequin with true 3-D meshes, joint trajectories,
per-segment animated glTF transforms and three scientifically labeled gait cases.
"""
import argparse
import hashlib
import json
import math
import pathlib
import struct
import subprocess

import cv2
import numpy as np

FRAMES = 48
FPS = 24
SIZE = 400
LEN1 = .53
LEN2 = .52
STRIDE = .55
SPEED = .55

MATERIALS = {
    'torso': (45, 145, 159), 'pelvis': (42, 106, 125),
    'head': (224, 183, 143), 'arm': (208, 147, 112),
    'left_leg': (54, 116, 218), 'right_leg': (219, 110, 76),
    'left_shoe': (39, 73, 125), 'right_shoe': (144, 65, 48),
    'joint': (186, 195, 197),
}


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def foot(time_s, side, defect):
    offset = 0.0 if side == 'left' else 0.5
    cycle = time_s + offset
    step = math.floor(cycle)
    phase = cycle - step
    anchor_x = (step - offset) * STRIDE + .12
    contact = phase < .60
    if contact:
        x = anchor_x
        if defect == 'foot_slide' and side == 'left':
            x += .17 * (phase / .60)
        z = .12
    else:
        portion = (phase - .60) / .40
        x = anchor_x + STRIDE * (portion * portion * (3 - 2 * portion))
        z = .12 + .17 * math.sin(math.pi * portion)
    return np.array([x, -.14 if side == 'left' else .14, z]), contact


def knee_ik(hip, ankle, wrong=False):
    h, a = np.asarray(hip, float), np.asarray(ankle, float)
    d = np.array([a[0]-h[0], a[2]-h[2]], float)
    length = float(np.linalg.norm(d))
    if length >= LEN1 + LEN2 or length <= abs(LEN1 - LEN2):
        raise ValueError('unreachable limb endpoints')
    unit = d / length
    along = (LEN1 * LEN1 - LEN2 * LEN2 + length * length) / (2 * length)
    aside = math.sqrt(max(0., LEN1 * LEN1 - along * along))
    perpendicular = np.array([-unit[1], unit[0]])
    k = np.array([h[0], h[2]]) + along * unit + (-1 if wrong else 1) * aside * perpendicular
    return np.array([k[0], h[1], k[1]])


def pose_at(i, defect):
    if defect not in ('clean', 'knee_reverse', 'foot_slide'):
        raise ValueError('unsupported gait case')
    t = i / FPS
    root_x = SPEED * t
    bob = .013 * math.cos(4 * math.pi * t)
    root = np.array([root_x, 0., 1.08 + bob])
    parts = []
    joints = {}
    contact = {}

    def link(name, a, b, radius, material):
        parts.append({'name': name, 'type': 'segment', 'a': np.asarray(a,float),
                      'b': np.asarray(b,float), 'radius': radius, 'material': material})

    def ball(name, p, r, material):
        parts.append({'name':name, 'type':'ball', 'point':np.asarray(p,float),
                      'radius':r, 'material':material})

    chest = root + np.array([0, 0, .42])
    neck = chest + np.array([.018, 0., .13])
    head = neck + np.array([.018, 0., .15])
    link('torso',root + np.array([0,0,.01]),chest,.19,'torso')
    link('pelvis',root + np.array([0,0,-.12]),root + np.array([0,0,.07]),.165,'pelvis')
    ball('head',head,.125,'head')
    link('neck',neck-.06*np.array([0,0,1]),neck+.03*np.array([0,0,1]),.053,'head')
    for side in ('left','right'):
        y = -.14 if side == 'left' else .14
        hip = root + np.array([0.,y,-.055])
        ankle, is_contact = foot(t, side, defect)
        # One-sided reversal persists long enough to be measurable on native source.
        wrong = defect=='knee_reverse' and side=='left' and 20 <= i < 36
        knee = knee_ik(hip, ankle, wrong)
        prefix = side
        link(prefix+'_thigh',hip,knee,.091,prefix+'_leg')
        link(prefix+'_shin',knee,ankle,.075,prefix+'_leg')
        ball(prefix+'_knee_joint',knee,.077,'joint')
        shoe_center = ankle + np.array([.075,0.,-.055])
        toe = shoe_center + np.array([.105,0.,0.])
        heel = shoe_center - np.array([.07,0.,0.])
        link(prefix+'_shoe',heel,toe,.061,prefix+'_shoe')
        contact[prefix] = bool(is_contact)
        joints[prefix+'_hip'] = hip.tolist()
        joints[prefix+'_knee'] = knee.tolist()
        joints[prefix+'_ankle'] = ankle.tolist()
        joints[prefix+'_toe'] = toe.tolist()
        arm_phase = 2*math.pi * (t + (0 if side == 'right' else .5))
        shoulder = chest + np.array([0.,y*1.45,-.025])
        elbow = shoulder + np.array([.13*math.cos(arm_phase),0.,-.30])
        hand = elbow + np.array([.12*math.cos(arm_phase)+.035,0.,-.28])
        link(prefix+'_upper_arm',shoulder,elbow,.067,'arm')
        link(prefix+'_forearm',elbow,hand,.055,'arm')
        ball(prefix+'_hand',hand,.058,'head')
        joints[prefix+'_shoulder'] = shoulder.tolist()
        joints[prefix+'_elbow'] = elbow.tolist()
        joints[prefix+'_hand'] = hand.tolist()
    joints['root'] = root.tolist()
    joints['head'] = head.tolist()
    return parts, joints, contact


def sphere_mesh(lat=7, lon=12):
    verts=[];indices=[]
    for y in range(lat+1):
        phi=math.pi*y/lat
        for x in range(lon+1):
            theta=2*math.pi*x/lon
            verts.append([math.sin(phi)*math.cos(theta),math.sin(phi)*math.sin(theta),math.cos(phi)])
    for y in range(lat):
        for x in range(lon):
            a=y*(lon+1)+x; b=a+(lon+1)
            indices.extend([a,b,a+1,b,b+1,a+1])
    return np.asarray(verts,dtype=np.float32),np.asarray(indices,dtype=np.uint16).reshape(-1,3)


def quat_z_to(target):
    z=np.array([0.,0.,1.]); target=np.asarray(target,float)
    target=target/np.linalg.norm(target)
    v=np.cross(z,target); w=1+np.dot(z,target)
    if w<1e-8:return np.array([1.,0.,0.,0.])
    q=np.array([v[0],v[1],v[2],w]); return q/np.linalg.norm(q)


def transform(part):
    radius=part['radius']
    if part['type']=='ball':
        return part['point'],np.array([0,0,0,1],float),np.array([radius]*3,float)
    a,b=part['a'],part['b']
    midpoint=(a+b)/2
    length=float(np.linalg.norm(b-a))
    return midpoint,quat_z_to(b-a),np.array([radius,radius,length/2 + radius*.45])


def build_animation(variant, out):
    """Write an actual glTF 2.0 animated mesh scene, not an animation of 2D sprites."""
    poses=[pose_at(i,variant)[0] for i in range(FRAMES)]
    names=[p['name'] for p in poses[0]]
    if any([p['name'] for p in parts]!=names for parts in poses):
        raise ValueError('animated node ordering changed')
    verts,faces=sphere_mesh()
    stream=bytearray(); views=[]; accessors=[]

    def pack(a,typ,component,kind,with_bounds=False):
        arr=np.ascontiguousarray(a)
        while len(stream)%4:stream.append(0)
        off=len(stream);stream.extend(arr.tobytes())
        vid=len(views);views.append({'buffer':0,'byteOffset':off,'byteLength':arr.nbytes})
        item={'bufferView':vid,'componentType':component,'count':len(arr),'type':kind}
        if with_bounds:
            flat=arr.reshape(len(arr),-1);item['min']=flat.min(axis=0).tolist();item['max']=flat.max(axis=0).tolist()
        accessors.append(item);return len(accessors)-1

    pos_acc=pack(verts,'vec3',5126,'VEC3',True)
    nor_acc=pack(verts,'vec3',5126,'VEC3')
    idx_acc=pack(faces.ravel(), 'indices',5123,'SCALAR')
    times=pack(np.arange(FRAMES,dtype=np.float32)/FPS,'time',5126,'SCALAR',True)
    mats=[{'name':k,'pbrMetallicRoughness':{'baseColorFactor':[x/255 for x in c]+[1.0],
            'metallicFactor':0,'roughnessFactor':.78},'doubleSided':True} for k,c in MATERIALS.items()]
    order=list(MATERIALS)
    meshes=[]
    for k in order:
        meshes.append({'name':'mannequin_'+k,'primitives':[{'attributes':{'POSITION':pos_acc,'NORMAL':nor_acc},
                       'indices':idx_acc,'material':order.index(k)}]})
    nodes=[]; channels=[]; samplers=[]
    for n,name in enumerate(names):
        part0=poses[0][n];tr,qr,sc=transform(part0)
        nodes.append({'name':name,'mesh':order.index(part0['material']),
                      'translation':tr.tolist(),'rotation':qr.tolist(),'scale':sc.tolist()})
        rows=[transform(p[n]) for p in poses]
        for typ,data in [('translation',[r[0] for r in rows]),('rotation',[r[1] for r in rows]),('scale',[r[2] for r in rows])]:
            acc=pack(np.asarray(data,dtype=np.float32), 'anim',5126,
                     'VEC4' if typ=='rotation' else 'VEC3')
            s=len(samplers);samplers.append({'input':times,'output':acc,'interpolation':'LINEAR'})
            channels.append({'sampler':s,'target':{'node':n,'path':typ}})
    # glTF 2.0 binary buffer requires four-byte aligned JSON and BIN chunks.
    gltf={'asset':{'version':'2.0','generator':'SemperSupra original 3D QA mannequin v1',
                   'copyright':'Rights-original procedural research model'},
          'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}], 'nodes':nodes,
          'meshes':meshes,'materials':mats,'accessors':accessors,'bufferViews':views,
          'buffers':[{'byteLength':len(stream)}],
          'animations':[{'name':variant+'_walking_48frames','channels':channels,'samplers':samplers}],
          'extras':{'fps':FPS,'variant':variant,'groundPlaneZ':0,'axes':'x forward / z up / y lateral',
                    'rights':'rights-original research mannequin; no identity references'}}
    payload=json.dumps(gltf,separators=(',',':'),sort_keys=True).encode('utf-8')
    payload+=b' ' * ((-len(payload))%4)
    while len(stream)%4:stream.append(0)
    length=12+8+len(payload)+8+len(stream)
    glb=struct.pack('<III',0x46546c67,2,length)+struct.pack('<II',len(payload),0x4e4f534a)+payload+struct.pack('<II',len(stream),0x004e4942)+stream
    out.write_bytes(glb)
    return {'sha256':sha_bytes(glb),'bytes':len(glb),'animated_nodes':len(nodes),
            'animation_channels':len(channels),'triangles_per_mesh':len(faces)}


def camera(view):
    target=np.array([.50,0.,.92])
    eye=np.array([.50,-5.3,2.12]) if view=='side' else np.array([3.2,-4.7,2.27])
    look=target-eye;look/=np.linalg.norm(look)
    right=np.cross(look,[0,0,1.]);right/=np.linalg.norm(right)
    up=np.cross(right,look); up/=np.linalg.norm(up)
    return eye,look,right,up


def project(points,cam):
    eye,forward,right,up=cam
    relative=np.asarray(points)-eye
    depth=np.dot(relative,forward)
    if np.any(depth<=.05):raise ValueError('3-D geometry behind camera')
    return np.column_stack((SIZE/2 + 630*np.dot(relative,right)/depth,
                            SIZE/2 - 630*np.dot(relative,up)/depth)),depth


def render_frame(i, variant, view, mesh):
    parts,joints,contact=pose_at(i,variant)
    cam=camera(view)
    frame=np.empty((SIZE,SIZE,3),dtype=np.uint8)
    for row in range(SIZE):
        gradient=int(242-row*0.052)
        frame[row,:]=(max(170,gradient-4),max(170,gradient-1),max(170,gradient))
    # Ground reference grid genuinely projected from 3-D coordinates.
    def drawline(a,b,color=(214,220,225),thickness=1):
        p,_=project([a,b],cam)
        cv2.line(frame,tuple(np.round(p[0]).astype(int)),tuple(np.round(p[1]).astype(int)),color,thickness,cv2.LINE_AA)
    for x in np.arange(-1.5,2.5,.25):drawline((x,-.7,0),(x,.7,0))
    for y in np.arange(-.7,.8,.2):drawline((-1.5,y,0),(2.5,y,0))
    for side in ('left','right'):
        p=np.asarray(joints[side+'_ankle']);p[2]=.006
        location,_=project([p],cam)
        xy=tuple(np.round(location[0]).astype(int))
        cv2.circle(frame,xy,12,(199,207,210),2,cv2.LINE_AA)
        if contact[side]:cv2.circle(frame,xy,3,(65,125,75),-1,cv2.LINE_AA)
    sphere,faces=mesh
    all_faces=[]
    light=np.array([-.4,-.5,.8]);light/=np.linalg.norm(light)
    for p in parts:
        trans,quat,scale=transform(p)
        qx,qy,qz,qw=quat
        # Convert unit quaternion to rotation matrix.
        rot=np.array([[1-2*(qy*qy+qz*qz),2*(qx*qy-qz*qw),2*(qx*qz+qy*qw)],
                      [2*(qx*qy+qz*qw),1-2*(qx*qx+qz*qz),2*(qy*qz-qx*qw)],
                      [2*(qx*qz-qy*qw),2*(qy*qz+qx*qw),1-2*(qx*qx+qy*qy)]])
        world=(sphere*scale)@rot.T+trans
        proj,depth=project(world,cam)
        rgb=MATERIALS[p['material']]
        for tri in faces:
            x,y,z=world[tri];nor=np.cross(y-x,z-x)
            magnitude=np.linalg.norm(nor)
            if magnitude<1e-9:continue
            nor/=magnitude
            brightness=.54+.46*max(0.,float(np.dot(nor,light)))
            shade=tuple(max(0,min(255,int(channel*brightness))) for channel in rgb[::-1])
            coords=np.round(proj[tri]).astype(np.int32)
            if (coords[:,0].max()<0 or coords[:,0].min()>=SIZE or
                coords[:,1].max()<0 or coords[:,1].min()>=SIZE):continue
            all_faces.append((float(np.mean(depth[tri])),coords,shade))
    all_faces.sort(key=lambda x:x[0],reverse=True)
    for _,points,color in all_faces:
        cv2.fillConvexPoly(frame,points,color,lineType=cv2.LINE_AA)
    # Non-scientific overlay is outside the model to avoid evidence confusion.
    pretty={'clean':'CONTROL / NORMAL WALK','knee_reverse':'FAULT / REVERSED KNEE',
            'foot_slide':'FAULT / PLANTED FOOT SLIDE'}[variant]
    cv2.rectangle(frame,(0,0),(SIZE,39),(37,46,58),-1)
    cv2.putText(frame,'3D GAIT RDT&E  |  '+pretty,(12,16),cv2.FONT_HERSHEY_SIMPLEX,.38,(239,243,245),1,cv2.LINE_AA)
    cv2.putText(frame,f'{view.upper()}  |  F {i+1:02d}/{FRAMES}  |  24 FPS  |  ORIGINAL MESH',(12,31),cv2.FONT_HERSHEY_SIMPLEX,.34,(204,218,224),1,cv2.LINE_AA)
    return frame


def create_video(variant,view,folder,mesh):
    dest=folder/(variant+'_'+view+'.mp4')
    args=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-f','rawvideo',
          '-pix_fmt','bgr24','-s',f'{SIZE}x{SIZE}','-r',str(FPS),'-i','pipe:0','-an',
          '-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
    cmd=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    for i in range(FRAMES):cmd.stdin.write(render_frame(i,variant,view,mesh).tobytes())
    cmd.stdin.close();errors=cmd.stderr.read();result=cmd.wait()
    if result:raise RuntimeError(errors.decode('utf-8','replace')[-700:])
    return dest


def render_corpus(root, chosen=None):
    root=pathlib.Path(root);root.mkdir(parents=True,exist_ok=True)
    mesh=sphere_mesh()
    items=[]
    for variant in (chosen or ('clean','knee_reverse','foot_slide')):
        glb=root/(variant+'.glb');info=build_animation(variant,glb)
        full=[]
        for i in range(FRAMES):
            _,points,contact=pose_at(i,variant)
            full.append({'frame':i,'time_s':round(i/FPS,6),'joints':points,'contact':contact})
        labels=root/(variant+'_ground_truth.json')
        labels.write_text(json.dumps({'schema':'scp.original-3d-gait-labels.v1','variant':variant,
                   'fps':FPS,'frames':full,'source_model':glb.name,
                   'gltf_sha256':info['sha256'],'thigh_m':LEN1,'shin_m':LEN2,
                   'camera_profiles':['side','three_quarter']},indent=2)+'\n')
        outputs=[]
        for view in ('side','three_quarter'):
            video=create_video(variant,view,root,mesh)
            outputs.append({'view':view,'file':video.name,'sha256':sha_bytes(video.read_bytes()),
                            'bytes':video.stat().st_size})
        items.append({'variant':variant,'model':glb.name,'model_info':info,
                      'labels':labels.name,'video':outputs})
    manifest={'schema':'scp.original-3d-gait-corpus.v1','license':'CC0-1.0 for original generated files',
              'generator':'rights-original procedural full-body mesh/rig animation',
              'no_personal_identity':True,'frames':FRAMES,'fps':FPS,'resolution':[SIZE,SIZE],
              'variants':items,'notes':['Actual animated glTF 2.0 mesh nodes and 3-D frame poses',
                  'H.264 frames rasterize the actual triangles in 3-D with two calibrated cameras',
                  'Defects intentionally synthetic and unqualified for biological movement',
                  'No third-party character art, mocap, person identity or model weights']}
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'variants':[x['variant'] for x in items],'video_count':6,
                      'glb_count':3,'frame_count':FRAMES,'output':str(root)},indent=2))
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True)
    p.add_argument('--variants',default='clean,knee_reverse,foot_slide')
    opts=p.parse_args();render_corpus(opts.out,opts.variants.split(','))