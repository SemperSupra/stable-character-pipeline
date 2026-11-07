#!/usr/bin/env python3
"""Reversible research garment-clearance projection against CC0 candidate body.

This is a first-pass *vertex* clearance experiment, not a pattern re-fit,
cloth collision proof, dynamic fit, anatomy acceptance, or production export.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import vtk
from costume_garment_v1 import _unpack_glb,_pack_glb,_accessor
from sculpt_human_v1 import _read_accessor
from retarget_makehuman_v0 import _vertex_normals,ACTORS,SCHEMA,CANDIDATE_GLB_SHA256
from observe_makehuman35_garment_v0 import polygon_mesh, signed_distance

SCHEMA_FIT='scp.r009.makehuman35.rest_clearance_projection.v0'
CLEARANCE_M=.015
MAX_STEP_M=.20

class ClearanceError(ValueError): pass

def project_points(bodypoly,points,clearance_m=CLEARANCE_M):
    f=vtk.vtkImplicitPolyDataDistance();f.SetInput(bodypoly)
    waist=f.EvaluateFunction((0,1.15,0))
    outside=f.EvaluateFunction((0,1.15,-1))
    if waist>.005 and outside<-.1:mult=-1
    elif waist<-.005 and outside>.1:mult=1
    else:raise ClearanceError('UNTRUSTED_DISTANCE_SIGN')
    pts=np.asarray(points,dtype=np.float64)
    dist=mult*np.array([f.EvaluateFunction(tuple(p)) for p in pts])
    grad=np.empty_like(pts)
    for i,p in enumerate(pts):
        v=[0.,0.,0.];f.EvaluateGradient(tuple(p),v)
        grad[i]=mult*np.asarray(v)
    gradlen=np.linalg.norm(grad,axis=1)
    if np.any(gradlen<1e-9):raise ClearanceError('ZERO_GRADIENT')
    need=np.maximum(0,clearance_m-dist)
    if max(need)>MAX_STEP_M:raise ClearanceError('PROJECTION_STEP_EXCEEDS_BOUND')
    output=pts+need[:,None]*grad/gradlen[:,None]
    revised=mult*np.asarray([f.EvaluateFunction(tuple(x)) for x in output])
    return output.astype(np.float32),{
      'initial_inside_gt_5mm_fraction':float(np.mean(dist<-.005)),
      'post_inside_gt_5mm_fraction':float(np.mean(revised<-.005)),
      'initial_signed_distance_p50_m':float(np.median(dist)),
      'post_signed_distance_p50_m':float(np.median(revised)),
      'projection_95pct_m':float(np.quantile(need,.95)),
      'projection_max_m':float(np.max(need)),
      'touched_vertices':int(np.sum(need>0)),
      'vertex_count':len(pts),
      'signed_distance_multiplier':mult,
      'rest_clearance_accepted':False,
      'dynamic_clearance_accepted':False}

def derive(raw,expected_sha256=CANDIDATE_GLB_SHA256):
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ClearanceError('SOURCE_SHA_MISMATCH')
    d,b=_unpack_glb(raw)
    if d.get('extras',{}).get('makehuman_candidate_v0',{}).get('schema')!=SCHEMA:
        raise ClearanceError('INCORRECT_SOURCE_SCHEMA')
    names={n['name']:n for n in d['nodes']}
    witnesses={}
    for actor in ACTORS:
        body=names[actor+'_Candidate_MakeHuman_35Joint_Body']
        pr=d['meshes'][body['mesh']]['primitives'][0]
        bp=np.asarray(_read_accessor(d,b,pr['attributes']['POSITION']),dtype=np.float32).reshape(-1,3)
        bf=np.asarray(_read_accessor(d,b,pr['indices']),dtype=np.int32).reshape(-1,3)
        poly=polygon_mesh(bp,bf)
        witnesses[actor]={}
        for slot in ('costume_top','costume_bottom','costume_trim'):
            node=names[actor+'_Wardrobe_'+slot]
            original=node['mesh']
            source=d['meshes'][original]
            if len(source['primitives'])!=1:raise ClearanceError('EXPECTED_ONE_GARMENT_PRIMITIVE')
            prim=source['primitives'][0]
            ps=np.asarray(_read_accessor(d,b,prim['attributes']['POSITION']),dtype=np.float32).reshape(-1,3)
            fs=np.asarray(_read_accessor(d,b,prim['indices']),dtype=np.int32).reshape(-1,3)
            # First grade the whole garment cut radially; then only correct local
            # remaining penetrations. This is less destructive than projecting
            # all deeply-embedded vertices individually from the old source.
            staged=ps.copy()
            radial_grade={'costume_top':1.22,'costume_bottom':1.12,'costume_trim':1.20}[slot]
            staged[:,[0,2]]*=radial_grade
            new,w=project_points(poly,staged)
            w['radial_grading_factor']=radial_grade
            beforeedges=np.linalg.norm(ps[fs[:,1]]-ps[fs[:,0]],axis=1)
            afteredges=np.linalg.norm(new[fs[:,1]]-new[fs[:,0]],axis=1)
            if np.any(afteredges<1e-6):raise ClearanceError('GARMENT_DEGENERATE_AFTER')
            faceold=np.cross(ps[fs[:,1]]-ps[fs[:,0]],ps[fs[:,2]]-ps[fs[:,0]])
            facenew=np.cross(new[fs[:,1]]-new[fs[:,0]],new[fs[:,2]]-new[fs[:,0]])
            inversion=float(np.mean(np.einsum('ij,ij->i',faceold,facenew)<0))
            w['face_normal_direction_reversal_fraction']=inversion
            w['max_edge_stretch']=float(np.max(afteredges/np.maximum(beforeedges,1e-9)))
            w['old_mesh_retained_id']=original
            # Clone the old skinned primitive, replacing ONLY position and normals
            # accessors, preserving joint/weight/UV/source material reference.
            updated=json.loads(json.dumps(prim))
            updated['attributes']['POSITION']=_accessor(d,b,new.ravel().tolist(),comp_type=5126,
                                            shape='VEC3',count=len(new),add_bounds=True)
            updated['attributes']['NORMAL']=_accessor(d,b,_vertex_normals(new,fs).ravel().tolist(),
                                      comp_type=5126,shape='VEC3',count=len(new))
            mid=len(d['meshes'])
            d['meshes'].append({'name':actor+'_'+slot+'_signed_rest_clearance_candidate',
                                'primitives':[updated]})
            node['mesh']=mid
            node.setdefault('extras',{})['original_skin_mesh_retained_id']=original
            node['extras']['rest_clearance_candidate_only']=True
            witnesses[actor][slot]=w
    d.setdefault('extras',{})['wardrobe_clearance_candidate_v0']={
      'schema':SCHEMA_FIT,'source_sha256':expected_sha256,'original_geometry_preserved':True,
      'source_clothing_mesh_library_preserved':True,'rig_animation_preserved':True,
      'full_motion_collision_qualified':False,'realistic_garment_cut_accepted':False,
      'release_approved':False}
    out=_pack_glb(d,b)
    receipt={'schema':SCHEMA_FIT,'source_sha256':expected_sha256,
      'derived_sha256':hashlib.sha256(out).hexdigest(),
      'actors':witnesses,'native_cloth_qualified':False,
      'sparse_frame_contact_accepted':False,
      'source_unchanged':True,'release_approved':False}
    return out,receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    if len({a.source.resolve(),a.out.resolve(),a.receipt.resolve()})!=3 or a.out.exists() or a.receipt.exists():
        raise ClearanceError('NO_OVERWRITE')
    raw=a.source.read_bytes();out,receipt=derive(raw)
    a.out.write_bytes(out);a.receipt.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'sha':receipt['derived_sha256'],
      'actors':{a:{s:[round(r['initial_inside_gt_5mm_fraction'],3),round(r['post_inside_gt_5mm_fraction'],3),round(r['projection_max_m'],3),round(r['face_normal_direction_reversal_fraction'],3)]
            for s,r in slots.items()} for a,slots in receipt['actors'].items()}}))

if __name__=='__main__':main()
