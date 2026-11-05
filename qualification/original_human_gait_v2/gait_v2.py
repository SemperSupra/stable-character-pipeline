#!/usr/bin/env python3
"""R009 source-pinned, phase-aware human-inspired gait overlay for original fictional GLB.

No protected human likeness or third-party source. Motion is kinematically plausible,
not clinical normative validation, photorealistic, or scientifically certified.
All source meshes/skins/textures and source file remain immutable.
"""
import argparse,copy,hashlib,json,math,struct
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
FPS=12;FRAMES=72;DURATION=(FRAMES-1)/FPS;T=1.60;D=0.60
SPEED=2.56/6.0
STRIDE=SPEED*T
FORWARD=.16
HIP_Y=.89
ANKLE_Y=.115
THIGH=math.hypot(.400,.01414213562373095)
SHANK=math.hypot(.375,.01)
REST_HIP=math.atan2(-.01,.4)
REST_SHANK=math.atan2(-.01,.375)
JOINT_BOUNDS={"hip":(-.40,.70),"knee":(-1.30,0),"ankle":(-.40,.72),"shoulder":(-.48,.48),"elbow":(.0,.75)}

def smooth(x):
    x=min(1.,max(0.,x));return x*x*(3.-2*x)

def hermite(a,b,m0,m1,u):
    return (2*u**3-3*u*u+1)*a+(u**3-2*u*u+u)*m0+(-2*u**3+3*u*u)*b+(u**3-u*u)*m1

def leg_target(phase):
    p=phase%1.
    if p<D:
        f=FORWARD-SPEED*T*p
        heel_raise=.04*smooth((p-.45)/.15)
        y=ANKLE_Y+heel_raise
        # Stance: mostly flat, modest heel-strike toe-up to late heel rise.
        pitch=.055*(1-smooth(p/.12))-.20*smooth((p-.46)/.14)
        stage='stance'
    else:
        u=(p-D)/(1.-D);start=FORWARD-SPEED*T*D
        tangent=-SPEED*T*(1.-D)
        f=hermite(start,FORWARD,tangent,tangent,u)
        y=ANKLE_Y+.04*(1-u)**2+.100*max(0.,math.sin(math.pi*(u+.90*u*(1-u))))**1.15
        pitch=-.20-.05*smooth(u/.2)+.25*smooth((u-.55)/.45)+.05*smooth((u-.82)/.18)
        stage='swing'
    return float(f),float(y),float(pitch),stage

def solve_leg(phase,pelvis_delta):
    f,y,pitch,stage=leg_target(phase)
    # Analytic planar two-link IK in (local forward=-Z, up=Y).
    dy=y-(HIP_Y+pelvis_delta);dst=math.hypot(f,dy)
    if dst>THIGH+SHANK+1e-6 or dst<abs(THIGH-SHANK)-1e-6:
        raise ValueError('IK_UNREACHABLE f=%g y=%g p=%g dst=%g limit=%g'% (f,y,phase,dst,THIGH+SHANK))
    dst=min(dst,THIGH+SHANK-1e-7)
    along=(THIGH*THIGH-SHANK*SHANK+dst*dst)/(2*dst*dst)
    h=math.sqrt(max(0,THIGH*THIGH-(along*dst)**2))
    # Knee always moves FORWARD of the hip-ankle chord (physiological sagittal bend).
    knee_f=along*f+h*(-dy)/dst
    knee_y=along*dy+h*f/dst
    thigh_angle=math.atan2(knee_f,-knee_y)-REST_HIP
    shank_f=f-knee_f;shank_y=dy-knee_y
    absolute_shank_angle=math.atan2(shank_f,-shank_y)-REST_SHANK
    knee_angle=absolute_shank_angle-thigh_angle
    ankle_angle=-(thigh_angle+knee_angle)+pitch
    # glTF local ankle controls foot orientation; no toe joint exists in source.
    angles={'hip':thigh_angle,'knee':knee_angle,'ankle':ankle_angle}
    for k,v in angles.items():
        low,high=JOINT_BOUNDS[k]
        if not low-1e-4<=v<=high+1e-4:
            raise ValueError('JOINT_ROM_OVERFLOW %s %.3f at phase %.3f'%(k,v,phase))
    return {'phase':phase%1.,'stage':stage,'fwd':f,'ankle_y':y,'pitch':pitch,'knee_fwd':knee_f,
            'knee_y':HIP_Y+pelvis_delta+knee_y,'angles':angles}

