#!/usr/bin/env python3
"""Juniper-only lower hem radial taper after separate source-pinned +14% skirt cut.

No source/body/face/rig edits. Every candidate is evaluated by unchanged native
R009 #340 72-frame BVH and sampled edge-strain, not a garment simulator.
The 14% broad radial initial trial reduced 8,657->543 crossings; its remaining
18 frames occur exclusively below imported Blender-Z .85m. For original GLB
Y-up, adjust only skirt lower radial rings and taper smoothly before .91m.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from parametric_morphology_v1 import write_vec3
from rig35_v2 import glb_pack
from verify_original_glb import accessory,decode
from fit_radial_ablations_v1 import SCHEMA as RADIAL_SCHEMA

SCHEMA="scp.r009.juniper_original_lower_hem_motion_fit.v1"
ACTOR="JuniperOriginal"
# Extra 3/6/10% relative to unmodified +14% original-only pattern. The last
# test isolates low hem only, and shall not auto-accept from low crossing count.
OPTIONS={
 "hem_03":(.03,.66,.91),
 "hem_06":(.06,.66,.91),
 "hem_10":(.10,.66,.91),
 "lower_hem_06":(.06,.56,.78),
}


def atten(y,low,high):
    if not math.isfinite(y) or not low<high:raise ValueError("HEM_BAD_HEIGHT")
    t=max(0.,min(1.,(high-y)/(high-low)))
    fade=t*t*(3.-2.*t)
    deriv=(-6.*t*(1.-t)/(high-low)) if 0<t<1 else 0.
    return fade,deriv


def deform(points,normals,growth,low,high):
    if not points or len(points)!=len(normals):
        raise ValueError("HEM_ACCESSOR_COUNT")
    if growth<=0 or growth>.12:raise ValueError("HEM_RADIUS_BOUND")
    cx=sum(v[0] for v in points)/len(points)
    cz=sum(v[2] for v in points)/len(points)
    new,normal_new=[],[]
    count=0
    for p,n in zip(points,normals):
        y=p[1] # glTF original source is Y-up; Blender imports Z-up.
        fade,dfade=atten(y,low,high)
        if fade<=0.:
            new.append(p)
            normal_new.append(n)  # EXACT no-op: do not normalize
            continue
        scale=1.+growth*fade
        dscale=growth*dfade
        dx, dz=p[0]-cx, p[2]-cz
        pt=(cx+dx*scale,y,cz+dz*scale)
        # J = [[scale, dx*dscale, 0], [0,1,0],
        #      [0,dz*dscale,scale]]. Inverse-transpose normal.
        nx,nz=n[0]/scale,n[2]/scale
        ny=n[1]-dx*dscale*nx-dz*dscale*nz
        length=math.sqrt(nx*nx+ny*ny+nz*nz)
        if length<1e-8 or not math.isfinite(length):
            raise ValueError("HEM_DEGENERATE_NORMAL")
        new.append(pt)
        normal_new.append((nx/length,ny/length,nz/length))
        if abs(pt[0]-p[0])>1e-7 or abs(pt[2]-p[2])>1e-7:
            count+=1
    if count<=50:raise ValueError("HEM_NO_EFFECT")
    if max(math.dist(p,q) for p,q in zip(points,new))>.06:
        raise ValueError("HEM_EXCESSIVE_VERTEX_DISPLACEMENT")
    return new,normal_new,count


def apply(src,source_receipt,out,receipt,variant):
    if variant not in OPTIONS:raise ValueError("HEM_VARIANT_UNKNOWN")
    paths=[Path(p).resolve() for p in (src,source_receipt,out,receipt)]
    if len(set(paths))!=4:raise ValueError("HEM_SOURCE_OVERWRITE")
    source,meta,target,receipt_path=paths
    if target.exists() or receipt_path.exists():
        raise FileExistsError("HEM_REFUSE_EXISTING_OUTPUT")
    raw=source.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
    sr=json.loads(meta.read_text())
    d,binary=decode(raw)
    variant_meta=d.get("extras",{}).get("radial_ablation",{})
    if (sr.get("schema")!=RADIAL_SCHEMA+".receipt" or
        sr.get("derived_sha256")!=sha or
        sr.get("variant")!="juniper_skirt_14" or
        variant_meta.get("schema")!=RADIAL_SCHEMA or
        variant_meta.get("variant")!="juniper_skirt_14" or
        variant_meta.get("source_sha256")!=sr.get("source_sha256") or
        d.get("extras",{}).get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or
        len(d.get("skins",[]))!=2 or any(len(s["joints"])!=35 for s in d["skins"])):
        raise ValueError("HEM_SOURCE_NOT_PINNED_ORIGINAL_RADIAL14")
    names={n.get("name"):i for i,n in enumerate(d["nodes"])}
    node_id=names.get(ACTOR+"_Wardrobe_style_bottom")
    root_id=names.get(ACTOR+"_SceneRoot")
    if node_id is None or root_id is None or (
            node_id not in d["nodes"][root_id].get("children",[])) or (
            d["nodes"][node_id].get("skin")!=1):
        raise ValueError("HEM_NOT_ACTIVE_JUNIPER_LAYER")
    index=d["nodes"][node_id]["mesh"]
    mesh=d["meshes"][index]
    bb=bytearray(binary)
    used=set(); total=0
    growth,low,high=OPTIONS[variant]
    for prim in mesh["primitives"]:
        attrs=prim["attributes"]
        pos,nor=attrs["POSITION"],attrs["NORMAL"]
        if pos in used or nor in used:
            raise ValueError("HEM_SHARED_ACCESSOR_REFUSED")
        used.add(pos);used.add(nor)
        points=accessory(d,binary,pos);normals=accessory(d,binary,nor)
        transformed,normals_out,count=deform(points,normals,growth,low,high)
        total+=count
        write_vec3(d,bb,pos,transformed)
        write_vec3(d,bb,nor,normals_out)
    if total<100:raise ValueError("HEM_TOO_FEW_CHANGED_VERTICES")
    d.setdefault("extras",{})["juniper_motion_hem_trial"]={
        "schema":SCHEMA,"variant":variant,
        "source_sha256":sha,"radial_growth":growth,
        "ramp_y_up_m":[low,high],
        "target":"JuniperOriginal/Wardrobe/style_bottom",
        "skin_animation_preserved":True,"visual_accepted":False,
        "cloth_collision_accepted":False,
    }
    payload=glb_pack(d,bb)
    rec={"schema":SCHEMA+".receipt",
         "source_sha256":sha,
         "baseline_strict_source_sha256":sr["source_sha256"],
         "derived_sha256":hashlib.sha256(payload).hexdigest(),
         "variant":variant,"changed_skirt_vertices":total,
         "height_coordinate":"original GLB Y-up (Blender world Z)",
         "grow_ratio_extra":growth,"taper_glb_y_low_high":[low,high],
         "garment_clearance_accepted":False,"human_visual_accepted":False,
         "72f_cloth_physics_accepted":False,"release_held":True}
    target.parent.mkdir(parents=True,exist_ok=True)
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    with target.open("xb") as f:f.write(payload)
    with receipt_path.open("x",encoding="utf8") as f:
        f.write(json.dumps(rec,sort_keys=True,indent=2)+"\n")
    if hashlib.sha256(source.read_bytes()).hexdigest()!=sha:
        raise ValueError("HEM_SOURCE_MUTATED")
    return rec


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--source-receipt",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--receipt",required=True)
    p.add_argument("--variant",required=True,choices=sorted(OPTIONS))
    a=p.parse_args()
    print(json.dumps(apply(a.input,a.source_receipt,a.out,
                           a.receipt,a.variant),sort_keys=True))
