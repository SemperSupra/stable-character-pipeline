#!/usr/bin/env python3
"""R009 original-only, cross-sectional fitted shoe-last *research* prototype.

Builds separately skinned, capped geometric shoe lasts from exact CC0-body
cross-sections, not by projecting old shoe triangles. Includes deterministic
source hashes, strict topology, rest contact and source preservation checks.
Still NOT footwear realism, valid shoe opening, ground-contact, native Blender
or 72-frame collision acceptance.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy,numpy_to_vtk,numpy_to_vtkIdTypeArray
from scipy.spatial import ConvexHull
from costume_garment_v1 import _unpack_glb,_pack_glb,_accessor
from sculpt_human_v1 import _read_accessor
from observe_makehuman35_garment_v0 import polygon_mesh,signed_distance
from retarget_makehuman_v0 import ACTORS,SCHEMA as BODY_SCHEMA
from scipy.spatial import cKDTree

def transfer_foot_weights(vertices,body_positions,body_joints,body_weights):
    """Source-local k=4 bounded inverse distance transfer, UV seam-aware."""
    v=np.asarray(vertices,float).reshape(-1,3)
    bp=np.asarray(body_positions,float).reshape(-1,3)
    j=np.asarray(body_joints,int).reshape(-1,4)
    w=np.asarray(body_weights,float).reshape(-1,4)
    if len(bp)!=len(j) or len(bp)!=len(w) or not np.isfinite(v).all() or not np.isfinite(bp).all():
        raise LastError('INVALID_BODY_WEIGHT_INPUT')
    if (j<0).any() or (j>34).any() or (w<0).any() or not np.isfinite(w).all():
        raise LastError('INVALID_BODY_WEIGHTS')
    dist,idx=cKDTree(bp).query(v,k=4)
    if dist.max()>.065:raise LastError('SOURCE_FOOT_LANDMARK_DISTANCE_TOO_LARGE')
    influence=1/np.maximum(dist,1e-5)**2
    influence/=influence.sum(axis=1,keepdims=True)
    vec=np.zeros((len(v),35),dtype=np.float64)
    rows=np.arange(len(v))
    for k in range(4):
        for slot in range(4):
            np.add.at(vec,(rows,j[idx[:,k],slot]),influence[:,k]*w[idx[:,k],slot])
    order=np.argsort(-vec,axis=1)[:,:4]
    values=np.take_along_axis(vec,order,axis=1)
    values/=np.maximum(values.sum(axis=1,keepdims=True),1e-12)
    if np.max(abs(values.sum(axis=1)-1))>1e-5:raise LastError('FAILED_NORMALIZATION')
    return order.astype(np.uint8),values.astype(np.float32),float(np.quantile(dist[:,0],.95))

SOURCE_SHA256="366fc2964e0e156988b0207735d89b8dbba18d6b92d0ac453e0d4fc7846fe99f"
SCHEMA="scp.r009.synthetic_footwear_cross_section_last.v1"
Z_SLICES=(-.200,-.190,-.180,-.165,-.150,-.130,-.110,-.090,-.070,-.050,-.030,-.010,.010,.030,.045)
EASE_M=.011
OPENING_Y=.140
RADIAL=48
class LastError(ValueError):pass

def _slice(poly,z,side):
    p=vtk.vtkPlane();p.SetOrigin(0,0,float(z));p.SetNormal(0,0,1)
    c=vtk.vtkCutter();c.SetCutFunction(p);c.SetInputData(poly);c.Update()
    out=c.GetOutput()
    if out.GetNumberOfPoints()<8:raise LastError('INSUFFICIENT_FOOT_SECTION')
    ps=vtk_to_numpy(out.GetPoints().GetData()).copy().astype(float)
    ps=ps[(ps[:,0]*side>.04)&(ps[:,1]<.24)]
    if len(ps)<8 or np.linalg.norm(np.ptp(ps[:,:2],axis=0))==0:
        raise LastError('MISSING_FOOT_CROSS_SECTION')
    return ps

def last_geometry(poly,side,*,ease=EASE_M,radial=RADIAL):
    if type(side) is not int or side not in (-1,1):raise LastError('SIDE_REQUIRED')
    if not(type(ease) in (float,int) and math.isfinite(ease) and .005<=ease<=.030):
        raise LastError('INVALID_EASE')
    if type(radial) is not int or radial<32 or radial>96 or radial%8:raise LastError('INVALID_RADIAL')
    sections=[];sec_witness=[]
    angle=np.arange(radial)*2*math.pi/radial
    directions=np.stack([np.cos(angle),np.sin(angle)],axis=1)
    for z in Z_SLICES:
        pts=_slice(poly,z,side)
        xy=pts[:,:2]
        center=(xy.min(axis=0)+xy.max(axis=0))*.5
        # True radial intersection with a convex-hull halfspace, then ease.
        # Unlike treating support h(theta) as radial distance, this does not
        # grossly inflate diagonals or cross into the opposite foot.
        hull=ConvexHull(xy)
        center=xy[hull.vertices].mean(axis=0)  # convex combination = inside
        planes=hull.equations
        rhs=-(planes[:,:2]@center+planes[:,2])
        denom=planes[:,:2]@directions.T
        ratios=np.where(denom>1e-9,rhs[:,None]/np.maximum(denom,1e-9),np.inf)
        r=ratios.min(axis=0)+ease
        if r.min()<.005:raise LastError('DEGENERATE_SECTION')
        ring=np.column_stack((center[0]+r*np.cos(angle),center[1]+r*np.sin(angle),np.full(radial,z)))
        sections.append(ring)
        sec_witness.append({'z_m':z,'sample_count':len(pts),'min_radius_m':float(r.min()),
                            'max_radius_m':float(r.max())})
    sections=np.array(sections,np.float64)
    # Add compact rounded toe and heel caps, with consistent outward orientation.
    first=sections[0]
    last=sections[-1]
    toe_center=first.mean(axis=0);heel_center=last.mean(axis=0)
    toe_ring=toe_center+.20*(first-toe_center);toe_ring[:,2]=Z_SLICES[0]-.015
    heel_ring=heel_center+.30*(last-heel_center);heel_ring[:,2]=Z_SLICES[-1]+.017
    rings=np.concatenate([toe_ring[None],sections,heel_ring[None]],axis=0)
    v=rings.reshape(-1,3)
    toe_id=len(v);heel_id=toe_id+1
    v=np.vstack([v,toe_center+np.array([0,0,-.018]),heel_center+np.array([0,0,.020])])
    faces=[]
    for k in range(len(rings)-1):
        for j in range(radial):
            a=k*radial+j;b=k*radial+(j+1)%radial
            c=(k+1)*radial+j;d=(k+1)*radial+(j+1)%radial
            faces.extend([(a,b,c),(b,d,c)])
    endbase=(len(rings)-1)*radial
    for j in range(radial):
        nex=(j+1)%radial
        faces.append((toe_id,nex,j))
        faces.append((heel_id,endbase+j,endbase+nex))
    f=np.asarray(faces,dtype=np.int32)
    normals=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    area=np.linalg.norm(normals,axis=1)*.5
    if (area<1e-10).any():raise LastError('DEGENERATE_LAST_FACES')
    # Each lateral ring has consistent nonzero outward x/y normal.
    mids=f[:(len(rings)-1)*radial*2]
    n=np.cross(v[mids[:,1]]-v[mids[:,0]],v[mids[:,2]]-v[mids[:,0]])
    mid=(v[mids[:,0]]+v[mids[:,1]]+v[mids[:,2]])/3
    # Outward radial orientation excluding complicated toe/heel cap direction.
    cx=np.repeat(rings.mean(axis=1)[:-1,:2],radial*2,axis=0)
    cc=np.column_stack((cx,np.zeros(len(cx))))
    if np.mean(np.einsum('ij,ij->i',n[:,:2],(mid-cc)[:,:2])<0)>.05:
        raise LastError('INVERTED_LAST_WINDING')
    # A shoe must have an ankle opening: trim the anatomical last's upper
    # surface without adding a fake closure cap across the leg. This removes
    # the previously measured ankle-body penetration, while keeping the toe
    # and heel shaped by verified cross-sections.
    points=vtk.vtkPoints();points.SetData(numpy_to_vtk(v.astype(np.float64),deep=True))
    cells=vtk.vtkCellArray()
    cells.SetData(numpy_to_vtkIdTypeArray(np.arange(0,3*(len(f)+1),3,dtype=np.int64),deep=True),
                  numpy_to_vtkIdTypeArray(f.astype(np.int64).ravel(),deep=True))
    poly=vtk.vtkPolyData();poly.SetPoints(points);poly.SetPolys(cells)
    plane=vtk.vtkPlane();plane.SetOrigin(0,OPENING_Y,0);plane.SetNormal(0,1,0)
    clip=vtk.vtkClipPolyData();clip.SetInputData(poly)
    clip.SetClipFunction(plane);clip.InsideOutOn();clip.Update()
    tri=vtk.vtkTriangleFilter();tri.SetInputConnection(clip.GetOutputPort());tri.Update()
    mesh=tri.GetOutput()
    v=vtk_to_numpy(mesh.GetPoints().GetData()).copy().astype(np.float32)
    f=np.array([[mesh.GetCell(i).GetPointId(k) for k in range(3)]
                for i in range(mesh.GetNumberOfCells())],dtype=np.int32)
    if len(v)<400 or len(f)<700 or v[:,1].max()>OPENING_Y+1e-6:
        raise LastError('SHOE_OPENING_CUT_FAILED')
    areas=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)*.5
    if (areas<1e-10).any():raise LastError('SHOE_OPENING_DEGENERACY')
    return v,f,sec_witness

def derive(raw,expected_sha256=SOURCE_SHA256):
    src_sha=hashlib.sha256(raw).hexdigest()
    if src_sha!=expected_sha256:raise LastError('SOURCE_SHA_MISMATCH')
    doc,b=_unpack_glb(raw)
    if doc.get('extras',{}).get('makehuman_candidate_v0',{}).get('schema')!=BODY_SCHEMA:
        raise LastError('INCOMPATIBLE_CC0_BODY')
    prefix=bytes(b)
    names={n.get('name'):n for n in doc['nodes']}
    rec={}
    for ai,actor in enumerate(ACTORS):
        bn=names[actor+'_Candidate_MakeHuman_35Joint_Body']
        footwear=names[actor+'_Wardrobe_footwear']
        if bn.get('skin')!=ai or footwear.get('skin')!=ai or len(doc['skins'][ai]['joints'])!=35:
            raise LastError('RIG_MISMATCH')
        prim=doc['meshes'][bn['mesh']]['primitives'][0]
        attrs=prim['attributes']
        verts=np.array(_read_accessor(doc,b,attrs['POSITION']),np.float32).reshape(-1,3)
        faces=np.array(_read_accessor(doc,b,prim['indices']),np.int32).reshape(-1,3)
        joints=np.array(_read_accessor(doc,b,attrs['JOINTS_0']),np.int32).reshape(-1,4)
        weights=np.array(_read_accessor(doc,b,attrs['WEIGHTS_0']),np.float32).reshape(-1,4)
        poly=polygon_mesh(verts,faces)
        i=vtk.vtkImplicitPolyDataDistance();i.SetInput(poly)
        inside=i.EvaluateFunction((0,1.15,0));outside=i.EvaluateFunction((0,1.15,-1))
        sign=(-1 if inside>.005 and outside<-.1 else 1 if inside<-.005 and outside>.1 else 0)
        if not sign:raise LastError('BODY_SIGN_NOT_CALIBRATED')
        allv=[];allf=[];allj=[];allw=[];samples=[]
        for side in (-1,1):
            v,f,wit=last_geometry(poly,side)
            j,w,d95=transfer_foot_weights(v,verts,joints,weights)
            sd=sign*signed_distance(poly,v)
            fraction=float(np.mean(sd<-.005))
            if fraction>.02:raise LastError('SHOE_LAST_SOURCE_PENETRATION')
            off=len(allv)
            allv.extend(v.tolist());allf.extend((f+off).tolist());allj.extend(j.tolist());allw.extend(w.tolist())
            samples.append({'side':side,'vertices':len(v),'triangles':len(f),
              'negative_gt_5mm_fraction':fraction,'signed_p10_m':float(np.quantile(sd,.1)),
              'source_weight_nearest_p95_m':d95,'cross_sections':wit})
        v=np.asarray(allv,np.float32);f=np.asarray(allf,np.int32)
        j=np.asarray(allj,np.int32);w=np.asarray(allw,np.float32)
        ns=np.zeros_like(v)
        face_n=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
        for k in range(3):np.add.at(ns,f[:,k],face_n)
        norm=np.linalg.norm(ns,axis=1)
        if (norm<1e-9).any():raise LastError('INVALID_LAST_VERTEX_NORMAL')
        ns/=norm[:,None]
        original_prim=doc['meshes'][footwear['mesh']]['primitives'][0]
        nprim={'attributes':{
          'POSITION':_accessor(doc,b,v.ravel().tolist(),comp_type=5126,shape='VEC3',count=len(v),add_bounds=True),
          'NORMAL':_accessor(doc,b,ns.ravel().tolist(),comp_type=5126,shape='VEC3',count=len(v)),
          'JOINTS_0':_accessor(doc,b,j.ravel().tolist(),comp_type=5121,shape='VEC4',count=len(v)),
          'WEIGHTS_0':_accessor(doc,b,w.ravel().tolist(),comp_type=5126,shape='VEC4',count=len(v)),
        },'indices':_accessor(doc,b,f.ravel().tolist(),comp_type=5125,shape='SCALAR',count=len(f)*3),
        'material':original_prim['material'],'mode':4}
        new_id=len(doc['meshes'])
        doc['meshes'].append({'name':actor+'_Footwear_CrossSectionLast_Research_v1','primitives':[nprim]})
        footwear.setdefault('extras',{})['pre_fit_mesh_id']=footwear['mesh']
        footwear['extras']['unaccepted_technical_fit']=True
        footwear['mesh']=new_id
        rec[actor]=samples
    if bytes(b[:len(prefix)])!=prefix:raise LastError('SOURCE_PREFIX_MUTATED')
    doc.setdefault('extras',{})['footwear_last_research_v1']={
       'schema':SCHEMA,'source_sha256':src_sha,'source_geometry_preserved':True,
       'rig_35_joint_and_motion_preserved':True,'shoe_opening_geometry_verified':False,'top_cut_y_m':OPENING_Y,
       'native_blender_evaluated':False,'motion_accepted':False,'release_approved':False}
    out=_pack_glb(doc,b)
    return out,{'schema':SCHEMA,'source_sha256':src_sha,'derived_sha256':hashlib.sha256(out).hexdigest(),
                'actors':rec,'source_binary_prefix_preserved':True,'human_accepted':False,
                '72_frame_native_contact_qualified':False,'release_approved':False}

def main():
    a=argparse.ArgumentParser();a.add_argument('--input',required=True,type=Path)
    a.add_argument('--output',required=True,type=Path);a.add_argument('--receipt',required=True,type=Path)
    args=a.parse_args()
    if len({args.input.resolve(),args.output.resolve(),args.receipt.resolve()})!=3 or args.output.exists() or args.receipt.exists():
        raise LastError('NO_OVERWRITE')
    o,r=derive(args.input.read_bytes())
    args.output.write_bytes(o);args.receipt.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'sha256':r['derived_sha256'],
           'shoe_penetration':{actor:[(x['side'],x['negative_gt_5mm_fraction']) for x in rs] for actor,rs in r['actors'].items()}}))
if __name__=='__main__':main()
