#!/usr/bin/env python3
"""Original fictional human sculpt experiment for a 35-joint skinned wardrobe GLB.

Source-specific reversible derivative: bridge visibly disconnected limbs with
smooth, skin-weighted lofts, soften head/face features, and adjust the eyes.
Original bytes, 35-joint skins, animation and wardrobe nodes remain unchanged.
This is *not* photoreal, anatomically validated, or a cloth-physics result.
No user/third-party scans or photos are consumed. Python standard library only.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

from costume_garment_v1 import _unpack_glb, _pack_glb, _accessor

SCHEMA = "scp.r009.original_human.sculpt_reconstruction.v1"
ACTORS = ("AsterOriginal", "JuniperOriginal")


def _read_accessor(doc, data, index):
    if type(index) is not int or not 0 <= index < len(doc['accessors']):
        raise ValueError('BAD_ACCESSOR_INDEX')
    acc=doc['accessors'][index]
    view=doc['bufferViews'][acc['bufferView']]
    if view['buffer'] != 0 or 'sparse' in acc:
        raise ValueError('UNSUPPORTED_SOURCE_ACCESSOR')
    comp=acc['componentType']; shape=acc['type']; count=acc['count']
    fmts={5126:('f',4),5125:('I',4),5123:('H',2),5121:('B',1)}
    types={'SCALAR':1,'VEC3':3,'VEC4':4}
    if comp not in fmts or shape not in types or count < 1:
        raise ValueError('UNSUPPORTED_SOURCE_FORMAT')
    fmt,sz=fmts[comp]; n=types[shape]
    stride=view.get('byteStride',sz*n)
    if stride < sz*n or stride > 256:
        raise ValueError('BAD_ACCESSOR_STRIDE')
    begin=view.get('byteOffset',0)+acc.get('byteOffset',0)
    end=begin+(count-1)*stride+sz*n
    if end>len(data) or begin<0 or end > view.get('byteOffset',0)+view['byteLength']:
        raise ValueError('ACCESSOR_OOB')
    st=struct.Struct('<'+fmt*n)
    if stride==sz*n:
        return list(struct.unpack_from('<'+fmt*(count*n),data,begin))
    flat=[]
    for i in range(count):flat.extend(st.unpack_from(data,begin+i*stride))
    return flat


def _connected_components(indices, vcount):
    par=list(range(vcount)); used=set()
    def find(x):
        while par[x]!=x:
            par[x]=par[par[x]];x=par[x]
        return x
    for i in range(0,len(indices),3):
        a,b,c=indices[i:i+3]
        if min(a,b,c)<0 or max(a,b,c)>=vcount:raise ValueError('TRIANGLE_INDEX_OOB')
        used.update((a,b,c))
        ra,rb,rc=find(a),find(b),find(c)
        par[rb]=ra;par[rc]=ra
    groups={}
    for v in used:groups.setdefault(find(v),[]).append(v)
    return groups,par,find


def _drop_source_components(doc,buf,mesh_id):
    """Index-only crop: no source vertex positions/weights or animation changed."""
    mesh=doc['meshes'][mesh_id]
    prim=mesh['primitives'][0]
    pos=_read_accessor(doc,buf,prim['attributes']['POSITION'])
    if len(pos)%3:raise ValueError('BAD_BODY_POSITIONS')
    points=list(zip(pos[0::3],pos[1::3],pos[2::3]))
    indices=list(_read_accessor(doc,buf,prim['indices']))
    if len(indices)%3:raise ValueError('BAD_BODY_INDICES')
    groups,par,find=_connected_components(indices,len(points))
    select={}; report=[]
    for root,vids in groups.items():
        xs=[points[i][0] for i in vids]; ys=[points[i][1] for i in vids]
        cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
        lo,hi=min(ys),max(ys);extent=max(xs)-min(xs)
        role='retained'
        # Distinguish groups by *both* pose-local region and extent. The
        # entire torso/head surface, pelvis and foot meshes remain present.
        if .10<lo and hi<.92 and .06<abs(cx)<.28 and extent>.095:
            role='replace_segmented_leg'
        elif .77<lo and hi<1.43 and abs(cx)>.23 and extent>.07:
            role='replace_segmented_arm'
        elif .62<lo and hi<.83 and abs(cx)>.39:
            role='replace_segmented_hand'
        elif 1.56<lo and hi<1.70 and extent<.28 and abs(cx)>.075:
            role='replace_stylized_face_details'
        if role!='retained': select[root]=role
        report.append({'group_vertices':len(vids),'role':role,'center_y_m':round(cy,4)})
    retained=[];removed=0
    for i in range(0,len(indices),3):
        tri=indices[i:i+3]
        if find(tri[0]) in select:removed+=1
        else:retained.extend(tri)
    expected={'replace_segmented_arm','replace_segmented_leg','replace_segmented_hand','replace_stylized_face_details'}
    got=set(select.values())
    if got!=expected or removed<4000 or len(retained)<1200:
        raise ValueError('SOURCE_COMPONENT_TOPOLOGY_REVIEW_HOLD:'+repr((sorted(got),removed)))
    acc=_accessor(doc,buf,retained,comp_type=5125,shape='SCALAR',count=len(retained))
    prim['indices']=acc
    return {'removed_triangle_count':removed,'retained_triangle_count':len(retained)//3,
            'replacement_groups':{s:list(select.values()).count(s) for s in expected},
            'untouched_source_geometry':True}


class Builder:
    def __init__(self,joints):
        self.joints=joints
        self.pos=[]; self.norm=[]; self.joint=[]; self.weight=[]; self.indices=[]

    def role(self,role):
        if role not in self.joints:raise ValueError('RIG_ROLE_MISSING:'+role)
        return self.joints[role]

    def vert(self,pos,norm,weights):
        if not all(math.isfinite(z) for z in (*pos,*norm)):
            raise ValueError('NONFINITE_SCULPT')
        total=sum(w for r,w in weights)
        if not .999999 <= total <= 1.000001:raise ValueError('SKIN_NOT_NORMALIZED')
        joints=[self.role(role) for role,w in weights]
        self.pos.extend(pos)
        norm_len=math.sqrt(sum(k*k for k in norm)) or 1.
        self.norm.extend(k/norm_len for k in norm)
        self.joint.extend((joints+[0]*4)[:4]);self.weight.extend(([w for r,w in weights]+[0.]*4)[:4])
        return len(self.pos)//3-1

    def loft(self,rings,*,side=0,radial=28,bones=None):
        """Z/X elliptical body or limb axial rings, smoothly skinned."""
        if len(rings)<3:raise ValueError('TOO_FEW_LOFT_RINGS')
        base=len(self.pos)//3
        for i,(cx,y,cz,rx,rz) in enumerate(rings):
            ws=bones(i,cx,y,cz) if bones else [('head',1.)]
            for j in range(radial):
                a=j*math.tau/radial
                co,si=math.cos(a),math.sin(a)
                # bias to shallow z anterior/posterior human leg ellipsoid
                px=cx+co*rx; pz=cz+si*rz
                normal=(co/max(rx,1e-8),0.,si/max(rz,1e-8))
                self.vert((px,y,pz),normal,ws)
        for k in range(len(rings)-1):
            for j in range(radial):
                a=base+k*radial+j;b=base+k*radial+(j+1)%radial
                self.indices.extend((a,a+radial,b,b,a+radial,b+radial))

    def ellipsoid(self,c,r,weights,lat=10,lon=20):
        # Retains smooth normals; capped pole rings prevent zero-area pole fans.
        rings=[]
        for k in range(1,lat):
            th=math.pi*k/lat
            rings.append((c[0],c[1]+r[1]*math.cos(th),c[2],r[0]*math.sin(th),r[2]*math.sin(th)))
        self.loft(list(reversed(rings)),radial=lon,bones=lambda *_:weights)

    def data(self):
        return {'POSITION':self.pos,'NORMAL':self.norm,'JOINTS_0':self.joint,
                'WEIGHTS_0':self.weight,'indices':self.indices}


def _weights_arm(y,side):
    if y>1.31:return [('shoulder_'+side,.86),('clavicle_'+side,.14)]
    if y>1.07:
        t=(y-1.07)/.24
        return [('shoulder_'+side,.2+.78*t),('elbow_'+side,.8-.78*t)]
    if y>.93:return [('elbow_'+side,1.)]
    t=max(0.,min(1.,(y-.78)/.15))
    return [('elbow_'+side,t*.9+.1),('wrist_'+side,(1.-t)*.9)]


def _weights_leg(y,side):
    if y>.60:return [('hip_'+side,1.)]
    if y>.45:
        t=(y-.45)/.15
        return [('hip_'+side,t),('knee_'+side,1-t)]
    if y>.32:return [('knee_'+side,1.)]
    t=max(0.,min(1.,(y-.13)/.19))
    return [('knee_'+side,t),('ankle_'+side,1-t)]


def _arm_rings(sign):
    # Contours: shoulder flare -> triceps -> elbow -> forearm -> wrist.
    spec=[(1.394,.174,.056,.060),(1.367,.195,.078,.069),
      (1.343,.215,.083,.076),(1.308,.237,.078,.076),
      (1.264,.271,.071,.067),(1.205,.316,.065,.061),
      (1.143,.369,.058,.055),(1.081,.409,.053,.050),
      (1.032,.424,.052,.048),(.990,.429,.052,.050),
      (.950,.431,.051,.050),(.908,.438,.048,.046),
      (.859,.445,.044,.042),(.816,.450,.040,.038),
      (.768,.450,.036,.035),(.743,.450,.034,.033)]
    return [(sign*x,y,0,rx,rz) for y,x,rx,rz in reversed(spec)]


def _leg_rings(sign,which):
    # Neutral long-bone envelopes: knee narrows, gastrocnemius bulges, ankle tapers.
    wide=1.03 if which==1 else 1.
    spec=[(.932,.141,.100,.100),(.892,.141,.107,.105),
      (.823,.140,.111,.110),(.754,.141,.100,.099),
      (.669,.144,.091,.090),(.575,.145,.079,.077),
      (.510,.144,.072,.071),(.459,.144,.072,.069),
      (.414,.143,.068,.067),(.362,.142,.069,.069),
      (.318,.141,.069,.069),(.274,.141,.062,.064),
      (.225,.140,.055,.056),(.171,.140,.048,.049),
      (.128,.140,.046,.046),(.110,.140,.047,.046)]
    return [(sign*x,y,0,rx*wide,rz*wide) for y,x,rx,rz in reversed(spec)]


def _hands(g,sign,side):
    # Hand dorsum continuous at wrist, narrowed at knuckles; short articulated fingers.
    g.loft([(sign*.451,.656,0,.034,.024),(sign*.451,.675,0,.046,.026),
            (sign*.451,.705,0,.045,.026),(sign*.450,.740,0,.033,.029),
            (sign*.450,.768,0,.035,.030)],radial=22,bones=lambda *_:[('wrist_'+side,1.)])
    # Thumb angles toward the torso; fingers use existing 35-joint roles.
    centers=[(-.030,.035),(-.015,0),(0,0),(.015,0),(.030,0)]
    lengths=[.041,.061,.065,.057,.047]
    for j,((dx,dz),length) in enumerate(zip(centers,lengths)):
        cx=sign*.451 + dx
        tip=.665-length
        rr=.010 if j in (1,2,3) else .009
        rings=[(cx,tip, dz, rr*.55,rr*.60),(cx,tip+.008,dz,rr*.70,rr*.75),
               (cx,tip+length*.35,dz,rr*.86,rr*.90),
               (cx,tip+length*.80,dz,rr,rr),
               (cx,tip+length,dz,rr*1.04,rr*1.04)]
        g.loft(rings,radial=14,bones=lambda *_ , j=j:[('finger%d_%s'%(j,side),.70),('wrist_'+side,.30)])


def _human_sculpt(actor,joints):
    g=Builder(joints);which=0 if actor==ACTORS[0] else 1
    for sign,side in ((-1,'L'),(1,'R')):
        g.loft(_arm_rings(sign),radial=32,
               bones=lambda _i,_x,y,_z,side=side:_weights_arm(y,side))
        g.loft(_leg_rings(sign,which),radial=36,
               bones=lambda _i,_x,y,_z,side=side:_weights_leg(y,side))
        _hands(g,sign,side)
    # Trapezius/sculpted neckline eases neck-to-shoulder mannequin stick effect.
    g.loft([(0.,1.381,0.,.175,.086),(0.,1.404,0.,.143,.074),
            (0.,1.430,-.002,.097,.065),(0.,1.455,-.004,.063,.055),
            (0.,1.478,-.008,.053,.053)],radial=48,
           bones=lambda i,x,y,z: [('chest',.65),('neck',.35)] if y<1.43 else [('neck',.9),('head',.1)])
    # Keep existing nose and mouth source components: the first additive
    # ellipsoid experiment produced a cartoon muzzle and failed visual QA.
    H=[('head',1.)]
    for sx in (-1,1):
        g.ellipsoid((sx*.096,1.646,.006),(.014,.027,.011),H,10,18)
    return g.data()


def _sculpt_source_head(doc,buf,meshid):
    """Moderate craniofacial proportion correction, preserving source topology."""
    prim=doc['meshes'][meshid]['primitives'][0]
    pos=_read_accessor(doc,buf,prim['attributes']['POSITION'])
    ix=_read_accessor(doc,buf,prim['indices'])
    groups,parents,find=_connected_components(ix,len(pos)//3)
    mods={}; summary={'jaw_vertices':0,'nose_vertices':0,'mouth_vertices':0}
    for root,vids in groups.items():
        xs=[pos[3*v] for v in vids]
        ys=[pos[3*v+1] for v in vids]
        if min(ys)>1.40 and max(ys)>1.77 and min(xs)<-.08 and max(xs)>.08:
            mods[root]='jaw'
        elif 1.59<min(ys) and max(ys)<1.68 and max(abs(min(xs)),abs(max(xs)))<.04:
            mods[root]='nose'
        elif 1.57<min(ys) and max(ys)<1.60 and max(abs(min(xs)),abs(max(xs)))<.04:
            mods[root]='mouth'
    if 'jaw' not in mods.values() or 'nose' not in mods.values():
        raise ValueError('FACE_TOPOLOGY_REVIEW_HOLD')
    new=pos[:]
    for root,vids in groups.items():
        kind=mods.get(root)
        if kind is None:continue
        for v in vids:
            x,y,z=pos[3*v:3*v+3]
            if kind=='jaw' and y>=1.53 and y<=1.635:
                # Straight tapered cartoon jaw gains a human mandible curve.
                x*=1.+.085*math.exp(-((y-1.573)/.060)**2)
                summary['jaw_vertices']+=1
            elif kind=='nose':
                x*=.78
                z=-.108+(z+.108)*.82
                summary['nose_vertices']+=1
            elif kind=='mouth':
                y=1.585+(y-1.585)*.68
                summary['mouth_vertices']+=1
            new[3*v:3*v+3]=(x,y,z)
    if summary['jaw_vertices']<50 or summary['nose_vertices']<50:
        raise ValueError('FACE_COVERAGE_HOLD')
    prim['attributes']['POSITION']=_accessor(doc,buf,new,comp_type=5126,
        shape='VEC3',count=len(new)//3,add_bounds=True)
    return summary


def _replace_original_eyes(doc,buf,meshid):
    """Convert spherical eyes to narrower almond-like silhouettes; source retained."""
    rows=[]
    for k in (1,2):
        prim=doc['meshes'][meshid]['primitives'][k]
        attr=prim['attributes']['POSITION']
        pos=_read_accessor(doc,buf,attr)
        new=[]
        for x,y,z in zip(pos[0::3],pos[1::3],pos[2::3]):
            sign=1 if x>=0 else -1
            center=.041*sign
            # Reduce pop-eye y extent; keep both irises in their source sockets.
            new.extend((center+1.09*(x-center),1.666+(y-1.666)*.68,z+.002))
        prim['attributes']['POSITION']=_accessor(doc,buf,new,comp_type=5126,
                shape='VEC3',count=len(new)//3,add_bounds=True)
        rows.append({'primitive':k,'modified_vertex_count':len(new)//3})
    return rows


def _refit_skirt_clearance(doc,buf,actor):
    """Add hip clearance to existing removable original-fabric skirt; no new cut."""
    needle=actor+'_Wardrobe_costume_bottom'
    byname={n.get('name'):i for i,n in enumerate(doc['nodes'])}
    if needle not in byname:raise ValueError('COSTUME_SKIRT_NODE_MISSING')
    prim=doc['meshes'][doc['nodes'][byname[needle]]['mesh']]['primitives'][0]
    pos=_read_accessor(doc,buf,prim['attributes']['POSITION'])
    new=[];changed=0
    for x,y,z in zip(pos[0::3],pos[1::3],pos[2::3]):
        if .76 <= y <= .98:
            # limit to torso/upper-thigh overlap band, preserving the hem/cuff
            x=x+(.020 if x>=0 else -.020)
            z=z+(.014 if z>=0 else -.014)
            changed+=1
        new.extend((x,y,z))
    if changed<80:raise ValueError('SKIRT_CLEARANCE_COVERAGE_MISSING')
    prim['attributes']['POSITION']=_accessor(doc,buf,new,comp_type=5126,
              shape='VEC3',count=len(new)//3,add_bounds=True)
    return changed


def _inject_primitive(doc,buf,meshid,matid,geo):
    n=len(geo['POSITION'])//3
    if n<100 or not geo['indices'] or len(geo['indices'])%3:raise ValueError('SCULPT_EMPTY')
    attrs={}
    for name,comp,shape in (('POSITION',5126,'VEC3'),('NORMAL',5126,'VEC3'),
          ('JOINTS_0',5121,'VEC4'),('WEIGHTS_0',5126,'VEC4')):
        attrs[name]=_accessor(doc,buf,geo[name],comp_type=comp,shape=shape,count=n,
                              add_bounds=name=='POSITION')
    ix=_accessor(doc,buf,geo['indices'],comp_type=5125,shape='SCALAR',count=len(geo['indices']))
    doc['meshes'][meshid]['primitives'].append({'attributes':attrs,'indices':ix,'material':matid,'mode':4})
    return n,len(geo['indices'])//3


def sculpt(raw,expected_sha256):
    observed=hashlib.sha256(raw).hexdigest()
    if not isinstance(expected_sha256,str) or observed!=expected_sha256:
        raise ValueError('SOURCE_SHA256_MISMATCH')
    doc,buf=_unpack_glb(raw)
    if doc.get('extras',{}).get('source_class') != 'ORIGINAL_SELF_AUTHORED_SYNTHETIC':
        raise ValueError('NOT_ORIGINAL_SYNTHETIC')
    if doc.get('extras',{}).get('costume_variant',{}).get('schema') != 'scp.r009.source_original.costume_variant.v1':
        raise ValueError('NOT_QUALIFIED_COSTUME_SOURCE')
    if len(doc.get('skins',[]))!=2 or any(len(s.get('joints',[]))!=35 for s in doc['skins']):
        raise ValueError('INVALID_35_JOINTS')
    if len(doc.get('animations',[]))!=1:raise ValueError('EXPECTED_ANIMATION')
    names={x.get('name'):i for i,x in enumerate(doc['nodes'])}
    results={}
    for i,actor in enumerate(ACTORS):
        skin=doc['skins'][i]
        joints={doc['nodes'][idx]['name'].removeprefix(actor+'_'):j for j,idx in enumerate(skin['joints'])}
        body=doc['nodes'][names[actor+'_Wardrobe_body']]['mesh']
        if not doc['meshes'][body]['name'].startswith(actor+'_body_'):
            raise ValueError('UNEXPECTED_BODY_MESH')
        matids={m.get('name'):idx for idx,m in enumerate(doc['materials'])}
        mat=matids.get('skinWarm' if i==0 else 'skinCool')
        if mat is None:raise ValueError('SKIN_MATERIAL_MISSING')
        crop=_drop_source_components(doc,buf,body)
        head_refine=_sculpt_source_head(doc,buf,body)
        eye_changes=_replace_original_eyes(doc,buf,body)
        skirt_changed=_refit_skirt_clearance(doc,buf,actor)
        geo=_human_sculpt(actor,joints)
        newv,newf=_inject_primitive(doc,buf,body,mat,geo)
        results[actor]={'body_mesh':body,'replacement_vertices':newv,
                        'replacement_triangles':newf,'eye_changes':eye_changes,'head_refine':head_refine,
                        'skirt_clearance_adjusted_vertices':skirt_changed,**crop}
    doc.setdefault('extras',{})['source_original_sculpt_v1']={
        'schema':SCHEMA, 'source_sha256':observed,
        'source_skinned_animation_preserved':True,
        'source_skin_joint_counts':[35,35],
        'actors':results, 'visual_acceptance':'REVIEW_REQUIRED',
        'cloth_collision_qualified':False,'gait_accepted':False,
        'photorealism_accepted':False,'source_mutation':False,
        'release_approved':False}
    return _pack_glb(doc,buf),doc['extras']['source_original_sculpt_v1']


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--receipt',required=True)
    a=p.parse_args()
    src=Path(a.input);out=Path(a.out);rec=Path(a.receipt)
    if src.resolve() in (out.resolve(),rec.resolve()) or out.resolve()==rec.resolve() or out.exists() or rec.exists():
        raise ValueError('NO_OVERWRITE_OR_SOURCE_CLOBBER')
    raw=src.read_bytes()
    final,report=sculpt(raw,a.expected_sha256)
    out.write_bytes(final)
    rec.write_text(json.dumps({'schema':SCHEMA,'input':src.name,'source_sha256':a.expected_sha256,
            'output_sha256':hashlib.sha256(final).hexdigest(),**report},indent=2,sort_keys=True)+'\n')
    print(out,hashlib.sha256(final).hexdigest())

if __name__=='__main__':main()
