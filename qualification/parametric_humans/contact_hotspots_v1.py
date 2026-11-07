#!/usr/bin/env python3
"""Source-pinned R009 triangle contact-face attribution, CPU witness only.

Reports actual VTK face pairs at original armholes and skirt yokes, never
claims cloth, anatomical, actor identity or wearable clearance acceptance.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from costume_garment_v1 import _unpack_glb
from observe_makehuman35_motion_v0 import parents_of,worlds,frame_poses,matrices_accessor,skin_vertices,mesh_primitive
from triangle_surface_bvh_v1 import make_polydata
from retarget_makehuman_v0 import ACTORS,SCHEMA

SOURCE_SHA256='ae2b809ffa5cf5dfee0adf2f6b88b0a864e3588b95638de4c8b86e83a6e524af'
SCHEMA_OUT='scp.r009.triangle_contact_face_atlas.v1'
SLOTS=('costume_top','costume_bottom')
FULL_FRAMES=('rest',*range(72))
FALSE_SCIENCE={k:False for k in ('native_blender_evaluated','physical_cloth_qualified','full_72_frames_evaluated','garment_fit_accepted','release_approved')}
class AtlasError(ValueError):pass

def face_pairs(body_surface, garment_surface):
    f=vtk.vtkCollisionDetectionFilter()
    f.SetInputData(0,body_surface);f.SetInputData(1,garment_surface)
    f.SetMatrix(0,vtk.vtkMatrix4x4());f.SetMatrix(1,vtk.vtkMatrix4x4())
    f.SetCollisionModeToAllContacts();f.SetNumberOfCellsPerNode(10)
    f.SetBoxTolerance(0.0);f.SetCellTolerance(0.0);f.Update()
    n=f.GetNumberOfContacts()
    if n<0:raise AtlasError('NEGATIVE_CONTACT_COUNT')
    if n==0:return np.empty((0,2),dtype=np.int64)
    a=np.asarray(vtk_to_numpy(f.GetContactCells(0)),dtype=np.int64)
    b=np.asarray(vtk_to_numpy(f.GetContactCells(1)),dtype=np.int64)
    if len(a)!=n or len(b)!=n:raise AtlasError('ID_PAIR_LENGTH_MISMATCH')
    return np.column_stack((a,b))

def hotspot_rows(pairs,body_p,body_f,garment_p,garment_f,limit=16):
    if pairs.ndim!=2 or pairs.shape[1]!=2 or (len(pairs) and (pairs.min()<0 or pairs[:,0].max()>=len(body_f) or pairs[:,1].max()>=len(garment_f))):
        raise AtlasError('BAD_CONTACT_FACE_IDS')
    bc=collections.Counter(int(i) for i in pairs[:,0]);gc=collections.Counter(int(i) for i in pairs[:,1])
    def report(freq,p,f):
        out=[]
        for face,count in sorted(freq.items(),key=lambda x:(-x[1],x[0]))[:limit]:
            centroid=np.asarray(p[f[face]],dtype=np.float64).mean(axis=0)
            if not np.isfinite(centroid).all():raise AtlasError('NONFINITE_HOTSPOT')
            out.append({'face_index':face,'contact_count':count,'centroid_m':[round(float(q),6) for q in centroid]})
        return out
    return {'pairs':len(pairs),'body_distinct_faces':len(bc),'garment_distinct_faces':len(gc),
            'body_hotspots':report(bc,body_p,body_f),'garment_hotspots':report(gc,garment_p,garment_f)}

def audit(raw,frames=('rest',0,12,16,24,36,48,60,71)):
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:raise AtlasError('SOURCE_SHA_MISMATCH')
    if type(frames) not in (tuple,list) or not frames or len(frames)>73 or len(set(map(str,frames)))!=len(frames) or any(f not in FULL_FRAMES for f in frames):
        raise AtlasError('FRAME_SELECTION_INVALID')
    d,b=_unpack_glb(raw)
    if d.get('extras',{}).get('makehuman_candidate_v0',{}).get('schema')!=SCHEMA:raise AtlasError('MISSING_CC0_RETARGET_CONTRACT')
    nodes=d['nodes'];names={n.get('name'):i for i,n in enumerate(nodes)}
    parents=parents_of(nodes);rest=worlds(nodes,parents)
    needed={f for f in frames if type(f) is int}
    poses={i:p for i,p in enumerate(frame_poses(d,b)) if i in needed}
    if set(poses)!=needed:raise AtlasError('MOTION_FRAMES_MISSING')
    out={'schema':SCHEMA_OUT,'source_sha256':SOURCE_SHA256,'frames':list(frames),'frame_count':len(frames),
         'backend':'VTK CPU actor-local evaluated triangle-pair IDs','actors':{},**FALSE_SCIENCE}
    for ai,actor in enumerate(ACTORS):
        skin=d['skins'][ai]
        if len(skin['joints'])!=35:raise AtlasError('WRONG_SKIN')
        ibm=matrices_accessor(d,b,skin['inverseBindMatrices'])
        bn=names.get(actor+'_Candidate_MakeHuman_35Joint_Body')
        if bn is None or nodes[bn].get('skin')!=ai:raise AtlasError('BODY_SKIN_MISMATCH')
        body=mesh_primitive(d,b,nodes[bn]['mesh'])
        garments={}
        for slot in SLOTS:
            ni=names.get(actor+'_Wardrobe_'+slot)
            if ni is None or nodes[ni].get('skin')!=ai:raise AtlasError('GARMENT_SKIN_MISMATCH')
            garments[slot]=(ni,mesh_primitive(d,b,nodes[ni]['mesh']))
        frame_rows={slot:[] for slot in SLOTS}
        for frame in frames:
            world=rest if frame=='rest' else worlds(nodes,parents,poses[frame])
            def deform(ni,mesh):
                p,j,w,f=mesh
                if frame=='rest':return p,f
                inv=np.linalg.inv(world[ni])
                matrices=np.stack([inv@world[jid]@ibm[k] for k,jid in enumerate(skin['joints'])])
                return skin_vertices(p,j,w,matrices),f
            bp,bf=deform(bn,body);bs=make_polydata(bp,bf)
            for slot,(ni,mesh) in garments.items():
                gp,gf=deform(ni,mesh)
                pair=face_pairs(bs,make_polydata(gp,gf))
                row={'frame':frame,**hotspot_rows(pair,bp,bf,gp,gf)}
                frame_rows[slot].append(row)
        out['actors'][actor]={slot:{'total_pairs':sum(row['pairs'] for row in rows),'sampled_frames':rows} for slot,rows in frame_rows.items()}
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--frame',action='append')
    args=ap.parse_args()
    if args.input.resolve()==args.out.resolve() or args.out.exists():raise AtlasError('NO_OVERWRITE')
    fs=tuple('rest' if x=='rest' else int(x) for x in args.frame) if args.frame else ('rest',0,12,16,24,36,48,60,71)
    r=audit(args.input.read_bytes(),fs)
    args.out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'sha256':SOURCE_SHA256,'frames':list(fs),'pair_totals':{a:{s:v['total_pairs'] for s,v in slots.items()} for a,slots in r['actors'].items()},'promoted':False},sort_keys=True))
if __name__=='__main__':main()
