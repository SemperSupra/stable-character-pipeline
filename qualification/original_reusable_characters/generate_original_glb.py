#!/usr/bin/env python3
"""Original-from-code fictional character demo. Pure stdlib glTF2 binary, no third-party media.

The synthetic figures are deliberately stylized. This is a technical model/skin/
animation acceptance fixture, NOT a natural human gait or photorealism claim.
"""
import argparse,hashlib,json,math,struct
from pathlib import Path

FPS=12
FRAMES=72
DURATION=(FRAMES-1)/FPS
NAMES=('AsterOriginal','JuniperOriginal')

class Buffer:
    def __init__(self): self.data=bytearray();self.views=[];self.accessors=[]
    def put(self, values, fmt, typ, count, target=None, normalize=False, extrema=False):
        # fmt is one struct scalar and typ glTF vector specification.
        comps={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[typ]
        assert len(values)==count*comps
        size=struct.calcsize('<'+fmt)
        while len(self.data)%4:self.data.append(0)
        off=len(self.data)
        for x in values:self.data+=struct.pack('<'+fmt,x)
        view={'buffer':0,'byteOffset':off,'byteLength':len(values)*size}
        if target:view['target']=target
        vi=len(self.views);self.views.append(view)
        ct={'f':5126,'H':5123,'B':5121,'I':5125}[fmt]
        a={'bufferView':vi,'componentType':ct,'count':count,'type':typ}
        if normalize:a['normalized']=True
        if extrema and typ in ('VEC3','SCALAR'):
            s=[values[k::comps] for k in range(comps)]
            a['min']=[min(x) for x in s];a['max']=[max(x) for x in s]
        ai=len(self.accessors);self.accessors.append(a);return ai

# All positions are glTF Y-up; each figure's rest mesh is in armature-root local coordinates.
JOINTS=[
('pelvis',None,(0,.93,0)),('spine','pelvis',(0,1.11,0)),('chest','spine',(0,1.38,0)),
('neck','chest',(0,1.49,0)),('head','neck',(0,1.63,0)),
('hip_L','pelvis',(-.13,.89,0)),('knee_L','hip_L',(-.14,.49,.01)),('ankle_L','knee_L',(-.14,.115,.02)),
('hip_R','pelvis',(.13,.89,0)),('knee_R','hip_R',(.14,.49,.01)),('ankle_R','knee_R',(.14,.115,.02)),
('shoulder_L','chest',(-.235,1.35,0)),('elbow_L','shoulder_L',(-.415,1.045,0)),('wrist_L','elbow_L',(-.45,.79,0)),
('shoulder_R','chest',(.235,1.35,0)),('elbow_R','shoulder_R',(.415,1.045,0)),('wrist_R','elbow_R',(.45,.79,0))]
POS={n:xyz for n,_,xyz in JOINTS}
JIDX={n:i for i,(n,_,_) in enumerate(JOINTS)}

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def mul(a,s):return tuple(x*s for x in a)
def norm(a):return math.sqrt(sum(v*v for v in a))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a):return mul(a,1/max(norm(a),1e-12))

def quat_x(angle):return [math.sin(angle/2),0.,0.,math.cos(angle/2)]
def quat_z(angle):return [0.,0.,math.sin(angle/2),math.cos(angle/2)]