def frame_pose(frame,which):
    # Offset variation prevents unnatural synchronized actors; left/right legs 180deg apart.
    t=frame/FPS;p=(t/T + (0.0 if which==0 else .22))%1
    # Two-bob COM movement per stride; calibrated for source leg reach.
    pelvis_delta=-.006-.012*(.5+.5*math.cos(4*math.pi*p))
    legs={'L':solve_leg(p,pelvis_delta),'R':solve_leg((p+.5)%1.,pelvis_delta)}
    stride_difference=legs['L']['fwd']-legs['R']['fwd']
    arm_drive=math.cos(2*math.pi*p)  # smooth contralateral first harmonic, not saturating square wave
    # Contralateral coupling: left leg forward -> right arm forward.
    arms={
        'L':{'shoulder':-.32*arm_drive,'elbow':.34-.25*arm_drive},
        'R':{'shoulder': .32*arm_drive,'elbow':.34+.25*arm_drive},
    }
    for side,a in arms.items():
        for role,val in a.items():
            lo,hi=JOINT_BOUNDS[role]
            if not lo<=val<=hi:raise ValueError('ARM_ROM_OVERFLOW')
    return {'frame':frame,'time_s':t,'phase_L':p,'pelvis_delta_y_m':pelvis_delta,'legs':legs,
            'arms':arms,'arm_drive':arm_drive}

def decode_glb(data):
    if len(data)<28 or data[:4]!=b'glTF' or struct.unpack_from('<I',data,8)[0]!=len(data):raise ValueError('BAD_SOURCE_GLB')
    jsonlen,kind=struct.unpack_from('<I4s',data,12)
    if kind!=b'JSON':raise ValueError('BAD_JSON_CHUNK')
    doc=json.loads(data[20:20+jsonlen]);off=20+jsonlen
    binlen,kind=struct.unpack_from('<I4s',data,off)
    if kind!=b'BIN\0' or off+8+binlen!=len(data):raise ValueError('BAD_BIN_CHUNK')
    return doc,data[off+8:]

def encode_glb(doc,binary):
    j=json.dumps(doc,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    j+=b' '*(-len(j)%4);binary+=b'\0'*(-len(binary)%4)
    return struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(binary))+struct.pack('<I4s',len(j),b'JSON')+j+struct.pack('<I4s',len(binary),b'BIN\0')+binary

