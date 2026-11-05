#!/usr/bin/env python3
"""Opt-in original-only R009 torso continuity and genuinely different outfit cuts.

Derives from the frozen v1 wardrobe source. No downloaded model or protected
identity. Keeps the v1 actor/skin/node/slot contract and source bytes unchanged.
A continuous torso-neck-head surface is NOT a watertight full human body.
"""
import argparse
import hashlib
import json
import math
import struct
import tempfile
from pathlib import Path

import humanization_v2 as h
import modular_wardrobe_v1 as v1
from phase_gait35 import animate
from rig35_v2 import main_expand, glb_pack
from verify_original_glb import decode, accessory

def continuous_figure(which):
    """Replace independent torso and face lofts by one weighted trunk/head loft.

    Hands/limbs remain inherited overlapping surfaces pending full retopology.
    Preserve parent clothing, face decorations, hair, armature and source names.
    """
    original = h.loft_anatomy
    skin = "skinWarm" if which == 0 else "skinCool"
    counts = {"head_removed": 0, "trunk_replaced": 0}
    def intercept(g, mat, rings, bones, sides=32):
        lo, hi = rings[0][0], rings[-1][0]
        if mat == skin and lo > 1.4 and hi > 1.7:
            counts["head_removed"] += 1
            return  # replaced by a contiguous trunk-to-cranium loft
        if mat == skin and lo < .9 and 1.40 < hi < 1.5:
            counts["trunk_replaced"] += 1
            merged = list(rings)
            # The trunk's terminal radius connects directly to neck/head.
            # Radial order and ring indexing stay continuous at every level.
            merged.extend([
                (1.480,-.003,.052,.054),
                (1.500,-.008,.053,.054),
                (1.519,-.013,.060,.060),
                (1.548,-.013,.072,.072),
                (1.574,-.010,.081,.083),
                (1.611,0,.091 if which==0 else .088,.095),
                (1.657,0,.102 if which==0 else .096,.105),
                (1.701,.008,.102 if which==0 else .097,.106),
                (1.737,.019,.085,.093),
                (1.766,.025,.052,.062),
                (1.785,.028,.005,.010)])
            def spine_to_head(y):
                if y <= 1.38:
                    return bones(y)
                if y <= 1.48:
                    blend=max(0.,min(1.,(1.48-y)/.10))
                    return ("chest","neck",blend)
                blend=max(0.,min(1.,(1.56-y)/.08))
                return ("neck","head",blend)
            return original(g,mat,merged,spine_to_head,sides=36)
        return original(g,mat,rings,bones,sides=sides)
    try:
        h.loft_anatomy = intercept
        geo = v1.adult_body_geometry(which)
    finally:
        h.loft_anatomy = original
    if counts != {"head_removed":1,"trunk_replaced":1}:
        raise ValueError("TOPOLOGY_REPLACEMENT_UNEXPECTED:"+str(counts))
    return geo

def _append(d, binary, values, kind, fmt, count, target=None):
    while len(binary) % 4: binary.append(0)
    offset=len(binary)
    binary.extend(struct.pack("<"+fmt*len(values),*values))
    view={"buffer":0,"byteOffset":offset,"byteLength":struct.calcsize(fmt)*len(values)}
    if target: view["target"]=target
    view_id=len(d["bufferViews"])
    d["bufferViews"].append(view)
    acc_id=len(d["accessors"])
    d["accessors"].append({"bufferView":view_id,"componentType":{"B":5121,"I":5125,"f":5126}[fmt],
        "count":count,"type":kind})
    return acc_id