class Geometry:
    def __init__(self):self.parts={}
    def part(self,material):return self.parts.setdefault(material,{'p':[],'n':[],'j':[],'w':[],'i':[]})
    def ellipsoid(self,material,center,radii,bone,lat=14,lon=20):
        q=self.part(material);base=len(q['p'])//3
        for a in range(lat+1):
            theta=math.pi*a/lat
            for b in range(lon+1):
                phi=2*math.pi*b/lon
                ux=math.sin(theta)*math.cos(phi);uy=math.cos(theta);uz=math.sin(theta)*math.sin(phi)
                q['p']+=list(add(center,(ux*radii[0],uy*radii[1],uz*radii[2])))
                q['n']+=list(unit((ux/radii[0],uy/radii[1],uz/radii[2])))
                q['j']+=[JIDX[bone],0,0,0];q['w']+=[1.,0.,0.,0.]
        for a in range(lat):
            for b in range(lon):
                v=base+a*(lon+1)+b;nv=v+lon+1
                q['i'] += [v,nv,v+1,v+1,nv,nv+1]
    def tube(self,material,start,end,r0,r1,bone_a,bone_b,steps=10,sides=18,ellipse=(1.,1.)):
        q=self.part(material);base=len(q['p'])//3
        axis=unit(sub(end,start));ref=(0.,0.,1.) if abs(axis[2])<.85 else (0.,1.,0.)
        u=unit(cross(axis,ref));v=unit(cross(axis,u))
        for k in range(steps+1):
            t=k/steps;middle=add(start,mul(sub(end,start),t));radius=r0*(1-t)+r1*t
            blend=max(0.,min(1.,(t-.64)/.36))
            for b in range(sides+1):
                ang=2*math.pi*b/sides
                direction=add(mul(u,math.cos(ang)*ellipse[0]),mul(v,math.sin(ang)*ellipse[1]))
                q['p']+=list(add(middle,mul(direction,radius)))
                q['n']+=list(unit(direction))
                q['j']+=[JIDX[bone_a],JIDX[bone_b],0,0];q['w'] += [1.-blend,blend,0.,0.]
        for k in range(steps):
            for b in range(sides):
                idx=base+k*(sides+1)+b;next_=idx+sides+1
                q['i'] += [idx,idx+1,next_,idx+1,next_+1,next_]

def figure_geometry(which):
    g=Geometry();aster=which==0
    skin='skinWarm' if aster else 'skinCool'
    jacket='coralJacket' if aster else 'tealJacket'
    trousers='slatePants' if aster else 'ochrePants'
    hair='ebonyHair' if aster else 'chestnutHair'
    boots='darkBoots' if aster else 'earthBoots'
    # Multiple connected, smooth-weighted tubes and joints, not a single block-man.
    g.tube(jacket,(0,.92,0),(0,1.39,0),.225,.245,'pelvis','chest',steps=13,ellipse=(1.,.60))
    g.ellipsoid(skin,(0,1.46,0),(.10,.085,.09),'neck')
    g.ellipsoid(skin,(0,1.64,0),(.145,.185,.126),'head',lat=20,lon=26)
    g.ellipsoid(hair,(0,1.773,.011),(.15,.076,.13),'head')
    for s in (-1,1):
        # Eyes and pupils: forward is -Z.
        g.ellipsoid('eyeWhite',(s*.059,1.657,-.115),(.031,.020,.010),'head',lat=9,lon=12)
        g.ellipsoid('iris',(s*.059,1.655,-.124),(.012,.016,.007),'head',lat=9,lon=12)
        # Hair framing deliberately differs across characters.
        if aster:
            g.ellipsoid(hair,(s*.133,1.68,.018),(.027,.135,.080),'head',lat=12,lon=12)
        else:
            g.ellipsoid(hair,(s*.126,1.595,.037),(.035,.19,.077),'head',lat=12,lon=12)
        letter='L' if s==-1 else 'R'
        hip,knee,ankle=(POS[f'{name}_{letter}'] for name in ('hip','knee','ankle'))
        g.tube(trousers,hip,knee,.115,.092,f'hip_{letter}',f'knee_{letter}',steps=10)
        g.tube(trousers,knee,ankle,.093,.074,f'knee_{letter}',f'ankle_{letter}',steps=10)
        g.ellipsoid(boots,(s*.14,.079,-.067),(.098,.072,.174),f'ankle_{letter}',lat=12,lon=16)
        shoulder,elbow,wrist=(POS[f'{name}_{letter}'] for name in ('shoulder','elbow','wrist'))
        g.tube(jacket,shoulder,elbow,.096,.069,f'shoulder_{letter}',f'elbow_{letter}',steps=10)
        g.tube(jacket,elbow,wrist,.071,.053,f'elbow_{letter}',f'wrist_{letter}',steps=10)
        g.ellipsoid(skin,add(wrist,(0,-.035,0)),(.055,.077,.05),f'wrist_{letter}',lat=10,lon=12)
    if not aster:
        g.ellipsoid(hair,(0,1.39,.100),(.105,.215,.097),'head',lat=16,lon=16) # long back hair
    else:
        g.ellipsoid('scarf',(0,1.473,-.08),(.135,.042,.060),'neck',lat=10,lon=16)
    return g