def produce(source,out,receipt,expected):
    source=Path(source);out=Path(out);receipt=Path(receipt)
    if len({str(x.resolve()) for x in (source,out,receipt)})!=3:raise ValueError('SOURCE_MUTATION_REFUSED')
    raw=source.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=expected:raise ValueError('SOURCE_HASH_MISMATCH')
    doc,binary=decode_glb(raw)
    if doc.get('extras',{}).get('source_class')!='ORIGINAL_SELF_AUTHORED_SYNTHETIC' or doc['extras'].get('third_party_models') is not False:raise ValueError('NOT_OWNER_ORIGINAL')
    actors=('AsterOriginal','JuniperOriginal');nodes=doc['nodes']
    nodeids={n['name']:i for i,n in enumerate(nodes)}
    if len(doc['skins'])!=2 or any(len(x['joints'])!=17 for x in doc['skins']):raise ValueError('INCORRECT_RIG')
    for a in actors:
        for part in ('SceneRoot','pelvis','hip_L','hip_R','knee_L','knee_R','ankle_L','ankle_R',
                     'shoulder_L','shoulder_R','elbow_L','elbow_R','spine','head'):
            if a+'_'+part not in nodeids:raise ValueError('MISSING_RIG_PART '+part)
    if len(doc['animations'])!=1:raise ValueError('UNEXPECTED_CLIPS')
    old_animation=doc['animations'][0];new=copy.deepcopy(old_animation)
    # Enforce no source motion clip fake claims. We only rewrite animation samplers.
    mapping={(ch['target']['node'],ch['target']['path']):ch['sampler'] for ch in new['channels']}
    poses=[[frame_pose(f,w) for f in range(FRAMES)] for w in range(2)]
    binary=bytearray(binary)
    def put_accessor(arr,typ):
        data=np.asarray(arr,dtype='<f4');size=data.size*4
        while len(binary)%4:binary.append(0)
        off=len(binary);binary.extend(data.tobytes(order='C'))
        doc['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':size})
        num={'SCALAR':1,'VEC3':3,'VEC4':4}[typ]
        doc['accessors'].append({'bufferView':len(doc['bufferViews'])-1,'componentType':5126,'count':len(data)//num,'type':typ})
        return len(doc['accessors'])-1
    timeacc=put_accessor([f/FPS for f in range(FRAMES)],'SCALAR')
    control_data={}
    for which,a in enumerate(actors):
        pose=poses[which];control_data[a]=pose
        srcroot=nodeids[a+'_SceneRoot']
        for part in ('pelvis','hip_L','hip_R','knee_L','knee_R','ankle_L','ankle_R','shoulder_L',
                     'shoulder_R','elbow_L','elbow_R','spine','head'):
            ni=nodeids[a+'_'+part];values=[]
            if part=='pelvis':
                typ='VEC3';path='translation'
                for p in pose:values.extend([0,.93+p['pelvis_delta_y_m'],0])
            else:
                typ='VEC4';path='rotation'
                for p in pose:
                    if part.startswith(('hip_','knee_','ankle_')):
                        role,side=part.split('_');ang=p['legs'][side]['angles'][role]
                    elif part.startswith(('shoulder_','elbow_')):
                        role,side=part.split('_');ang=p['arms'][side][role]
                    elif part=='spine':ang=0.012*math.sin(2*math.pi*p['phase_L'])
                    else:ang=-0.010*math.sin(2*math.pi*p['phase_L'])
                    values.extend([math.sin(ang/2),0,0,math.cos(ang/2)])
            outputacc=put_accessor(values,typ)
            if (ni,path) in mapping:
                si=mapping[(ni,path)]
                new['samplers'][si]={'input':timeacc,'output':outputacc,'interpolation':'LINEAR'}
            else:
                si=len(new['samplers']);new['samplers'].append({'input':timeacc,'output':outputacc,'interpolation':'LINEAR'})
                new['channels'].append({'sampler':si,'target':{'node':ni,'path':path}})
    doc['animations']=[new]
    new['name']='R009HumanInspiredPhaseAwareIK6s_72f_NOT_ACCEPTED'
    doc['buffers'][0]['byteLength']=len(binary)
    doc.setdefault('extras',{})['r009_human_gait_v2']={
        'input_sha256':sha,'source_unchanged':True,'source_class':'ORIGINAL_SYNTHETIC',
        'stance_fraction':D,'swing_fraction':1-D,'stride_period_s':T,'hip_knee_ankle_ik':True,
        'contralateral_shoulder_elbow_coupling':True,'clinical_human_gait_acceptance':'NOT_TESTED',
        'real_human_identity':'NOT_APPLICABLE','foot_skin_science':'NOT_TESTED',
        'source_assets_unchanged':True,'publication_approved':False,
        'gait_reference_urls':['https://www.oandplibrary.org/alp/chap13-01.asp',
           'https://pmc.ncbi.nlm.nih.gov/articles/PMC10277704/',
           'https://pubmed.ncbi.nlm.nih.gov/18417138/']}
    payload=encode_glb(doc,bytes(binary));out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(out.suffix+'.tmp');tmp.write_bytes(payload);tmp.replace(out)
    r={'schema':'scp.r009.human_inspired_synthetic_gait.v2',
       'source_sha256':sha,'output_sha256':hashlib.sha256(payload).hexdigest(),
       'source_bytes_untouched':hashlib.sha256(source.read_bytes()).hexdigest()==sha,
       'input_size_bytes':len(raw),'output_size_bytes':len(payload),'characters':list(actors),
       'skins':[len(s['joints']) for s in doc['skins']],'clips':1,'channels':len(new['channels']),
       'frames':FRAMES,'fps':FPS,'motion':'phase-aware 2-link IK + heel-rise/ankle pitch + contralateral shoulder-elbow',
       'ranges_degrees':{},'actual_skinned_mesh_contact':'PENDING','human_motion_accepted':False,
       'out_name':out.name}
    for role in ('hip','knee','ankle','shoulder','elbow'):
        vals=[]
        for pp in poses:
            for p in pp:
                for side in ('L','R'):
                    d=p['legs'][side]['angles'] if role in ('hip','knee','ankle') else p['arms'][side]
                    vals.append(d[role])
        r['ranges_degrees'][role]=[round(math.degrees(min(vals)),3),round(math.degrees(max(vals)),3)]
    receipt.write_text(json.dumps(r,indent=2,sort_keys=True))
    return r,control_data

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);ap.add_argument('--receipt',required=True);ap.add_argument('--sha256',required=True)
    a=ap.parse_args()
    try:
        r,_=produce(a.source,a.out,a.receipt,a.sha256);print(json.dumps(r,indent=2))
    except Exception as e:raise SystemExit(f'GAIT_V2_FAILURE:{e}')