def _rings(skin_index, names, rings, sides=28):
    """Surface of revolution with per-ring two-bone skin blend."""
    vertices=[]; normals=[]; joints=[]; weights=[]; indices=[]
    for k,(cy,cx,cz,rx,rz,role0,role1,blend) in enumerate(rings):
        if not (rx>0 and rz>0 and 0<=blend<=1):
            raise ValueError("INVALID_CUT_RING")
        if k and cy<=rings[k-1][0]:
            raise ValueError("NONMONOTONIC_CUT")
        for j in range(sides):
            angle=math.tau*j/sides
            co,si=math.cos(angle),math.sin(angle)
            vertices.extend((cx+rx*co,cy,cz+rz*si))
            nx,nz=co/rx,si/rz
            nn=math.hypot(nx,nz)
            normals.extend((nx/nn,0,nz/nn))
            joints.extend((skin_index[role0],skin_index[role1],0,0))
            weights.extend((blend,1-blend,0,0))
    for k in range(len(rings)-1):
        for j in range(sides):
            a=k*sides+j;b=k*sides+(j+1)%sides
            indices.extend((a,a+sides,b,b,a+sides,b+sides))
    return vertices,normals,joints,weights,indices

def _combine(*surfaces):
    out=[[],[],[],[],[]]
    for surface in surfaces:
        count=len(out[0])//3
        for idx,values in enumerate(surface):
            out[idx].extend((v+count for v in values) if idx==4 else values)
    return out

def _mesh_primitive(d,b,mesh,material,geom):
    pos,nor,joints,weights,indices=geom
    n=len(pos)//3
    if not (n>0 and len(nor)==3*n and len(joints)==4*n
            and len(weights)==4*n and len(indices)%3==0):
        raise ValueError("CUT_VERTEX_FORMAT")
    for i in range(n):
        if any(j>=35 for j in joints[4*i:4*i+4]):
            raise ValueError("CUT_INVALID_JOINT")
        if abs(sum(weights[4*i:4*i+4])-1)>1e-6:
            raise ValueError("CUT_BAD_WEIGHT")
    attrs={
      "POSITION":_append(d,b,pos,"VEC3","f",n,34962),
      "NORMAL":_append(d,b,nor,"VEC3","f",n,34962),
      "JOINTS_0":_append(d,b,joints,"VEC4","B",n,34962),
      "WEIGHTS_0":_append(d,b,weights,"VEC4","f",n,34962)}
    idx=_append(d,b,indices,"SCALAR","I",len(indices),34963)
    d["meshes"][mesh]["primitives"]=[{"attributes":attrs,"indices":idx,"material":material}]

