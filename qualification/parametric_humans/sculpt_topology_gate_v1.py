#!/usr/bin/env python3
"""Fail-closed, read-only disconnected-body/skin witness for original R009 GLBs.

This measures topological connectivity, finite geometry and source provenance;
within-primitive islands are not anatomical identities. Shared positions across
primitives are NOT treated as welded, and no rig/gait/cloth/realism is accepted.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from sculpt_human_v1 import _unpack_glb, _read_accessor

SCHEMA='scp.r009.original_human.topology_quality_v1'
ACTORS=('AsterOriginal','JuniperOriginal')

class TopologyError(ValueError):
    pass

def primitive_metrics(doc,buf,primitive):
    attrs=primitive.get('attributes',{})
    needed={'POSITION','JOINTS_0','WEIGHTS_0'}
    if not needed <= attrs.keys():
        raise TopologyError('MISSING_SKIN_ATTRIBUTES')
    p=_read_accessor(doc,buf,attrs['POSITION'])
    j=_read_accessor(doc,buf,attrs['JOINTS_0'])
    w=_read_accessor(doc,buf,attrs['WEIGHTS_0'])
    ind=_read_accessor(doc,buf,primitive['indices'])
    if len(p)%3 or len(ind)%3 or len(j)!=4*len(p)//3 or len(w)!=len(j):
        raise TopologyError('ATTRIBUTE_LENGTH_MISMATCH')
    nv=len(p)//3
    if nv==0:raise TopologyError('EMPTY_GEOMETRY')
    if any(not math.isfinite(v) for v in p+w):
        raise TopologyError('NONFINITE_OR_BAD_WEIGHT')
    if any(abs(sum(w[i:i+4])-1.0)>1e-4 or min(w[i:i+4])<0 for i in range(0,len(w),4)):
        raise TopologyError('WEIGHT_SUM_OR_SIGN_INVALID')
    if any(v<0 or v>=35 for v in j):
        raise TopologyError('JOINT_INDEX_OUT_OF_RANGE')
    if any(v<0 or v>=nv for v in ind):
        raise TopologyError('TRIANGLE_INDEX_OUT_OF_RANGE')
    parents={}; used=set(); edge_count={}; degenerate=0
    def find(i):
        if i not in parents:parents[i]=i
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for k in range(0,len(ind),3):
        a,b,c=ind[k:k+3]
        if len({a,b,c})<3:
            degenerate+=1;continue
        ax,ay,az=p[3*a:3*a+3];bx,by,bz=p[3*b:3*b+3];cx,cy,cz=p[3*c:3*c+3]
        u=(bx-ax,by-ay,bz-az);v=(cx-ax,cy-ay,cz-az)
        area2=((u[1]*v[2]-u[2]*v[1])**2 + (u[2]*v[0]-u[0]*v[2])**2 + (u[0]*v[1]-u[1]*v[0])**2)
        if area2<=1e-22:degenerate+=1;continue
        used.update((a,b,c))
        root=find(a)
        for q in (b,c):parents[find(q)]=root
        for aa,bb in ((a,b),(b,c),(c,a)):
            e=(min(aa,bb),max(aa,bb));edge_count[e]=edge_count.get(e,0)+1
    islands=len({find(v) for v in used})
    return {'vertices':nv,'used_vertices':len(used), 'unused_vertices':nv-len(used),
            'triangles':len(ind)//3,'geometric_degenerate_triangles':degenerate,
            'connected_surface_islands':islands,
            'boundary_edges':sum(n==1 for n in edge_count.values()),
            'nonmanifold_edges':sum(n>2 for n in edge_count.values()),
            'joint_weight_sum_qualified':True}

def inspect(raw,expected_sha256):
    if type(raw) is not bytes or not isinstance(expected_sha256,str) or len(expected_sha256)!=64:
        raise TopologyError('MISSING_SOURCE_SHA256')
    actual=hashlib.sha256(raw).hexdigest()
    if actual!=expected_sha256:raise TopologyError('SOURCE_SHA256_MISMATCH')
    doc,buf=_unpack_glb(raw)
    if doc.get('extras',{}).get('source_class')!='ORIGINAL_SELF_AUTHORED_SYNTHETIC':
        raise TopologyError('NOT_ORIGINAL_SYNTHETIC')
    if len(doc.get('skins',[]))!=2 or any(len(s.get('joints',[]))!=35 for s in doc['skins']):
        raise TopologyError('EXPECTED_TWO_35_JOINT_SKINS')
    if len(doc.get('animations',[]))!=1:raise TopologyError('ANIMATION_ABSENT')
    actor_data={}; nodes={n.get('name'):n for n in doc['nodes']}
    for a in ACTORS:
        body=nodes.get(a+'_Wardrobe_body')
        if not body or 'mesh' not in body:raise TopologyError('BODY_NODE_MISSING:'+a)
        mesh=doc['meshes'][body['mesh']]
        rows=[primitive_metrics(doc,buf,p) for p in mesh['primitives']]
        actor_data[a]={'body_primitive_count':len(rows),
           'body_component_count':sum(m['connected_surface_islands'] for m in rows),
           'main_body_primitive_components':rows[0]['connected_surface_islands'],
           'boundary_edges_total':sum(m['boundary_edges'] for m in rows),
           'unused_vertices_total':sum(m['unused_vertices'] for m in rows),
           'triangles_total':sum(m['triangles'] for m in rows),
           'degenerate_triangles_total':sum(m['geometric_degenerate_triangles'] for m in rows),
           'primitive_metrics':rows,
           'single_connected_anatomical_surface':False,
           'anatomy_accepted':False}
    return {'schema':SCHEMA,'source_sha256':actual,
      'source_class':'ORIGINAL_SELF_AUTHORED_SYNTHETIC',
      'actors':actor_data,'connectedness_qualified_as_realistic':False,
      'source_animation_preserved_in_read_only_audit':True,
      'measurement_scope':'REST_SOURCE_GLTF_TOPOLOGY_ONLY',
      'native_blender_evaluated_frames':0,
      'cloth_collision_qualified':False,'realistic_anatomy_accepted':False,
      'release_approved':False,
      'finding':'DISCONNECTED_BODY_COMPONENTS_REMAIN' if any(
          r['main_body_primitive_components']>1 or r['body_component_count']>5
          for r in actor_data.values()) else 'TOPOLOGY_REQUIRES_INDEPENDENT_VISUAL_QA'}

def compare(before,after):
    if before['schema']!=SCHEMA or after['schema']!=SCHEMA:
        raise TopologyError('BAD_RECEIPT_SCHEMA')
    rows={}
    for a in ACTORS:
        if a not in before['actors'] or a not in after['actors']:
            raise TopologyError('MISSING_ACTOR')
        old=before['actors'][a];new=after['actors'][a]
        rows[a]={'before_body_components':old['body_component_count'],
                 'after_body_components':new['body_component_count'],
                 'component_reduction':old['body_component_count']-new['body_component_count'],
                 'before_main_components':old['main_body_primitive_components'],
                 'after_main_components':new['main_body_primitive_components'],
                 'remaining_separate_body_components':new['body_component_count'],
                 'realistic_anatomy_accepted':False}
    return {'schema':'scp.r009.original_human.topology_delta_v1',
            'actors':rows,'visual_approval':False,
            'deformation_qualification':'NOT_RUN',
            'release_approved':False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() or a.out.resolve()==a.input.resolve():
        raise TopologyError('NO_OVERWRITE')
    r=inspect(a.input.read_bytes(),a.sha256)
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'finding':r['finding'], 'actors':{k:v['body_component_count'] for k,v in r['actors'].items()}},sort_keys=True))

if __name__=='__main__':main()
