#!/usr/bin/env python3
"""Source-bound, procedural, removable 35-joint outfit prototypes for Aster/Juniper.

Original-authored geometric archetypes. No third-party costume mesh or texture.
Outputs are animation-bearing glTF scene derivatives, NOT collision/visual passes.
Only exact source-original, independently verified v1 master is admitted.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import struct
from pathlib import Path

SOURCE_SHA256 = "470ec8fc159912e8ad2e30733a00c09785e11c1275c26936774690fe2807727b"
ACTORS = ("AsterOriginal", "JuniperOriginal")
SCHEMA = "scp.r009.source_original.costume_variant.v1"
# Primitive costume cuts are independent creations, not extracted anime geometry.
STYLES = {
    "classic_adventurer": {"top": (0.91,0.91,0.84,1), "skirt": (0.13,0.34,0.66,1), "trim": (0.74,0.58,0.20,1), "hem_y":0.68, "flare":1.45,"pleats":12,"collar":False},
    "casual": {"top":(0.67,0.13,0.17,1), "skirt":(0.12,0.26,0.46,1), "trim":(0.55,0.41,0.25,1), "hem_y":0.72, "flare":1.34,"pleats":8,"collar":False},
    "tournament_bodice": {"top":(0.31,0.17,0.52,1), "skirt":(0.41,0.23,0.60,1), "trim":(0.78,0.66,0.39,1), "hem_y":0.70, "flare":1.51,"pleats":16,"collar":False},
    "high_collar_adventurer": {"top":(0.12,0.27,0.57,1), "skirt":(0.88,0.88,0.82,1), "trim":(0.74,0.57,0.24,1), "hem_y":0.66, "flare":1.42,"pleats":10,"collar":True},
}
# Actor-specific source-original torso contour measured from authored ring controls;
# NOT body measurement inferred from photos. X and Z are glTF native metres.
TORSO = {
    "AsterOriginal": [(0.805,.153,.113),(.861,.184,.121),(.934,.167,.118),(1.014,.145,.102),(1.083,.144,.107),(1.174,.155,.129),(1.262,.187,.136),(1.330,.170,.116),(1.397,.091,.073),(1.443,.060,.057)],
    "JuniperOriginal": [(0.805,.160,.113),(.861,.193,.121),(.934,.176,.118),(1.014,.139,.102),(1.083,.138,.107),(1.174,.149,.129),(1.262,.180,.136),(1.330,.164,.116),(1.397,.091,.073),(1.443,.060,.057)],
}
DEFAULT_FIT = {"chest_scale":1.0,"waist_scale":1.0,"hip_scale":1.0,"ease_m":0.017}
FIT_BOUNDS = {"chest_scale":(.88,1.17),"waist_scale":(.88,1.17),"hip_scale":(.88,1.17),"ease_m":(.008,.045)}


def validate_fit(fit):
    if type(fit) is not dict or set(fit) != set(DEFAULT_FIT):
        raise ValueError("FIT_PARAMETER_KEYS")
    for k, (lo,hi) in FIT_BOUNDS.items():
        v=fit[k]
        if type(v) not in (float,int) or not math.isfinite(v) or not lo <= v <= hi:
            raise ValueError("FIT_PARAMETER_RANGE:"+k)
    return True


def _contour(actor,y):
    if actor not in TORSO or type(y) not in (float,int) or not math.isfinite(y):
        raise ValueError("BAD_ACTOR_OR_Y")
    rows=TORSO[actor]
    if not rows[0][0] <= y <= rows[-1][0]:
        raise ValueError("OUTSIDE_AUTHORED_CONTOUR")
    for a,b in zip(rows,rows[1:]):
        if a[0] <= y <= b[0]:
            t=(y-a[0])/(b[0]-a[0])
            return (a[1]+t*(b[1]-a[1]),a[2]+t*(b[2]-a[2]))
    return rows[-1][1:]


def _weights(region,y,side=None):
    if region in ("bottom","trim"):
        return (0,1,0.) # all on pelvis; cloth dynamics are NOT implemented
    if y <= 1.11:
        return (0,1,max(0.,min(1.,(1.11-y)/.20)))
    return (1,2,max(0.,min(1.,(1.38-y)/.27)))


def _ring_mesh(rings, *, sides=64, pleats=0, roll=0.0, region="top"):
    """Returns skinned attributes and triangles in rest-model local metres.

    Rings: (y, rx, rz), ordered low-to-high. Open edges are intentional cloth hems.
    More than two vertical rings prevent completely flat strip deformation.
    """
    if len(rings)<3 or sides<32 or sides%4:
        raise ValueError("BAD_RING_TOPOLOGY")
    if any(not all(math.isfinite(x) and x>0 for x in (y,rx,rz)) for y,rx,rz in rings):
        raise ValueError("NONFINITE_OR_NEGATIVE_RING")
    if any(a[0] >= b[0] for a,b in zip(rings,rings[1:])):
        raise ValueError("RING_ORDER")
    pos=[]; norms=[]; joints=[]; weights=[]; indices=[]
    for k,(y,rx,rz) in enumerate(rings):
        for j in range(sides):
            a=(2*math.pi*j/sides)+roll
            pleat=1.+(pleats and .025*math.cos(pleats*a)*min(1.,max(0.,(1.02-y)/.26)))
            x=rx*math.cos(a)*pleat
            z=rz*math.sin(a)*pleat
            pos.extend((x,y,z))
            nx, nz=math.cos(a)/rx, math.sin(a)/rz
            length=math.hypot(nx,nz)
            norms.extend((nx/length,0.,nz/length))
            primary,secondary,w=_weights(region,y)
            joints.extend((primary,secondary,0,0))
            weights.extend((w,1.-w,0.,0.))
    for k in range(len(rings)-1):
        for j in range(sides):
            a=k*sides+j; b=k*sides+(j+1)%sides
            indices.extend((a,a+sides,b,b,a+sides,b+sides))
    return {"POSITION":pos,"NORMAL":norms,"JOINTS_0":joints,"WEIGHTS_0":weights,"indices":indices}


def design_geometry(actor,design,fit=None):
    if design not in STYLES or actor not in ACTORS:
        raise ValueError("UNKNOWN_DESIGN_OR_ACTOR")
    fit=dict(DEFAULT_FIT if fit is None else fit)
    validate_fit(fit)
    style=STYLES[design]
    e=fit["ease_m"]
    def body(y):
        x,z=_contour(actor,y)
        scale=fit["chest_scale"] if y>=1.15 else fit["waist_scale"]
        return x*scale+e,z*scale+e
    top_y=(1.022,1.073,1.135,1.207,1.276,1.337,1.385)
    top=[(y,*body(y)) for y in top_y]
    top_mesh=_ring_mesh(top,region="top")
    # Waist, hip and hem grading are separated; no automatic identity resizing.
    waist_x,waist_z=_contour(actor,1.014)
    hip_x,hip_z=_contour(actor,.861)
    hem=style["hem_y"]
    skirt=[(hem,hip_x*fit["hip_scale"]*style["flare"]+e*1.5,
                 hip_z*fit["hip_scale"]*style["flare"]+e*1.5),
           (hem+.07,hip_x*fit["hip_scale"]*1.30+e*1.4,
                         hip_z*fit["hip_scale"]*1.30+e*1.4),
           (.86,hip_x*fit["hip_scale"]*1.27+e,
                 hip_z*fit["hip_scale"]*1.27+e),
           (.94,hip_x*fit["hip_scale"]*1.17+e,
                 hip_z*fit["hip_scale"]*1.17+e),
           (1.025,waist_x*fit["waist_scale"]*1.12+e,
                  waist_z*fit["waist_scale"]*1.12+e)]
    skirt_mesh=_ring_mesh(skirt,pleats=style["pleats"],region="bottom")
    belt=[(1.002,waist_x*fit["waist_scale"]*1.15+e,
                waist_z*fit["waist_scale"]*1.15+e),
          (1.021,waist_x*fit["waist_scale"]*1.17+e,
                waist_z*fit["waist_scale"]*1.17+e),
          (1.040,waist_x*fit["waist_scale"]*1.15+e,
                waist_z*fit["waist_scale"]*1.15+e)]
    meshes={"top":top_mesh,"bottom":skirt_mesh,"trim":_ring_mesh(belt,region="trim")}
    if style["collar"]:
        meshes["collar"]=_ring_mesh([(1.397,.086,.073),(1.429,.070,.063),(1.460,.065,.061)],region="top")
    return meshes


def _unpack_glb(raw):
    if len(raw)<28 or raw[:4]!=b"glTF" or struct.unpack_from("<I",raw,4)[0]!=2 or struct.unpack_from("<I",raw,8)[0]!=len(raw):
        raise ValueError("NOT_VALID_GLB_HEADER")
    n,kind=struct.unpack_from("<I4s",raw,12)
    if kind!=b"JSON" or n<2 or 20+n+8>len(raw):
        raise ValueError("NOT_VALID_JSON_CHUNK")
    off=20+n
    m,bin_kind=struct.unpack_from("<I4s",raw,off)
    if bin_kind!=b"BIN\0" or off+8+m!=len(raw):
        raise ValueError("NOT_VALID_BIN_CHUNK")
    return json.loads(raw[20:off].decode()),bytearray(raw[off+8:])


def _pack_glb(doc,data):
    doc["buffers"][0]["byteLength"]=len(data)
    j=json.dumps(doc,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    j+=b" "*((-len(j))%4)
    b=bytes(data)+b"\0"*((-len(data))%4)
    return struct.pack("<4sII",b"glTF",2,12+8+len(j)+8+len(b))+struct.pack("<I4s",len(j),b"JSON")+j+struct.pack("<I4s",len(b),b"BIN\0")+b


def _accessor(doc,data,values,*,comp_type,shape,count,add_bounds=False):
    components={"SCALAR":1,"VEC3":3,"VEC4":4}[shape]
    if len(values)%components or len(values)//components!=count:
        raise ValueError("ACCESSOR_VALUE_COUNT")
    if comp_type==5126:
        if not all(type(x) in (int,float) and math.isfinite(x) for x in values):
            raise ValueError("NONFINITE_ACCESSOR")
        packed=struct.pack("<"+"f"*len(values),*values)
    elif comp_type==5121:
        if not all(type(x) is int and 0<=x<=255 for x in values):
            raise ValueError("BAD_JOINT_ACCESSOR")
        packed=bytes(values)
    elif comp_type==5125:
        if not all(type(x) is int and x>=0 for x in values):
            raise ValueError("BAD_INDEX_ACCESSOR")
        packed=struct.pack("<"+"I"*len(values),*values)
    else:
        raise ValueError("UNSUPPORTED_COMPONENT_TYPE")
    while len(data)%4:data.append(0)
    start=len(data);data.extend(packed)
    view=len(doc["bufferViews"])
    doc["bufferViews"].append({"buffer":0,"byteOffset":start,"byteLength":len(packed)})
    acc={"bufferView":view,"componentType":comp_type,"count":count,"type":shape}
    if add_bounds:
        acc["min"]=[min(values[k::components]) for k in range(components)]
        acc["max"]=[max(values[k::components]) for k in range(components)]
    idx=len(doc["accessors"]);doc["accessors"].append(acc)
    return idx


def _inject_mesh(doc,buf,actor,skin_idx,slot,geo,rgba):
    count=len(geo["POSITION"])//3
    if len(geo["indices"])%3 or max(geo["indices"])>=count:
        raise ValueError("INVALID_TRIANGLE_INDEX")
    attrs={}
    for key,ct,shape in (("POSITION",5126,"VEC3"),("NORMAL",5126,"VEC3"),("JOINTS_0",5121,"VEC4"),("WEIGHTS_0",5126,"VEC4")):
        attrs[key]=_accessor(doc,buf,geo[key],comp_type=ct,shape=shape,count=count,add_bounds=key=="POSITION")
    idx=_accessor(doc,buf,geo["indices"],comp_type=5125,shape="SCALAR",count=len(geo["indices"]))
    material=len(doc["materials"])
    doc["materials"].append({"name":actor+"_"+slot+"_original_pattern","doubleSided":True,
       "pbrMetallicRoughness":{"baseColorFactor":list(rgba),"metallicFactor":0.,"roughnessFactor":.87}})
    mesh=len(doc["meshes"])
    doc["meshes"].append({"name":actor+"_"+slot+"_ProceduralMesh","primitives":[{"attributes":attrs,"indices":idx,"material":material,"mode":4}]})
    node=len(doc["nodes"])
    doc["nodes"].append({"name":actor+"_Wardrobe_costume_"+slot,"mesh":mesh,"skin":skin_idx,
                         "extras":{"original_geometry":True,"wardrobe_slot":"costume_"+slot,"fit_accepted":False}})
    return node


def variant(source_bytes,design,fit_by_actor=None):
    if hashlib.sha256(source_bytes).hexdigest()!=SOURCE_SHA256:
        raise ValueError("SOURCE_SHA256_NOT_PINNED_MASTER")
    if design not in STYLES:
        raise ValueError("UNKNOWN_DESIGN")
    doc,buf=_unpack_glb(source_bytes)
    if doc.get("extras",{}).get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("SOURCE_CLASS_MISMATCH")
    if len(doc.get("skins",[]))!=2 or any(len(s.get("joints",[]))!=35 for s in doc["skins"]):
        raise ValueError("SOURCE_35JOINT_SKIN_REQUIRED")
    nodes=doc["nodes"]
    byname={n.get("name"):i for i,n in enumerate(nodes)}
    for i,actor in enumerate(ACTORS):
        root=byname[actor+"_SceneRoot"]
        allowed={actor+"_Wardrobe_"+name for name in ("body","hair","footwear")}
        children=nodes[root]["children"]
        preserved=[idx for idx in children if not nodes[idx].get("name","").startswith(actor+"_Wardrobe_") or nodes[idx].get("name") in allowed]
        if not {actor+"_Wardrobe_"+slot for slot in ("body","hair","footwear")}.issubset({nodes[x]["name"] for x in preserved}):
            raise ValueError("MISSING_REUSABLE_BODY_OR_FOOTWEAR")
        fit=DEFAULT_FIT if fit_by_actor is None else fit_by_actor.get(actor,DEFAULT_FIT)
        generated=design_geometry(actor,design,fit)
        for slot,mesh in generated.items():
            preserved.append(_inject_mesh(doc,buf,actor,i,slot,mesh,STYLES[design]["trim" if slot in ("trim","collar") else "skirt" if slot=="bottom" else "top"]))
        nodes[root]["children"]=preserved
    doc.setdefault("extras",{})["costume_variant"]={
       "schema":SCHEMA,"design":design,"design_source":"project_original_patterns",
       "source_sha256":SOURCE_SHA256,"actors":list(ACTORS),
       "rig_shared_per_actor":True,"source_animation_preserved":True,
       "manual_fit_required":True,"cloth_simulation":"NOT_RUN","collision_qualified":False,
       "natural_motion_accepted":False,"visual_accepted":False,"release_approved":False}
    return _pack_glb(doc,buf)


def build(source,outdir,*,designs=None,fit_by_actor=None):
    src=Path(source)
    output=Path(outdir)
    if not src.is_file() or not output.is_dir() or src.resolve().parent==output.resolve():
        raise ValueError("SOURCE_OR_OUTPUT_DIRECTORY_NOT_ADMITTED")
    data=src.read_bytes()
    if hashlib.sha256(data).hexdigest()!=SOURCE_SHA256:
        raise ValueError("SOURCE_SHA256_NOT_PINNED_MASTER")
    choices=list(STYLES) if designs is None else list(designs)
    if not choices or len(set(choices))!=len(choices) or any(x not in STYLES for x in choices):
        raise ValueError("INVALID_DESIGN_SELECTION")
    receipt={"schema":SCHEMA,"source_sha256":SOURCE_SHA256,"source_preserved":True,
        "source_class":"original_synthetic","actors":list(ACTORS),"designs":{},
        "native_blender":"NOT_RUN","fitting_accepted":False,"physical_cloth":"NOT_RUN",
        "photographic_identity":"NOT_APPLICABLE","release_approved":False}
    for name in choices:
        dest=output/("r009_"+name+"_aster_juniper_35joint.glb")
        if dest.exists():raise ValueError("REFUSE_OVERWRITE:"+str(dest))
    for name in choices:
        result=variant(data,name,fit_by_actor)
        dest=output/("r009_"+name+"_aster_juniper_35joint.glb")
        dest.write_bytes(result)
        parsed,_=_unpack_glb(result)
        receipt["designs"][name]={"file":dest.name,"sha256":hashlib.sha256(result).hexdigest(),
          "bytes":len(result),"nodes":len(parsed["nodes"]),"meshes":len(parsed["meshes"]),
          "joints_per_actor":35,"animations":len(parsed["animations"]),
          "garments_per_actor":3+bool(STYLES[name]["collar"]),"physical_fit":"UNQUALIFIED"}
    return receipt


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out-dir",required=True)
    p.add_argument("--design",action="append",choices=sorted(STYLES))
    p.add_argument("--fit-json")
    args=p.parse_args()
    fits=None
    if args.fit_json:
        fits=json.loads(Path(args.fit_json).read_text())
        if type(fits) is not dict or set(fits)-set(ACTORS):raise ValueError("INVALID_ACTOR_FITS")
        for v in fits.values():validate_fit(v)
    r=build(args.source,args.out_dir,designs=args.design,fit_by_actor=fits)
    print(json.dumps(r,sort_keys=True,indent=2))

if __name__=="__main__":main()