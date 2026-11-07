#!/usr/bin/env python3
"""Source-pinned, reversible MakeHuman core-CC0 anatomy/skin transfer *candidate*.

Exact MakeHuman body-only OBJ -> original fictional Aster/Juniper 35-joint
animation and separate wardrobe. Preserves source library and animated rig.
No claim of calibrated proportions, anatomically correct weighting, clothes fit,
visual human likeness, motion acceptance or production-ready retopology.

Runtime: Python 3, numpy, scipy, trimesh. Source-free gates are stdlib.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from costume_garment_v1 import _unpack_glb, _pack_glb, _accessor
from sculpt_human_v1 import _read_accessor

SCHEMA = 'scp.r009.makehuman35.retarget_candidate.v0'
SOURCE_OBJ_SHA256 = '378921118144289030c9dad2e274dadc7affd8ff394a2ac93d562252b6513de8'
SOURCE_GLB_SHA256 = '5e86d299bffbeb478d1e4945aeaefd2692ccff67dd641ef84170122a283eca1a'
# Exact first derived GLB pin for independent motion / wardrobe observers.
CANDIDATE_GLB_SHA256 = '57a4cfd1d9df7e6e2f7c2e44e68765a8ca4357895d5b075f9229b78a5bbcd36a'
ACTORS = ('AsterOriginal', 'JuniperOriginal')
DESIGN = 'classic_adventurer'
# Coordinates are manually registered research landmarks, not measured anatomical
# or retargeting ground truth. Source units are approximately decimeters.
SOURCE_Y_MIN, SOURCE_Y_MAX = -8.1676, 8.4913
TARGET_HEIGHT = 1.785
SCALE = TARGET_HEIGHT/(SOURCE_Y_MAX-SOURCE_Y_MIN)
MAX_ALLOWED_ABSOLUTE_COORDINATE = 10.0

class RetargetError(ValueError):
    pass

def _require_input(data: bytes, expected: str, label: str) -> str:
    if not isinstance(data, bytes) or len(expected)!=64 or any(c not in '0123456789abcdef' for c in expected):
        raise RetargetError('INVALID_SOURCE_PIN:'+label)
    sha=hashlib.sha256(data).hexdigest()
    if sha!=expected:
        raise RetargetError('SOURCE_SHA_MISMATCH:'+label)
    return sha

def _smootherstep(x):
    x=max(0.,min(1.,float(x)))
    return x*x*x*(x*(6*x-15)+10)

def source_to_target(points, actor):
    """Pose-aware *research registration*; continuous vertex map, no UV/topology edits.

    Arms follow the lower Aster/Juniper rest silhouette, feet move toward the
    source-original ankle anchors, mirrored Z makes positive source-forward into
    negative target-forward. Aster chest is a *provisional* male-presentation
    morph, not an approved Master/identity or sex-anatomy reconstruction.
    """
    import numpy as np
    if actor not in ACTORS:
        raise RetargetError('UNKNOWN_ACTOR')
    p=np.asarray(points,dtype=np.float64)
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all():
        raise RetargetError('INVALID_VERTICES')
    if len(p)<500 or np.max(np.abs(p))>100:
        raise RetargetError('SCALE_OR_VERTEX_COUNT_ANOMALY')
    x,y,z=p.T.copy()
    if actor=='AsterOriginal':
        # Smooth, deliberately modest synthetic male presentation experiments.
        # Chest bust flattening applies to the *anterior* central torso only.
        chest=np.array([_smootherstep((q-1.75)/1.3)*(1-_smootherstep((q-4.5)/1.3)) for q in y])
        center=np.clip((1.85-np.abs(x))/1.0,0,1)
        anterior=np.clip((z-.45)/.65,0,1)
        z=z-(z-.45)*.46*chest*center*anterior
        shoulder=np.array([_smootherstep((q-2.1)/1.2)*(1-_smootherstep((q-5.7)/1.4)) for q in y])
        x=x*(1+.045*shoulder)
    pos=np.column_stack((x*SCALE,(y-SOURCE_Y_MIN)*SCALE,-z*SCALE))
    # Torso-to-arm control is gated by Y so wide, low foot meshes never inherit
    # shoulder offsets. Smooth weight avoids a hard shoulder seam.
    xabs=np.abs(p[:,0]); arm=np.array([_smootherstep((q-1.65)/1.0) for q in xabs])
    upper=np.array([_smootherstep((q-0.1)/1.5) for q in p[:,1]])
    progress=np.clip((xabs-1.65)/3.25,0,1)
    influence=arm*upper
    pos[:,0]-=np.sign(p[:,0])*.048*(progress**1.3)*influence
    pos[:,1]-=.23*(progress**1.25)*influence
    # MakeHuman arms/hands are projected anteriorly in the source A-pose,
    # unlike Aster/Juniper's nearly neutral armature. Move distal arms toward
    # the armature's Z=0 plane continuously, without altering face/torso.
    pos[:,2]+=.235*(progress**1.1)*influence
    # Legs/ankles: retain hip width, progressively bring each leg toward its
    # original armature ankle position rather than cutting geometry apart.
    below=np.array([1-_smootherstep((q+5.6)/4.3) for q in p[:,1]])
    leg=np.array([_smootherstep((q-.65)/1.1) for q in xabs])
    pos[:,0]-=np.sign(p[:,0])*.10*below*leg
    if not np.isfinite(pos).all() or np.abs(pos).max()>MAX_ALLOWED_ABSOLUTE_COORDINATE:
        raise RetargetError('TRANSFORM_OUT_OF_BOUNDS')
    return pos.astype(np.float32)

def _weighted_source_body(doc,binbuf,actor):
    """Only USED original body vertices may provide provisional weight samples."""
    import numpy as np
    byname={n.get('name'):n for n in doc['nodes']}
    node=byname.get(actor+'_Wardrobe_body')
    if node is None or 'mesh' not in node:
        raise RetargetError('SOURCE_BODY_NOT_FOUND:'+actor)
    mesh=doc['meshes'][node['mesh']]
    p_all=[];j_all=[];w_all=[]
    for prim in mesh['primitives']:
        attrs=prim['attributes'];needed={'POSITION','JOINTS_0','WEIGHTS_0'}
        if not needed.issubset(attrs):raise RetargetError('SOURCE_SKIN_MISSING')
        pos=np.asarray(_read_accessor(doc,binbuf,attrs['POSITION']),dtype=np.float64).reshape(-1,3)
        ji=np.asarray(_read_accessor(doc,binbuf,attrs['JOINTS_0']),dtype=np.int64).reshape(-1,4)
        wt=np.asarray(_read_accessor(doc,binbuf,attrs['WEIGHTS_0']),dtype=np.float64).reshape(-1,4)
        tri=np.asarray(_read_accessor(doc,binbuf,prim['indices']),dtype=np.int64).reshape(-1,3)
        if (tri<0).any() or (tri>=len(pos)).any() or (ji<0).any() or (ji>=35).any():
            raise RetargetError('SOURCE_SKIN_INDEX_INVALID')
        used=np.unique(tri)
        p_all.append(pos[used]);j_all.append(ji[used]);w_all.append(wt[used])
    return np.concatenate(p_all),np.concatenate(j_all),np.concatenate(w_all)

def _skin_transfer(pos,source_pos,source_joints,source_weights):
    """Four-neighbor spatial borrowing; records distances and never accepts fit."""
    import numpy as np
    from scipy.spatial import cKDTree
    tree=cKDTree(source_pos)
    distances,idx=tree.query(pos,k=4,workers=1)
    if not np.isfinite(distances).all():raise RetargetError('NEAREST_NOT_FINITE')
    coeff=1./np.maximum(distances,1e-5)**2
    coeff/=np.maximum(coeff.sum(axis=1,keepdims=True),1e-10)
    # Accumulate each donor's 4 skin joints into a candidate 35-DOF vector.
    masses=np.zeros((len(pos),35),dtype=np.float64)
    rows=np.arange(len(pos))
    for neighbor in range(4):
        for slot in range(4):
            np.add.at(masses,(rows,source_joints[idx[:,neighbor],slot]),
                      coeff[:,neighbor]*source_weights[idx[:,neighbor],slot])
    selected=np.argsort(-masses,axis=1,kind='stable')[:,:4]
    chosen=np.take_along_axis(masses,selected,axis=1)
    totals=chosen.sum(axis=1,keepdims=True)
    if (totals[:,0]<=0).any():raise RetargetError('UNWEIGHTED_VERTEX')
    chosen=(chosen/totals).astype(np.float32)
    if (selected>=35).any() or (np.abs(chosen.sum(axis=1)-1)>2e-5).any():
        raise RetargetError('SKIN_WEIGHT_INVALID')
    dist=distances[:,0]
    return selected.astype(np.uint8),chosen,{
      'nearest_surface_distance_m_p50':float(np.quantile(dist,.5)),
      'nearest_surface_distance_m_p95':float(np.quantile(dist,.95)),
      'nearest_surface_distance_m_p99':float(np.quantile(dist,.99)),
      'nearest_surface_distance_m_max':float(np.max(dist)),
      'over_10cm_fraction':float(np.mean(dist>.10)),
      'over_15cm_fraction':float(np.mean(dist>.15)),
      'sample_count':len(pos),
      'weight_method':'four-nearest-donor-body-vertices-in-rest-pose',
      'pervertex_joint_sum_pass':True,
      'weight_fidelity_accepted':False}

def _accessor_vec2(doc,buf,uv):
    import struct
    import numpy as np
    data=np.asarray(uv,dtype=np.float32)
    if data.ndim!=2 or data.shape[1]!=2 or not np.isfinite(data).all():
        raise RetargetError('INVALID_UV')
    while len(buf)%4:buf.append(0)
    offset=len(buf)
    payload=data.astype('<f4').tobytes(order='C')
    buf.extend(payload)
    view=len(doc['bufferViews'])
    doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(payload)})
    idx=len(doc['accessors'])
    doc['accessors'].append({'bufferView':view,'componentType':5126,'count':len(data),'type':'VEC2'})
    return idx

def _mesh_geometry(obj):
    import trimesh
    import numpy as np
    mesh=trimesh.load(obj,file_type='obj',process=False,force='mesh')
    pos=np.asarray(mesh.vertices,dtype=np.float64)
    faces=np.asarray(mesh.faces,dtype=np.int64)
    uv=getattr(mesh.visual,'uv',None)
    if uv is None or uv.shape!=(len(pos),2):raise RetargetError('UV_MISSING')
    if len(pos)<13000 or len(pos)>16000 or len(faces)!=26756:
        raise RetargetError('UNEXPECTED_BODY_ONLY_TOPOLOGY')
    if np.min(faces)<0 or np.max(faces)>=len(pos):raise RetargetError('FACE_OUT_OF_BOUNDS')
    # Geometry connectedness must be verified independently with UV splits welded.
    if len(np.unique(np.round(pos,5),axis=0))!=13380:
        raise RetargetError('SOURCE_BODY_WELD_COUNT_MISMATCH')
    return pos,faces,np.asarray(uv,dtype=np.float32)

def _vertex_normals(pos,faces):
    import numpy as np
    normals=np.zeros_like(pos,dtype=np.float64)
    a,b,c=pos[faces[:,0]],pos[faces[:,1]],pos[faces[:,2]]
    cross=np.cross(b-a,c-a)
    if not np.isfinite(cross).all():raise RetargetError('NORMAL_NONFINITE')
    for col in range(3):np.add.at(normals,faces[:,col],cross)
    lengths=np.linalg.norm(normals,axis=1)
    if (lengths<1e-13).sum():
        # Do not invent a normal for isolated vertices.
        raise RetargetError('ISOLATED_VERTEX_NORMAL')
    return (normals/lengths[:,None]).astype(np.float32)

def derive(glb:bytes,obj:bytes,*,expected_glb=SOURCE_GLB_SHA256,expected_obj=SOURCE_OBJ_SHA256):
    """Return (reversible GLB, nonpromoting read-only receipt)."""
    import numpy as np
    _require_input(glb,expected_glb,'original_character')
    _require_input(obj,expected_obj,'cc0_body')
    doc,buf=_unpack_glb(glb)
    if doc.get('extras',{}).get('source_class')!='ORIGINAL_SELF_AUTHORED_SYNTHETIC':
        raise RetargetError('SOURCE_CLASS_REJECTED')
    if len(doc.get('skins',[]))!=2 or any(len(s.get('joints',[]))!=35 for s in doc['skins']) or len(doc.get('animations',[]))!=1:
        raise RetargetError('SOURCE_RIG_AND_CLIP_REQUIRED')
    import io
    rawpos,faces,uv=_mesh_geometry(io.BytesIO(obj))
    # Coordinate calibration reflects source-forward +Z into target-forward -Z;
    # flip triangle winding to retain outward-facing normals and signed volume.
    faces=faces[:,[0,2,1]]
    witnesses={}
    nodes={n.get('name'):i for i,n in enumerate(doc['nodes'])}
    for ai,actor in enumerate(ACTORS):
        pos=source_to_target(rawpos,actor)
        old_p,old_j,old_w=_weighted_source_body(doc,buf,actor)
        joints,weights,qa=_skin_transfer(pos,old_p,old_j,old_w)
        norm=_vertex_normals(pos,faces)
        attrs={}
        for k,typ,shape,v in [
            ('POSITION',5126,'VEC3',pos.ravel().tolist()),
            ('NORMAL',5126,'VEC3',norm.ravel().tolist()),
            ('JOINTS_0',5121,'VEC4',joints.ravel().astype(int).tolist()),
            ('WEIGHTS_0',5126,'VEC4',weights.ravel().tolist())]:
            attrs[k]=_accessor(doc,buf,v,comp_type=typ,shape=shape,count=len(pos),add_bounds=k=='POSITION')
        attrs['TEXCOORD_0']=_accessor_vec2(doc,buf,uv)
        idx=_accessor(doc,buf,faces.ravel().astype(int).tolist(),comp_type=5125,shape='SCALAR',count=faces.size)
        mat=0 if ai==0 else 1
        meshid=len(doc['meshes'])
        doc['meshes'].append({'name':actor+'_MakeHuman_CC0_BodyOnly_Retarget_V0',
                              'primitives':[{'attributes':attrs,'indices':idx,'material':mat,'mode':4}]})
        ni=len(doc['nodes']);doc['nodes'].append({'name':actor+'_Candidate_MakeHuman_35Joint_Body',
          'mesh':meshid,'skin':ai,'extras':{'source_license':'CC0-1.0',
          'actor':actor,'candidate_only':True,'realism_accepted':False,
          'animation_accepted':False,'garment_accepted':False}})
        root=nodes[actor+'_SceneRoot']
        old=nodes[actor+'_Wardrobe_body']
        # Keep entire original body geometry and original mesh in the GLB library;
        # only hide its old scene graph binding in this reversible derivative.
        original_mesh=doc['nodes'][old].pop('mesh')
        old_skin=doc['nodes'][old].pop('skin')
        if old_skin!=ai:raise RetargetError('SOURCE_SKIN_MAPPING_CHANGED')
        doc['nodes'][old].setdefault('extras',{})['inactive_source_mesh_id']=original_mesh
        doc['nodes'][root].setdefault('children',[]).append(ni)
        witnesses[actor]={**qa,'geometry_mesh_id':meshid,'candidate_node_id':ni,
          'inactive_original_body_mesh_id':original_mesh,
          'retarget_method':'unmeasured-landmark-pose-warp-and-four-nearest-source-weight-proxy',
          'vertex_count':len(pos),'triangle_count':len(faces),
          'UV_preserved':True,'original_skeleton_untouched':True,
          'original_animation_untouched':True,'morphology_presentation':
           'provisional-masculine-bust-reduction_not_accepted' if ai==0 else 'source-template-feminine_not_accepted',
          'anatomical_realism_accepted':False,'garment_fit_accepted':False}
    doc.setdefault('extras',{})['makehuman_candidate_v0']={
        'schema':SCHEMA,'makehuman_source_sha256':expected_obj,
        'origin':'MakeHuman core CC0 visible body only',
        'source_glb_sha256':expected_glb,
        'body_visibility':'candidate body replaces scene visible old body; original source retained',
        'source_class':'mixed original-fictional rig + CC0 body asset',
        'rig_accepted':False,'morphology_accepted':False,
        'motion_accepted':False,'cloth_collision_accepted':False,
        'release_approved':False}
    out=_pack_glb(doc,buf)
    receipt={'schema':SCHEMA,'source_character_glb_sha256':expected_glb,
       'source_makehuman_obj_sha256':expected_obj,'output_sha256':hashlib.sha256(out).hexdigest(),
       'source_geometry_retained':True,'source_animations_retained':True,
       'UV_seam_split_vertices':len(rawpos), 'source_body_geometric_vertices':13380,
       'source_body_quads':13378,'candidate_body_triangles':len(faces),
       'actors':witnesses,'technical_file_build':True,'rigging_accepted':False,
       'native_blender_motion_tested':False,'garment_collision_accepted':False,
       'human_visual_accepted':False,'source_licensing':('MakeHuman CC0 CORE BODY; '
       'project-original character/wardrobe subject to separate existing terms'),
       'release_approved':False}
    return out,receipt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-glb',type=Path,required=True)
    p.add_argument('--makehuman-obj',type=Path,required=True)
    p.add_argument('--output-glb',type=Path,required=True)
    p.add_argument('--receipt',type=Path,required=True)
    args=p.parse_args()
    paths=[x.resolve() for x in (args.source_glb,args.makehuman_obj,args.output_glb,args.receipt)]
    if len(set(paths))!=4 or args.output_glb.exists() or args.receipt.exists():
        raise RetargetError('NO_OVERWRITE_OR_ALIAS')
    glb,receipt=derive(args.source_glb.read_bytes(),args.makehuman_obj.read_bytes())
    args.output_glb.write_bytes(glb)
    args.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'output_sha256':receipt['output_sha256'],
        'actors':{a:round(r['nearest_surface_distance_m_p95'],4) for a,r in receipt['actors'].items()},
        'qualification':'SOURCE_PINNED_FILE_BUILD_ONLY'}))

if __name__=='__main__':main()