def make_demo(out_path):
    b=Buffer();nodes=[];meshes=[];skins=[];animations=[];scene_roots=[]
    palette=[('skinWarm',(0.88,.59,.46)),('skinCool',(.58,.40,.31)),('coralJacket',(.62,.20,.25)),
             ('tealJacket',(.12,.43,.43)),('slatePants',(.17,.24,.31)),('ochrePants',(.38,.29,.16)),
             ('ebonyHair',(.068,.065,.078)),('chestnutHair',(.20,.11,.07)),('darkBoots',(.085,.07,.07)),
             ('earthBoots',(.22,.14,.09)),('eyeWhite',(.91,.86,.77)),('iris',(.065,.054,.045)),('scarf',(.92,.73,.30))]
    materials=[{'name':k,'pbrMetallicRoughness':{'baseColorFactor':[r,g,z,1.0],'metallicFactor':0,'roughnessFactor':.86},'doubleSided':True} for k,(r,g,z) in palette]
    midx={k:i for i,(k,_) in enumerate(palette)}
    # one global animation track, two independent roots and all 72 authored poses.
    tracks=[]
    times=[f/FPS for f in range(FRAMES)];time_accessor=b.put(times,'f','SCALAR',FRAMES,extrema=True)
    for which,name in enumerate(NAMES):
        root_idx=len(nodes);nodes.append({'name':name+'_SceneRoot','translation':[(-3.35 if which==0 else 3.35),0,0]})
        scene_roots.append(root_idx)
        joint_nodes={};abs_rest={}
        for bn,parent,xyz in JOINTS:
            abs_rest[bn]=xyz
            node={'name':name+'_'+bn,'translation':list(sub(xyz,abs_rest[parent])) if parent else list(xyz)}
            j=len(nodes);nodes.append(node);joint_nodes[bn]=j
            if parent:nodes[joint_nodes[parent]].setdefault('children',[]).append(j)
            else:nodes[root_idx].setdefault('children',[]).append(j)
        ibm=[]
        for bn,_,xyz in JOINTS:
            x,y,z=xyz
            ibm += [1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,-x,-y,-z,1.]
        skin_id=len(skins)
        ibm_accessor=b.put(ibm,'f','MAT4',len(JOINTS))
        skins.append({'name':name+'_17JointOriginalSkin','joints':[joint_nodes[x[0]] for x in JOINTS],
                      'inverseBindMatrices':ibm_accessor,'skeleton':joint_nodes['pelvis']})
        geo=figure_geometry(which);prims=[]
        for mat,vals in geo.parts.items():
            n=len(vals['p'])//3
            positions=b.put(vals['p'],'f','VEC3',n,target=34962,extrema=True)
            normals=b.put(vals['n'],'f','VEC3',n,target=34962)
            joint_attr=b.put(vals['j'],'B','VEC4',n,target=34962)
            weights=b.put(vals['w'],'f','VEC4',n,target=34962)
            ix=b.put(vals['i'],'I','SCALAR',len(vals['i']),target=34963)
            prims.append({'attributes':{'POSITION':positions,'NORMAL':normals,'JOINTS_0':joint_attr,'WEIGHTS_0':weights},
                          'indices':ix,'material':midx[mat]})
        mesh_id=len(meshes);meshes.append({'name':name+'_FullBodyStyledMesh','primitives':prims})
        meshnode=len(nodes);nodes.append({'name':name+'_SkinnedGeometry','mesh':mesh_id,'skin':skin_id})
        nodes[root_idx].setdefault('children',[]).append(meshnode)
        # Arms counter-swing; hips/knees move, head stabilizes. This is *synthetic* walking.
        channels=[];samplers=[]
        def track(node,path,values,typ):
            v=b.put(values,'f',typ,FRAMES)
            si=len(samplers);samplers.append({'input':time_accessor,'output':v,'interpolation':'LINEAR'})
            channels.append({'sampler':si,'target':{'node':node,'path':path}})
        root_values=[]
        for t in times:
            a=t/6.;x=(-3.35+2.56*a) if which==0 else (3.35-2.56*a)
            root_values += [x,0.,0.]
        track(root_idx,'translation',root_values,'VEC3')
        # Rotation amplitudes are intentionally below strenuous ROM, but not biologically certified.
        for bn in ('hip_L','hip_R','knee_L','knee_R','shoulder_L','shoulder_R','elbow_L','elbow_R','spine','head'):
            key=[]
            for f in range(FRAMES):
                phase=2*math.pi*(f/FPS)*1.25+(which*.40)
                if bn.startswith('hip_'):
                    angle=(.36 if bn.endswith('_L') else -.36)*math.sin(phase)
                elif bn.startswith('knee_'):
                    ph=phase+(0 if bn.endswith('_L') else math.pi)
                    angle=.15+.48*max(0.,math.sin(ph))
                elif bn.startswith('shoulder_'):
                    angle=(-.23 if bn.endswith('_L') else .23)*math.sin(phase)
                elif bn.startswith('elbow_'):
                    angle=(.12 if bn.endswith('_L') else -.12)+.06*math.sin(phase)
                elif bn=='spine':angle=.018*math.sin(phase*2)
                else:angle=-.016*math.sin(phase*2)
                key += quat_x(angle) if bn!='spine' else quat_z(angle)
            track(joint_nodes[bn],'rotation',key,'VEC4')
        tracks += [(channels,samplers)]
    all_ch=[];all_sm=[]
    for ch,sm in tracks:
        offset=len(all_sm);all_sm+=sm
        all_ch+=[{**c,'sampler':c['sampler']+offset} for c in ch]
    animations.append({'name':'Original72FrameParkApproach','samplers':all_sm,'channels':all_ch})
    gltf={'asset':{'version':'2.0','generator':'Stable Character R009 original-only scripted reusable character generator'},
          'extensionsUsed':[],'scene':0,'scenes':[{'name':'OriginalReusableCharacters','nodes':scene_roots}],
          'nodes':nodes,'meshes':meshes,'skins':skins,'materials':materials,'animations':animations,
          'buffers':[{'byteLength':len(b.data)}],'bufferViews':b.views,'accessors':b.accessors,
          'extras':{'source_class':'ORIGINAL_SELF_AUTHORED_SYNTHETIC','third_party_models':False,'identity_claim':False,
                    'human_gait_acceptance':'UNKNOWN','release_state':'RESEARCH_DRAFT'}}
    js=json.dumps(gltf,separators=(',',':'),sort_keys=True).encode();js+=b' ' * ((-len(js))%4)
    binary=bytes(b.data)+b'\0' * ((-len(b.data))%4)
    total=12+8+len(js)+8+len(binary)
    header=struct.pack('<4sII',b'glTF',2,total)
    payload=header+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    assert len(payload)==total
    out_path=Path(out_path);out_path.parent.mkdir(parents=True,exist_ok=True)
    out_path.write_bytes(payload)
    return {'schema':'scp.original_reusable_character.v1','status':'FORMAT_GENERATED_UNREVIEWED',
            'path':out_path.name,'sha256':hashlib.sha256(payload).hexdigest(),'bytes':len(payload),
            'characters':list(NAMES),'characters_count':2,'bone_count_per_character':len(JOINTS),
            'frames':FRAMES,'fps':FPS,'duration_seconds':6,
            'mesh_primitives':[len(x['primitives']) for x in meshes],
            'animation_channels':len(all_ch),'total_vertices':sum(a['count'] for m in meshes for p in m['primitives'] for key,idx in p['attributes'].items() if key=='POSITION' for a in [b.accessors[idx]]),
            'source':'original procedural geometry; no downloaded models, characters or clips',
            'rights':'self-authored synthetic, no external asset dependency; release license owner decision',
            'identity_verified':False,'anatomical_ROM':'UNKNOWN','foot_ground_contact':'UNKNOWN',
            'visual_acceptance':'NOT_RUN','native_blender_render':'NOT_RUN','product_accepted':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--receipt',required=True)
    a=p.parse_args();r=make_demo(a.out)
    Path(a.receipt).write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(json.dumps(r,sort_keys=True))
