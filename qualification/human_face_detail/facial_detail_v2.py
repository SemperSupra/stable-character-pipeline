#!/usr/bin/env python3
"""Opt-in original-only facial geometry controls, separate from character sex.

Bounded face detail only: eye shape/spacing, brow lift/arch, nose, cheek and mouth.
Owner-asserted sex and overall body morphology come unchanged from preceding
R009 morphology v1. This is stylized primitive differential sculpt, *not*
anatomical or facial-fidelity acceptance, a scan reconstruction, a classifier,
or surgery/clinical proof. Never writes to its own source.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "original_reusable_characters"))
from modular_wardrobe_v1 import ACTORS
from parametric_morphology_v1 import SCHEMA as MORPH_SCHEMA, cross, write_vec3
from rig35_v2 import glb_pack
from verify_original_glb import accessory, decode

SCHEMA="scp.r009.facial_detail_controls.v2"
BOUNDS={
    "eye_width":(.82,1.22),
    "eye_height":(.82,1.22),
    "eye_spacing":(.90,1.14),
    "brow_lift_m":(-.008,.012),
    "brow_arch_m":(-.004,.012),
    "nose_width":(.78,1.20),
    "cheek_fullness_m":(0.,.016),
    "mouth_width":(.82,1.22),
}
DEFAULT={
    "AsterOriginal":{
        "eye_width":.94,"eye_height":.95,"eye_spacing":1.02,
        "brow_lift_m":-.003,"brow_arch_m":.000,
        "nose_width":1.10,"cheek_fullness_m":.005,
        "mouth_width":1.01,
    },
    "JuniperOriginal":{
        "eye_width":1.15,"eye_height":1.12,"eye_spacing":1.02,
        "brow_lift_m":.006,"brow_arch_m":.006,
        "nose_width":.88,"cheek_fullness_m":.012,
        "mouth_width":1.12,
    }
}


def profiles_valid(profiles):
    if not isinstance(profiles,dict) or set(profiles)!=set(ACTORS):
        raise ValueError("FACE_ACTOR_SET")
    out={}
    for actor in ACTORS:
        p=profiles[actor]
        if not isinstance(p,dict) or set(p)!=set(BOUNDS):
            raise ValueError("FACE_PROFILE_KEYS:"+actor)
        for k,(lo,hi) in BOUNDS.items():
            v=p[k]
            if type(v) not in (float,int) or not math.isfinite(v) or not lo<=v<=hi:
                raise ValueError("FACE_PROFILE_BOUNDS:"+actor+":"+k)
        out[actor]=dict(p)
    return out


def gauss(x,mean,sigma):
    return math.exp(-.5*((x-mean)/sigma)**2)


def sculpt(position,material,profile):
    """Continuous local controls do not infer gender from an image or material."""
    x,y,z=position
    p=profile
    if material in ("eyeWhite","iris"):
        # Both the sclera and iris share center and pose transformations so
        # the iris does not drift away from its independently shaped eye.
        sign=1 if x>=0 else -1
        local_center=sign*.041
        x=(x-local_center)*p["eye_width"] + local_center*p["eye_spacing"]
        y=1.666+(y-1.666)*p["eye_height"]
    elif material in ("ebonyHair","chestnutHair"):
        # Hair also contains eyebrow ellipsoids. Restrict to brow-height front
        # only; preserve rest of scalp, long side hair, ponytail geometry.
        if .012<abs(x)<.11 and 1.674<y<1.713 and z<-.082:
            y+=p["brow_lift_m"]
            outer=min(1.,abs(x)/.085)
            y+=p["brow_arch_m"]*math.sin(math.pi*outer)
    elif material in ("skinWarm","skinCool"):
        # Head/nose/lip skin shares one source primitive. Spatial kernels are
        # local: no unverified geometry changes below source neck.
        if 1.596<y<1.684 and abs(x)<.055 and z<-.075:
            nose_strength=gauss(y,1.639,.023)
            x*=1. + nose_strength*(p["nose_width"]-1.)
        if 1.552<y<1.685 and z<-.026:
            cheek=(gauss(x,-.078,.030)+gauss(x,.078,.030))
            z-=p["cheek_fullness_m"]*cheek*gauss(y,1.643,.036)
        if 1.572<y<1.614 and abs(x)<.055 and z<-.077:
            x*=1.+gauss(y,1.586,.016)*(p["mouth_width"]-1.)
    return (x,y,z)


def normal_at(pos,normal,material,profile):
    # The local inverse-transpose deformation Jacobian (adjugate) preserves
    # per-material outward normal shading without retopology/weight changes.
    eps=1e-4
    deriv=[]
    for axis in range(3):
        a=list(pos);b=list(pos)
        a[axis]+=eps;b[axis]-=eps
        pa=sculpt(a,material,profile);pb=sculpt(b,material,profile)
        deriv.append(tuple((pa[k]-pb[k])/(2*eps) for k in range(3)))
    tx,ty,tz=deriv
    nx,ny,nz=cross(ty,tz),cross(tz,tx),cross(tx,ty)
    out=tuple(normal[0]*nx[i]+normal[1]*ny[i]+normal[2]*nz[i]
              for i in range(3))
    length=math.sqrt(sum(v*v for v in out))
    if length<1e-8 or not math.isfinite(length):
        raise ValueError("FACE_NORMAL_JACOBIAN_SINGULAR")
    return tuple(v/length for v in out)


def derive(source,source_manifest,dest,dest_manifest,receipt,profiles=None):
    names=[Path(x).resolve() for x in
           (source,source_manifest,dest,dest_manifest,receipt)]
    if len(set(names))!=5:raise ValueError("FACE_SOURCE_OVERWRITE")
    if any(p.exists() for p in names[2:]):raise FileExistsError("FACE_REFUSE_OVERWRITE")
    profiles=profiles_valid(DEFAULT if profiles is None else profiles)
    raw=names[0].read_bytes()
    source_sha=hashlib.sha256(raw).hexdigest()
    manifest=json.loads(names[1].read_text())
    if manifest.get("schema")!="scp.original_wardrobe_manifest.v1" or (
            manifest.get("derived_sha256")!=source_sha):
        raise ValueError("FACE_SOURCE_MANIFEST_SHA")
    doc,binary=decode(raw)
    if doc.get("extras",{}).get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("FACE_NOT_ORIGINAL_SOURCE")
    morph=doc.get("extras",{}).get("parametric_morphology",{})
    if morph.get("schema")!=MORPH_SCHEMA or not morph.get("owner_asserted_character_sex"):
        raise ValueError("FACE_MORPH_SOURCE_MISSING")
    if set(morph.get("profiles",{}))!=set(ACTORS):
        raise ValueError("FACE_OWNER_CHARACTER_REGISTRY_MISMATCH")
    if len(doc.get("skins",[]))!=2 or any(len(s["joints"])!=35 for s in doc["skins"]):
        raise ValueError("FACE_RIG_35")
    blob=bytearray(binary)
    counts={actor:{} for actor in ACTORS}
    seen=set()
    for actor in ACTORS:
        for slot in ("body","hair"):
            base=manifest["actor_slots"][actor]
            mesh=doc["meshes"][base[slot]["mesh"]]
            for prim in mesh["primitives"]:
                mat=doc["materials"][prim["material"]]["name"]
                if mat not in ("eyeWhite","iris","skinWarm","skinCool",
                               "ebonyHair","chestnutHair"):
                    continue
                attrs=prim["attributes"]
                pos_id=attrs["POSITION"];normal_id=attrs["NORMAL"]
                if (actor,pos_id) in seen:continue
                seen.add((actor,pos_id))
                before=accessory(doc,binary,pos_id)
                normals=accessory(doc,binary,normal_id)
                if len(before)!=len(normals) or not before:
                    raise ValueError("FACE_SOURCE_ACCESSOR")
                after=[sculpt(pos,mat,profiles[actor]) for pos in before]
                n_after=[normal_at(pos,n,mat,profiles[actor])
                         for pos,n in zip(before,normals)]
                count=sum(any(abs(v-w)>1e-7 for v,w in zip(p,q))
                          for p,q in zip(before,after))
                counts[actor][mat]=counts[actor].get(mat,0)+count
                write_vec3(doc,blob,pos_id,after)
                write_vec3(doc,blob,normal_id,n_after)
    needed=("eyeWhite","iris","skinWarm",
            "ebonyHair" if "AsterOriginal" in counts else "chestnutHair")
    # All five facial-primitive families must exhibit actual geometry effects
    # (different materials share no empty third-party reference).
    for actor in ACTORS:
        for mat in ("eyeWhite","iris",
                    "skinWarm" if actor=="AsterOriginal" else "skinCool",
                    "ebonyHair" if actor=="AsterOriginal" else "chestnutHair"):
            if counts[actor].get(mat,0)<1:
                raise ValueError("FACE_CONTROL_NO_ACTUAL_VERTEX_EFFECT:"+actor+":"+mat)
    doc["extras"]["facial_detail_v2"]={
        "schema":SCHEMA, "actor_controls":profiles,
        "original_identity":True,"sex_owner_asserted_not_predicted":True,
        "face_geometry_stylized":True,
        "face_fidelity_or_anatomical_realism_accepted":False,
        "skin_armatures_animation_preserved":True,
    }
    if doc.get("skins")!=decode(raw)[0].get("skins") or (
            doc.get("animations")!=decode(raw)[0].get("animations")):
        raise ValueError("FACE_SKIN_OR_ANIMATION_CHANGED")
    payload=glb_pack(doc,blob)
    m=json.loads(json.dumps(manifest))
    m["facial_source_sha256"]=source_sha
    m["derived_sha256"]=hashlib.sha256(payload).hexdigest()
    m["facial_detail_controls"]=profiles
    m["face_geometry_quality_accepted"]=False
    report={
        "schema":SCHEMA+".receipt",
        "input_sha256":source_sha,
        "derived_sha256":m["derived_sha256"],
        "vertex_changes_by_material":counts,
        "source_original":True,"controls_continuous":list(BOUNDS),
        "sex_inferred_from_images":False,
        "native_visual_accepted":False,
        "skin_armature_animation_preserved":True,
        "facial_identity_accepted":False,
        "body_and_garment_contact_accepted":False,
    }
    for path,data in (
        (names[2],payload),
        (names[3],(json.dumps(m,sort_keys=True,indent=2)+"\n").encode()),
        (names[4],(json.dumps(report,sort_keys=True,indent=2)+"\n").encode())
    ):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("xb") as f:f.write(data)
    if hashlib.sha256(names[0].read_bytes()).hexdigest()!=source_sha:
        raise ValueError("FACE_SOURCE_CHANGED_AFTER_DERIVATION")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for arg in ("--input","--manifest","--out","--out-manifest","--receipt"):
        p.add_argument(arg,required=True)
    p.add_argument("--profiles")
    a=p.parse_args()
    pval=None
    if a.profiles:
        loaded=json.loads(Path(a.profiles).read_text())
        if loaded.get("schema")!=SCHEMA:raise ValueError("FACE_SCHEMA_UNKNOWN")
        pval=loaded.get("actors")
    print(json.dumps(derive(a.input,a.manifest,a.out,a.out_manifest,
                            a.receipt,pval),sort_keys=True))
