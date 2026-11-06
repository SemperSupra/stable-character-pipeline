#!/usr/bin/env python3
"""Signed body/wardrobe static and sparse-frame penetration falsifier.

Blender cloth simulation, pressure, UV collision response, authentic fitting and
all-frame motion-quality acceptance are expressly NOT provided by this proxy.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
from scipy.spatial.transform import Rotation
from costume_garment_v1 import _unpack_glb
from sculpt_human_v1 import _read_accessor
from retarget_makehuman_v0 import ACTORS, SCHEMA
from observe_makehuman35_motion_v0 import (
  parents_of, worlds, frame_poses, matrices_accessor, skin_vertices, mesh_primitive)

GARMENT_SCHEMA='scp.r009.makehuman35.signed_wardrobe_contact_sample.v0'
FRAMES=('rest',0,24,48,71)

def polygon_mesh(positions,triangles):
    pos=np.asarray(positions,dtype=np.float64)
    faces=np.asarray(triangles,dtype=np.int64)
    points=vtk.vtkPoints();points.SetData(numpy_to_vtk(pos,deep=True))
    cells=vtk.vtkCellArray()
    offsets=np.arange(0,3*(len(faces)+1),3,dtype=np.int64)
    cells.SetData(numpy_to_vtkIdTypeArray(offsets,deep=True),
                  numpy_to_vtkIdTypeArray(faces.ravel(),deep=True))
    mesh=vtk.vtkPolyData();mesh.SetPoints(points);mesh.SetPolys(cells)
    clean=vtk.vtkCleanPolyData();clean.SetInputData(mesh)
    clean.PointMergingOn();clean.Update()
    norms=vtk.vtkPolyDataNormals();norms.SetInputConnection(clean.GetOutputPort())
    norms.AutoOrientNormalsOn();norms.ConsistencyOn();norms.SplittingOff();norms.Update()
    return norms.GetOutput()

def signed_distance(mesh,points):
    f=vtk.vtkImplicitPolyDataDistance();f.SetInput(mesh)
    return np.asarray([f.EvaluateFunction(tuple(x)) for x in points],dtype=np.float64)

def inspect(raw,source_sha):
    if hashlib.sha256(raw).hexdigest()!=source_sha:raise ValueError('CANDIDATE_SOURCE_SHA_MISMATCH')
    d,b=_unpack_glb(raw)
    if d.get('extras',{}).get('makehuman_candidate_v0',{}).get('schema')!=SCHEMA:
        raise ValueError('CANDIDATE_SCHEMA')
    nodes=d['nodes'];parent=parents_of(nodes)
    rest=worlds(nodes,parent)
    anim={i:p for i,p in enumerate(frame_poses(d,b)) if i in (0,24,48,71)}
    result={'schema':GARMENT_SCHEMA,'source_sha256':source_sha,
      'witness_frames':list(FRAMES),'actors':{},
      'full_motion_72_frame_collision_qualified':False,
      'native_blender_evaluated':False,'cloth_fitting_accepted':False,'release_approved':False}
    for ai,actor in enumerate(ACTORS):
        skin=d['skins'][ai]
        ibm=matrices_accessor(d,b,skin['inverseBindMatrices'])
        bodynode=next(i for i,n in enumerate(nodes) if n['name']==actor+'_Candidate_MakeHuman_35Joint_Body')
        bp,bj,bw,bf=mesh_primitive(d,b,nodes[bodynode]['mesh'])
        wardrobe=[]
        for slot in ('costume_top','costume_bottom','costume_trim','footwear'):
            nodename=actor+'_Wardrobe_'+slot
            ni=next((i for i,n in enumerate(nodes) if n['name']==nodename),None)
            if ni is None:raise ValueError('MISSING_CLOTHING:'+nodename)
            p,j,w,tri=mesh_primitive(d,b,nodes[ni]['mesh'])
            wardrobe.append((slot,ni,p,j,w,tri))
        witnesses={slot:[] for slot,*_ in wardrobe}
        for label in FRAMES:
            world=rest if label=='rest' else worlds(nodes,parent,anim[label])
            def relative(ni):
                inv=np.linalg.inv(world[ni])
                return np.stack([inv@world[jid]@ibm[k]
                        for k,jid in enumerate(skin['joints'])])
            body=bp if label=='rest' else skin_vertices(bp,bj,bw,relative(bodynode))
            polys=polygon_mesh(body,bf)
            # Per-frame sign calibration, else fail CLOSED rather than inventing
            # a purported inside-body percentage from an unoriented surface.
            waist_inside=float(signed_distance(polys,np.array([[0,1.15,0]]))[0])
            waist_outside=float(signed_distance(polys,np.array([[0,1.15,-1]]))[0])
            sign_multiplier=(1 if waist_inside<-.005 and waist_outside>.1
                   else -1 if waist_inside>.005 and waist_outside<-.1
                   else 0)
            sign_ok=sign_multiplier!=0
            for slot,ni,p,j,w,tri in wardrobe:
                gp=p if label=='rest' else skin_vertices(p,j,w,relative(ni))
                distances=sign_multiplier*signed_distance(polys,gp)
                row={'frame':label,'samples':len(gp),'signed_distance_m_min':float(distances.min()),
                  'signed_distance_m_p10':float(np.quantile(distances,.10)),
                  'signed_distance_m_p50':float(np.quantile(distances,.50)),
                  'negative_gt_5mm_fraction':float(np.mean(distances<-.005)) if sign_ok else None,
                  'near_surface_lt_10mm_fraction':float(np.mean(np.abs(distances)<.01)),
                  'sign_calibration_interior_distance_m':waist_inside,
                  'sign_calibration_exterior_distance_m':waist_outside,
                  'sign_calibrated':bool(sign_ok),
                  'sign_multiplier':sign_multiplier,'penetration_accepted':False}
                witnesses[slot].append(row)
        result['actors'][actor]={'slots':witnesses,'all_sign_calibrated':all(
             v['sign_calibrated'] for rows in witnesses.values() for v in rows),
             'cloth_fitting_accepted':False}
    result['scientific_first_failure']='SIGNED_INCLUSION_CONTACT_REQUIRES_CORRECTION' if any(
        any(row['negative_gt_5mm_fraction'] is not None and row['negative_gt_5mm_fraction']>.05
             for rows in a['slots'].values() for row in rows)
        for a in result['actors'].values()) else 'CONTACT_NOT_QUALIFIED'
    return result

def main():
    a=argparse.ArgumentParser();a.add_argument('--glb',required=True,type=Path)
    a.add_argument('--out',required=True,type=Path)
    a.add_argument('--expected-sha256',required=True);q=a.parse_args()
    if q.out.exists() or q.out.resolve()==q.glb.resolve():raise ValueError('NO_OVERWRITE')
    raw=q.glb.read_bytes();r=inspect(raw,q.expected_sha256)
    q.out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'finding':r['scientific_first_failure'],
          'signed':{a:{slot:round(rows[0]['negative_gt_5mm_fraction'],3) if rows[0]['negative_gt_5mm_fraction'] is not None else None
             for slot,rows in v['slots'].items()} for a,v in r['actors'].items()}}))

if __name__=='__main__':main()
