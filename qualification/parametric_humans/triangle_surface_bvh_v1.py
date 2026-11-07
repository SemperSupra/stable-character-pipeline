#!/usr/bin/env python3
"""Source-pinned CPU triangle-vs-triangle contact witness for original R009 MakeHuman35.

Uses vtkCollisionDetectionFilter over fully skinned meshes in *actor-local* space.
Only establishes surface intersection pairs, NOT collision-free wearable geometry:
fully enclosed surfaces can have zero crossing pairs, and it does not validate
normals, material, self-contact, skin pressure, cloth solver, gait or Blender.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from costume_garment_v1 import _unpack_glb
from observe_makehuman35_motion_v0 import (
    parents_of,worlds,frame_poses,matrices_accessor,skin_vertices,mesh_primitive)
from retarget_makehuman_v0 import ACTORS,SCHEMA

WITNESS_SCHEMA='scp.r009.makehuman35.triangle_bvh_contact.v1'
EXPECTED_SHA256='a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739'
SLOTS=('costume_top','costume_bottom','costume_trim','footwear')

class ContactError(ValueError):pass

def make_polydata(points,triangles):
    p=np.asarray(points,dtype=np.float64)
    f=np.asarray(triangles,dtype=np.int64)
    if p.ndim!=2 or p.shape[1]!=3 or len(p)<3 or not np.isfinite(p).all():
        raise ContactError('INVALID_POSITIONS')
    if f.ndim!=2 or f.shape[1]!=3 or len(f)==0 or f.min()<0 or f.max()>=len(p):
        raise ContactError('INVALID_TRIANGLES')
    if np.any((f[:,0]==f[:,1])|(f[:,0]==f[:,2])|(f[:,1]==f[:,2])):
        raise ContactError('DUPLICATE_TRIANGLE_VERTEX')
    pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(p,deep=True))
    cells=vtk.vtkCellArray()
    offsets=np.arange(0,3*(len(f)+1),3,dtype=np.int64)
    cells.SetData(numpy_to_vtkIdTypeArray(offsets,deep=True),numpy_to_vtkIdTypeArray(f.ravel(),deep=True))
    out=vtk.vtkPolyData();out.SetPoints(pts);out.SetPolys(cells)
    return out

def contacts(a,b):
    filt=vtk.vtkCollisionDetectionFilter()
    filt.SetInputData(0,a);filt.SetInputData(1,b)
    filt.SetMatrix(0,vtk.vtkMatrix4x4());filt.SetMatrix(1,vtk.vtkMatrix4x4())
    filt.SetCollisionModeToAllContacts()
    filt.SetNumberOfCellsPerNode(10)
    filt.SetBoxTolerance(0.0);filt.SetCellTolerance(0.0)
    filt.Update()
    result=filt.GetNumberOfContacts()
    if not isinstance(result,int) or result<0:
        raise ContactError('INVALID_COLLISION_COUNT')
    return result

def _frames(selected):
    if not isinstance(selected,(tuple,list)) or not selected:
        raise ContactError('MISSING_FRAMES')
    if len(set(str(x) for x in selected))!=len(selected) or any(
            x!='rest' and (type(x) is not int or not 0<=x<72) for x in selected):
        raise ContactError('DUPLICATE_OR_INVALID_FRAME')
    if len(selected)>73:raise ContactError('TOO_MANY_FRAMES')
    return list(selected)

def inspect(raw,sha256,*,frames=('rest',0,12,24,36,48,60,71)):
    if type(sha256) is not str or len(sha256)!=64 or hashlib.sha256(raw).hexdigest()!=sha256:
        raise ContactError('SOURCE_SHA_MISMATCH')
    selected=_frames(frames)
    d,b=_unpack_glb(raw)
    if d.get('extras',{}).get('makehuman_candidate_v0',{}).get('schema')!=SCHEMA:
        raise ContactError('SOURCE_SCHEMA')
    nodes=d['nodes']
    parent=parents_of(nodes)
    rest=worlds(nodes,parent)
    pose_needed=set(i for i in selected if type(i) is int)
    poses={i:v for i,v in enumerate(frame_poses(d,b)) if i in pose_needed}
    if len(poses)!=len(pose_needed):raise ContactError('ANIMATION_INCOMPLETE')
    names={n.get('name'):i for i,n in enumerate(nodes)}
    result={'schema':WITNESS_SCHEMA,'source_sha256':sha256,
      'backend':'VTK vtkCollisionDetectionFilter / CPU actor-local skin evaluated',
      'frames':selected,'frame_count':len(selected),'actors':{},
      'vertex_signed_inclusion_qualified':False,
      'native_blender_evaluated':False,'cloth_physics_qualified':False,
      'no_triangle_crossing_proven':False,'wearable_fit_accepted':False,
      'natural_gait_accepted':False,'release_approved':False}
    for ai,actor in enumerate(ACTORS):
        skin=d['skins'][ai]
        if len(skin['joints'])!=35:raise ContactError('INVALID_SKIN_JOINT_COUNT')
        ibm=matrices_accessor(d,b,skin['inverseBindMatrices'])
        bn=names.get(actor+'_Candidate_MakeHuman_35Joint_Body')
        if bn is None or nodes[bn].get('skin')!=ai:raise ContactError('BODY_SKIN_INVALID')
        body=mesh_primitive(d,b,nodes[bn]['mesh'])
        garment={}
        for slot in SLOTS:
            ni=names.get(actor+'_Wardrobe_'+slot)
            if ni is None or nodes[ni].get('skin')!=ai:raise ContactError('GARMENT_SKIN_INVALID:'+slot)
            garment[slot]=(ni,mesh_primitive(d,b,nodes[ni]['mesh']))
        metrics={s:[] for s in SLOTS}
        for frame in selected:
            world=rest if frame=='rest' else worlds(nodes,parent,poses[frame])
            def deform(ni,mesh):
                p,j,w,f=mesh
                if frame=='rest':return p,f
                inv=np.linalg.inv(world[ni])
                matrices=np.stack([inv@world[jid]@ibm[k]
                    for k,jid in enumerate(skin['joints'])])
                return skin_vertices(p,j,w,matrices),f
            bp,bf=deform(bn,body)
            surface=make_polydata(bp,bf)
            for slot,(ni,mesh) in garment.items():
                gp,gf=deform(ni,mesh)
                count=contacts(surface,make_polydata(gp,gf))
                metrics[slot].append({'frame':frame,'triangle_contact_pairs':count,
                                      'body_triangle_count':int(len(bf)),
                                      'garment_triangle_count':int(len(gf))})
        result['actors'][actor]={'slots':metrics,'any_crossings':any(
            row['triangle_contact_pairs']>0 for arr in metrics.values() for row in arr)}
    result['any_crossings']=any(v['any_crossings'] for v in result['actors'].values())
    result['interpretation']='SURFACE_TRIANGLE_CROSSINGS_OBSERVED' if result['any_crossings'] else 'NO_CROSSINGS_IN_SAMPLED_FRAMES_ONLY'
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--all-72',action='store_true')
    a=p.parse_args()
    if a.receipt.exists() or a.input.resolve()==a.receipt.resolve():
        raise ContactError('NO_OVERWRITE')
    frames=['rest']+list(range(72)) if a.all_72 else ['rest',0,12,24,36,48,60,71]
    r=inspect(a.input.read_bytes(),a.expected_sha256,frames=frames)
    a.receipt.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'source_sha256':r['source_sha256'], 'frames':len(frames),
       'interpretation':r['interpretation'],
       'per_actor_per_slot_pairs':{actor:{slot:sum(row['triangle_contact_pairs'] for row in entries)
          for slot,entries in result['slots'].items()} for actor,result in r['actors'].items()}},sort_keys=True))

if __name__=='__main__':main()