def distinct_cuts(master_path,manifest_path):
    """Create new meshes for sleeveless cropped top and flared cropped trousers."""
    src=Path(master_path).read_bytes()
    d,b0=decode(src);b=bytearray(b0)
    m=json.loads(Path(manifest_path).read_text())
    if m.get("derived_sha256")!=hashlib.sha256(src).hexdigest():
        raise ValueError("MANIFEST_SOURCE_MISMATCH")
    if d.get("extras",{}).get("wardrobe_contract",{}).get("schema")!="scp.original_wardrobe.v1":
        raise ValueError("WARDROBE_CONTRACT_CHANGED")
    for actor in v1.ACTORS:
        skin_id=v1.ACTORS.index(actor)
        skin_nodes=d["skins"][skin_id]["joints"]
        skinidx={d["nodes"][idx]["name"].removeprefix(actor+"_"):j
                 for j,idx in enumerate(skin_nodes)}
        slots=m["actor_slots"][actor]
        # A cropped sleeveless vest/tunic: neither a recolored jacket nor a
        # clone of its sleeve primitives. Independent ring topology.
        top_rings=[]
        for y,rx,rz in ((1.045,.160,.135),(1.085,.163,.139),
                        (1.190,.192,.156),(1.298,.211,.160),
                        (1.365,.189,.144),(1.415,.092,.091)):
            t=max(0.,min(1.,(1.38-y)/.27))
            top_rings.append((y,0,0,rx,rz,"spine","chest",t))
        top=_rings(skinidx,actor,top_rings,32)
        # Separate flared, calf-length culotte cut: distinctive wide cuffs.
        upper=[(.745,0,0,.205,.153,"pelvis","spine",1.),
               (.855,0,0,.209,.153,"pelvis","spine",.85),
               (.960,0,0,.175,.138,"pelvis","spine",.4),
               (1.030,0,0,.167,.128,"pelvis","spine",.1)]
        surfaces=[_rings(skinidx,actor,upper,32)]
        for side,sign in (("L",-1),("R",1)):
            leg=[(.195,sign*.14,0,.137,.119,"ankle_"+side,"knee_"+side,.93),
                 (.290,sign*.14,0,.145,.132,"knee_"+side,"hip_"+side,.82),
                 (.475,sign*.14,0,.143,.132,"knee_"+side,"hip_"+side,.55),
                 (.630,sign*.14,0,.135,.122,"hip_"+side,"knee_"+side,.87),
                 (.820,sign*.14,0,.130,.120,"hip_"+side,"pelvis",.83)]
            surfaces.append(_rings(skinidx,actor,leg,32))
        bottom=_combine(*surfaces)
        for slot,shape in (("alt_top",top),("alt_bottom",bottom)):
            meta=slots[slot]
            prim=d["meshes"][meta["mesh"]]["primitives"][0]
            material=prim["material"]  # exact owner-original colorway
            _mesh_primitive(d,b,meta["mesh"],material,shape)
            meta["material_ids"]=[material]
        m.setdefault("cut_styles",{})[actor]={
           "alt_top":"cropped_sleeveless_vest_v2",
           "alt_bottom":"flared_calf_length_culottes_v2"}
    d["extras"]["wardrobe_contract"]["cut_profile"]="ORIGINAL_DIFFERENT_TOPOLOGY_V2_RESEARCH"
    d["extras"]["wardrobe_contract"]["human_cloth_acceptance"]="UNKNOWN"
    result=glb_pack(d,b)
    Path(master_path).write_bytes(result)
    m["derived_sha256"]=hashlib.sha256(result).hexdigest()
    m["separate_new_geometry_for_alternate"]=True
    m["alternate_differences"]="new independent short sleeveless vest and flared cropped culotte mesh topology"
    m["human_appearance_accepted"]=False
    m["cloth_collision_qualified"]=False
    Path(manifest_path).write_text(json.dumps(m,sort_keys=True,indent=2)+"\n")
    return m

def build(out,manifest):
    paths=[Path(out).resolve(),Path(manifest).resolve()]
    if paths[0]==paths[1]:raise ValueError("OUTPUT_PATH_COLLISION")
    for p in paths:
        if p.exists():raise ValueError("IMMUTABLE_OUTPUT_EXISTS:"+str(p))
    paths[0].parent.mkdir(parents=True,exist_ok=True)
    paths[1].parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        source,rig,gait=(td/name for name in ("body17.glb","body35.glb","gait35.glb"))
        old=h.v1.figure_geometry
        try:
            h.v1.figure_geometry=continuous_figure
            h.v1.make_demo(source)
        finally:
            h.v1.figure_geometry=old
        main_expand(source,rig)
        animate(rig,gait)
        v1.split_skinned_layers(gait,out,manifest)
        m=distinct_cuts(out,manifest)
    return {"schema":"scp.r009.original_wardrobe_refinement.v2",
            "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "derived_sha256":m["derived_sha256"],
            "contiguous_trunk_neck_head_loft":True,
            "full_body_watertight":False,
            "new_alt_topology":True,
            "scientific_acceptance":"UNKNOWN_NOT_QUALIFIED",
            "rights_release_merge_cpe_held":True}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",required=True)
    p.add_argument("--manifest",required=True)
    p.add_argument("--receipt",required=True)
    a=p.parse_args()
    if Path(a.receipt).resolve() in (Path(a.out).resolve(),Path(a.manifest).resolve()):
        p.error("receipt must be distinct from source artifacts")
    r=build(a.out,a.manifest)
    Path(a.receipt).write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print(json.dumps(r,sort_keys=True))
