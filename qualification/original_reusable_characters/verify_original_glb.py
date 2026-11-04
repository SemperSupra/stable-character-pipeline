#!/usr/bin/env python3
"""Independent structural/kinematic GLB observer. Does not import the producer."""
import argparse,hashlib,json,math,struct
from pathlib import Path

class WitnessError(Exception):pass

def check(cond, code):
    if not cond:raise WitnessError(code)

def decode(data):
    check(len(data)>=32 and data[:4]==b'glTF','GLB_INVALID_HEADER')
    magic,version,total=struct.unpack_from('<4sII',data)
    check(version==2 and total==len(data),'GLB_BAD_LENGTH')
    n,typ=struct.unpack_from('<I4s',data,12)
    check(typ==b'JSON' and 20+n+8<=total,'GLB_NO_JSON')
    try:d=json.loads(data[20:20+n])
    except (UnicodeError,ValueError) as e:raise WitnessError('GLB_INVALID_JSON') from e
    start=20+n;size,typ=struct.unpack_from('<I4s',data,start)
    check(typ==b'BIN\0' and start+8+size==total,'GLB_BINARY_SIZE')
    return d,data[start+8:]

def accessory(d,bb,idx):
    a=d['accessors'][idx];v=d['bufferViews'][a['bufferView']]
    check(v['buffer']==0 and 'byteStride' not in v,'UNSUPPORTED_BUFFER_LAYOUT')
    c={5121:('B',1),5123:('H',2),5125:('I',4),5126:('f',4)}[a['componentType']]
    n={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
    start=v['byteOffset']+a.get('byteOffset',0);count=a['count']*n
    check(start>=0 and start+count*c[1]<=v['byteOffset']+v['byteLength'] and start+count*c[1]<=len(bb),'ACCESSOR_OUT_OF_BOUNDS')
    vals=struct.unpack_from('<'+c[0]*count,bb,start)
    return [vals[i:i+n] for i in range(0,len(vals),n)]

def verify(path):
    p=Path(path);raw=p.read_bytes();d,bb=decode(raw)
    check(d.get('asset',{}).get('version')=='2.0','GLTF_VERSION')
    check(d.get('extras',{}).get('source_class')=='ORIGINAL_SELF_AUTHORED_SYNTHETIC' and d['extras'].get('third_party_models') is False,'SOURCE_CLASS_MISSING')
    check(d['extras'].get('human_gait_acceptance')=='UNKNOWN','FALSE_HUMAN_ACCEPTANCE')
    check(len(d.get('skins',[]))==2 and len(d.get('meshes',[]))==2,'TWO_SKINNED_CHARACTERS_REQUIRED')
    check(len(d['animations'])==1,'SINGLE_APPROACH_CLIP_REQUIRED')
    roots=[n for n in d['nodes'] if n['name'].endswith('_SceneRoot')]
    check(len(roots)==2,'TWO_ACTOR_ROOTS_REQUIRED')
    skin_nodes=[n for n in d['nodes'] if 'skin' in n]
    check(len(skin_nodes)==2 and set(x['skin'] for x in skin_nodes)=={0,1},'RIG_SKIN_BINDING')
    vertices=0;triangles=0;blend_vertices=0;material_groups=0
    for mesh,skin in zip(d['meshes'],d['skins']):
        check(len(skin['joints'])==17 and len(set(skin['joints']))==17,'JOINT_COUNT_OR_DUPLICATE')
        check('inverseBindMatrices' in skin,'INVERSE_BIND_MISSING')
        ibm=accessory(d,bb,skin['inverseBindMatrices'])
        check(len(ibm)==17,'INVERSE_BIND_COUNT')
        material_groups+=len(mesh['primitives'])
        for primitive in mesh['primitives']:
            attrs=primitive['attributes']
            check({'POSITION','NORMAL','WEIGHTS_0','JOINTS_0'}.issubset(attrs),'SKIN_ATTRIBUTES_MISSING')
            position=accessory(d,bb,attrs['POSITION']);normals=accessory(d,bb,attrs['NORMAL']);weights=accessory(d,bb,attrs['WEIGHTS_0']);joints=accessory(d,bb,attrs['JOINTS_0']);indices=accessory(d,bb,primitive['indices'])
            check(len(position)==len(normals)==len(weights)==len(joints),'SKIN_ATTRIBUTE_COUNT')
            check(len(indices)%3==0,'BAD_TRIANGLE_INDEX_COUNT')
            check(all(0<=x[0]<len(position) for x in indices),'TRIANGLE_INDEX_OUT_OF_RANGE')
            for xyz,n,w,j in zip(position,normals,weights,joints):
                check(all(math.isfinite(x) for x in xyz+n+w),'NONFINITE_VERTEX_OR_WEIGHT')
                check(all(0<=k<17 for k in j),'JOINT_INDEX_OUT_OF_RANGE')
                check(abs(sum(w)-1)<1e-5 and min(w)>=0,'WEIGHTS_NOT_NORMALIZED')
                if w[0]>1e-5 and w[1]>1e-5:blend_vertices+=1
            vertices+=len(position);triangles+=len(indices)//3
    check(vertices>=8000 and material_groups>=14 and blend_vertices>=300,'INSUFFICIENT_OR_UNBLENDED_GEOMETRY')
    anim=d['animations'][0];check(len(anim['channels'])>=20,'ANIMATION_INCOMPLETE')
    roots_i={idx for idx,n in enumerate(d['nodes']) if n['name'].endswith('_SceneRoot')}
    found_root_tracks=[];rotation_nodes=set()
    for channel in anim['channels']:
        sampler=anim['samplers'][channel['sampler']]
        times=[x[0] for x in accessory(d,bb,sampler['input'])]
        check(len(times)==72 and times[0]==0 and abs(times[-1]-71/12)<1e-5,'FRAME_CLOCK_MISMATCH')
        check(all(times[k]<times[k+1] for k in range(len(times)-1)),'FRAME_CLOCK_NONMONOTONIC')
        vals=accessory(d,bb,sampler['output'])
        check(len(vals)==72 and sampler['interpolation']=='LINEAR','ANIMATION_CHANNEL_INVALID')
        node=channel['target']['node'];kind=channel['target']['path']
        if kind=='rotation':
            rotation_nodes.add(node)
            check(all(abs(sum(x*x for x in q)-1)<1e-4 for q in vals),'NONUNIT_QUATERNION')
        if kind=='translation' and node in roots_i:found_root_tracks.append(vals)
    check(len(found_root_tracks)==2 and len(rotation_nodes)>=18,'ANIMATION_TRACK_COVERAGE')
    initial=abs(found_root_tracks[0][0][0]-found_root_tracks[1][0][0]);final=abs(found_root_tracks[0][-1][0]-found_root_tracks[1][-1][0])
    check(initial>=6 and final<initial-4.5 and final>1.,'ACTORS_NOT_APPROACHING')
    return {'schema':'scp.original_reusable_independent_witness.v1','status':'GLB_FORMAT_SKIN_ANIMATION_PASS_VISUAL_UNKNOWN',
            'sha256':hashlib.sha256(raw).hexdigest(),'characters':2,'skeleton_joints_each':17,
            'frames':72,'fps':12,'animated_rotation_joints':len(rotation_nodes),
            'triangles':triangles,'vertices':vertices,'blended_vertices':blend_vertices,
            'material_groups':material_groups,'initial_separation_m':round(initial,4),
            'final_separation_m':round(final,4),'native_render':'NOT_RUN',
            'human_gait':'UNKNOWN','contact':'UNKNOWN','rights':'ORIGINAL_SYNTHETIC_NO_THIRD_PARTY_MODEL_INPUT'}
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--input',required=True);a.add_argument('--receipt',required=True);x=a.parse_args()
    try:r=verify(x.input)
    except WitnessError as e:raise SystemExit('INDEPENDENT_WITNESS_REJECT:'+str(e))
    Path(x.receipt).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps(r,sort_keys=True))
