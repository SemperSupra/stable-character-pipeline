#!/usr/bin/env python3
"""Opt-in source-original 35-joint BODY-SURFACE morphology experiment.

Uses only existing R009 self-authored procedural geometry and unchanged 35-joint
source. Does not retarget skeleton, fit garments, preserve volume, simulate
surgery, or establish human realism. Constrained geometry preview ONLY.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parent/"original_reusable_characters"
sys.path.insert(0,str(ORIGINAL))
import parameters_v1 as contract
import modular_wardrobe_v1 as wardrobe

def influence(y,center,spread):
    return math.exp(-0.5*((y-center)/spread)**2)

def apply_original_shape(which,state):
    """Return NEW source-owned Geometry with original part/index/skin counts.

    Only source-original skin surface vertices are touched, not clothing;
    the current 35-joint rest poses are intentionally fixed. We assert no
    topology change, but do not assert anatomy or cloth collision clearance.
    """
    contract.validate(state)
    g=wardrobe.adult_body_geometry(which)
    skin="skinWarm" if which==0 else "skinCool"
    part=g.parts[skin]
    coords=part["p"]
    original=tuple(coords)
    m=state["morphology"]
    waist_delta=max(-.20,min(.20,(m["waist_circumference_m"]/.78-1.0)*.22))
    hip_delta=max(-.20,min(.20,(m["hip_circumference_m"]/.98-1.0)*.20))
    jaw_delta=max(-.16,min(.16,(m["jaw_width_ratio"]-1.)*.35))
    nose_delta=max(-.025,min(.025,(m["nose_projection_ratio"]-1.)*.025))
    left_volume=(m["left_breast_volume"]-.5)*.032
    right_volume=(m["right_breast_volume"]-.5)*.032
    changed=0
    for k in range(0,len(coords),3):
        x,y,z=coords[k:k+3]
        nx,nz=x,z
        if .77<=y<=1.45:
            scale=1 + waist_delta*influence(y,1.04,.13)+hip_delta*influence(y,.87,.12)
            nx=x*scale
            nz=z*(1+(scale-1)*.65)
        if 1.49<=y<=1.76:
            nx*=1+jaw_delta*influence(y,1.61,.073)
            if z < -.082 and 1.59<y<1.68 and abs(x)<.048:
                nz+=nose_delta*influence(y,1.635,.034)
        if 1.17<y<1.39 and z<-.045 and .025<abs(x)<.17:
            volume=left_volume if x<0 else right_volume
            nx+=math.copysign(abs(volume)*.10*influence(y,1.29,.06), x) if volume>0 else 0
            nz-=volume*influence(y,1.28,.065)*influence(abs(x),.09,.06)
        if abs(nx-x)+abs(nz-z)>1e-9:
            changed+=1
        coords[k],coords[k+2]=nx,nz
    # Recompute skin-surface vertex normals after spatial deformation.
    normals=[0.]*len(coords)
    indices=part["i"]
    for i in range(0,len(indices),3):
        a,b,c=(indices[i]*3,indices[i+1]*3,indices[i+2]*3)
        ax,ay,az=coords[a:a+3]
        bx,by,bz=coords[b:b+3]
        cx,cy,cz=coords[c:c+3]
        ux,uy,uz=bx-ax,by-ay,bz-az
        vx,vy,vz=cx-ax,cy-ay,cz-az
        nx,ny,nz=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx
        for base in (a,b,c):
            normals[base]+=nx
            normals[base+1]+=ny
            normals[base+2]+=nz
    for k in range(0,len(coords),3):
        nx,ny,nz=normals[k:k+3]
        length=math.sqrt(nx*nx+ny*ny+nz*nz)
        if length>1e-12:
            normals[k:k+3]=[nx/length,ny/length,nz/length]
        else:
            normals[k:k+3]=part["n"][k:k+3]
    part["n"]=normals
    assert len(coords)==len(original)==len(part["n"])
    assert len(part["j"])==4*len(coords)//3
    assert len(part["w"])==4*len(coords)//3
    return g,{"actor":wardrobe.ACTORS[which],"vertices_unchanged":len(coords)//3,
              "vertices_position_modified":changed,
              "indices_unchanged":len(indices),
              "skin_index_count_unchanged":len(part["j"]),
              "source_geometry_preview":True,
              "rig_rest_retargeted":False,"wardrobe_collision_qualified":False,
              "anatomical_qualified":False}

def build(aster,juniper,out,manifest,receipt,as_of=None):
    for path in (out,manifest,receipt):
        if Path(path).exists():
            raise FileExistsError("REFUSE_OVERWRITE:"+str(path))
    state=[contract.snapshot(p,as_of) if as_of else p for p in (aster,juniper)]
    for p in state:contract.validate(p)
    witnesses={}
    parent_function=wardrobe.h.v1.figure_geometry
    try:
        def wrapped(which):
            geometry,proof=apply_original_shape(which,state[which])
            witnesses[wardrobe.ACTORS[which]]=proof
            return geometry
        wardrobe.h.v1.figure_geometry=wrapped
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"source_17.glb"
            expanded=root/"source_35.glb"
            gait=root/"source_72.glb"
            wardrobe.h.v1.make_demo(source)
            wardrobe.main_expand(source,expanded)
            wardrobe.animate(expanded,gait)
            manifest_body=wardrobe.split_skinned_layers(gait,out,manifest)
    finally:
        wardrobe.h.v1.figure_geometry=parent_function
    payload=Path(out).read_bytes()
    result={"schema":"scp.r009.original_human_morph_preview35.v1",
      "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
      "derived_glb_sha256":hashlib.sha256(payload).hexdigest(),
      "input_parameter_sha256":[contract.sha256(p) for p in (aster,juniper)],
      "original_source_sha256":{
        f:hashlib.sha256((ORIGINAL/f).read_bytes()).hexdigest()
        for f in ("modular_wardrobe_v1.py","humanization_v2.py","generate_original_glb.py")},
      "as_of":as_of,"witnesses":witnesses,
      "manifest_sha256":hashlib.sha256(Path(manifest).read_bytes()).hexdigest(),
      "rig_joint_count":35,"frames":72,
      "mesh_topology_preserved":True,
      "scientific_status":"UNKNOWN_NOT_ANATOMICALLY_OR_CLOTHING_QUALIFIED",
      "source_mutation":False,"release_approved":False}
    Path(receipt).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--aster",required=True,type=Path)
    p.add_argument("--juniper",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--receipt",required=True,type=Path)
    p.add_argument("--as-of")
    a=p.parse_args()
    aster=json.loads(a.aster.read_text(encoding="utf-8"))
    juniper=json.loads(a.juniper.read_text(encoding="utf-8"))
    proof=build(aster,juniper,a.out,a.manifest,a.receipt,a.as_of)
    print(json.dumps({"glb_sha256":proof["derived_glb_sha256"],
      "topology_preserved":True,"scientific_status":proof["scientific_status"]},
      sort_keys=True))

if __name__=="__main__":
    main()
