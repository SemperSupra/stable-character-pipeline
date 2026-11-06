#!/usr/bin/env python3
"""Source-preserving and ablatable original-mage garment radius hypotheses.

This creates independent derived GLBs from the exact source-bound, strict
portable adventure outfits in R009 #338/#340. The reference source GLB is
unchanged, as are body/hair/skin, armatures, 72f animation, materials and
garment vertex weights. Radius changes are *hypotheses*, NEVER automatic fixes
or human cloth-fit / face/body acceptance. Measured against the independent
full 72f BVH/edge-strain observer in #340; decrease in crossings alone is not
a full clearance or physics pass.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from modular_wardrobe_v1 import ACTORS
from parametric_morphology_v1 import write_vec3
from rig35_v2 import glb_pack
from verify_original_glb import decode, accessory

SCHEMA="scp.r009.original_mage_radial_fit_ablation.v2"
# (lateral radius, anterior/posterior depth radius); bounded, deliberate
# orthogonal experiments. Expand about EACH primitive's original transverse
# centroid so leg centerline separation cannot be an accidental tuning knob.
CANDIDATES={
    "lower_8": {"style_top":(1.,1.),"style_bottom":(1.08,1.08)},
    "upper_8": {"style_top":(1.08,1.08),"style_bottom":(1.,1.)},
    "both_8": {"style_top":(1.08,1.08),"style_bottom":(1.08,1.08)},
    "both_14":{"style_top":(1.14,1.14),"style_bottom":(1.14,1.14)},
    "juniper_skirt_8": {"style_top":(1.,1.),"style_bottom":(1.08,1.08)},
    "juniper_skirt_14":{"style_top":(1.,1.),"style_bottom":(1.14,1.14)},
}


TARGET_ACTOR={"juniper_skirt_8":"JuniperOriginal",
              "juniper_skirt_14":"JuniperOriginal"}

def factors_for(variant,actor,slot):
    if variant not in CANDIDATES or actor not in ACTORS or (
            slot not in ("style_top","style_bottom")):
        raise ValueError("ABLATION_UNKNOWN_ACTOR_VARIANT_OR_SLOT")
    if variant in TARGET_ACTOR and actor!=TARGET_ACTOR[variant]:
        return (1.,1.)
    return CANDIDATES[variant][slot]


def _authorship(doc,source_receipt,raw):
    if source_receipt.get("schema")!="scp.r009.strict_mage_portable.v1.receipt":
        raise ValueError("ABLATION_SOURCE_RECEIPT_SCHEMA")
    if source_receipt.get("derived_sha256")!=hashlib.sha256(raw).hexdigest():
        raise ValueError("ABLATION_SOURCE_SHA_MISMATCH")
    if set(source_receipt.get("choices",{}))!=set(ACTORS) or (
            set(source_receipt["choices"].values())!={"adventure"}):
        raise ValueError("ABLATION_STRICT_ADVENTURE_ONLY")
    extras=doc.get("extras",{})
    if extras.get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC" or (
            extras.get("strict_mage_portable",{}).get("schema") !=
            "scp.r009.strict_mage_portable.v1") or (
            extras.get("original_mage_outfits",{}).get("schema") !=
            "scp.r009.original_mage_outfits.v1"):
        raise ValueError("ABLATION_NOT_SOURCE_ORIGINAL_STRICT_MAGE")
    if len(doc.get("skins",[]))!=2 or any(len(s.get("joints",[]))!=35
                                             for s in doc["skins"]):
        raise ValueError("ABLATION_35_JOINT_SOURCE_REQUIRED")


def deform_primitive(points,normals,sx,sz):
    if len(points)!=len(normals) or not points:
        raise ValueError("ABLATION_ACCESSOR_CARDINALITY")
    cx=sum(p[0] for p in points)/len(points)
    cz=sum(p[2] for p in points)/len(points)
    altered=[]
    new_normals=[]
    for p,n in zip(points,normals):
        pt=(cx+(p[0]-cx)*sx,p[1],cz+(p[2]-cz)*sz)
        vector=(n[0]/sx,n[1],n[2]/sz)
        length=math.sqrt(sum(t*t for t in vector))
        if length<=1e-10 or not math.isfinite(length):
            raise ValueError("ABLATION_SINGULAR_NORMAL")
        altered.append(pt)
        new_normals.append(tuple(t/length for t in vector))
    if max(abs(a[0]-b[0]) for a,b in zip(points,altered))>0.10 or (
            max(abs(a[2]-b[2]) for a,b in zip(points,altered))>0.10):
        raise ValueError("ABLATION_EXCESSIVE_GEOMETRY_DISPLACEMENT")
    return altered,new_normals


def apply(src,source_receipt,out,receipt,variant):
    paths=list(map(lambda v:Path(v).resolve(),
                   (src,source_receipt,out,receipt)))
    if len(set(paths))!=4:raise ValueError("ABLATION_SOURCE_OVERWRITE_REFUSED")
    source,source_meta,out_path,receipt_path=paths
    if out_path.exists() or receipt_path.exists():
        raise FileExistsError("ABLATION_EXISTING_OUTPUT")
    if variant not in CANDIDATES:
        raise ValueError("ABLATION_UNKNOWN_VARIANT")
    raw=source.read_bytes()
    source_sha=hashlib.sha256(raw).hexdigest()
    sr=json.loads(source_meta.read_text(encoding="utf8"))
    doc,binary=decode(raw)
    _authorship(doc,sr,raw)
    bb=bytearray(binary)
    used=set()
    count={a:{} for a in ACTORS}
    processed={a:{} for a in ACTORS}
    effective={a:{} for a in ACTORS}
    names={n.get("name"):i for i,n in enumerate(doc["nodes"])}
    for actor_i,actor in enumerate(ACTORS):
        root_name=actor+"_SceneRoot"
        if root_name not in names:
            raise ValueError("ABLATION_ROOT_MISSING")
        children=set(doc["nodes"][names[root_name]].get("children",[]))
        for slot in CANDIDATES[variant]:
            sx,sz=factors_for(variant,actor,slot)
            effective[actor][slot]=[sx,sz]
            if sx<1 or sz<1 or sx>1.15 or sz>1.15:
                raise ValueError("ABLATION_OUT_OF_BOUNDS")
            name=actor+"_Wardrobe_"+slot
            if name not in names:raise ValueError("ABLATION_MISSING_LAYER")
            node=doc["nodes"][names[name]]
            if names[name] not in children or node.get("skin")!=actor_i:
                raise ValueError("ABLATION_INACTIVE_OR_MISBOUND_LAYER")
            mesh=doc["meshes"][node["mesh"]]
            cnt=0
            visited=0
            for prim in mesh["primitives"]:
                attrs=prim["attributes"]
                ipos,ino=attrs["POSITION"],attrs["NORMAL"]
                if ipos in used or ino in used:
                    raise ValueError("ABLATION_SHARED_ACCESSOR_REFUSED")
                used.update((ipos,ino))
                positions=accessory(doc,binary,ipos)
                normals=accessory(doc,binary,ino)
                if any(len(x)!=3 for x in positions+normals):
                    raise ValueError("ABLATION_MALFORMED_VECTORS")
                new,new_n=deform_primitive(positions,normals,sx,sz)
                write_vec3(doc,bb,ipos,new)
                write_vec3(doc,bb,ino,new_n)
                visited+=len(new)
                cnt+=sum(any(abs(a-b)>1e-7 for a,b in zip(p,q))
                         for p,q in zip(positions,new))
            processed[actor][slot]=visited
            count[actor][slot]=cnt
    # Only post-derivation diagnostic metadata; never grant appearance,
    # anatomy/rights or physical-clearance acceptance.
    doc.setdefault("extras",{})["radial_ablation"]={
        "schema":SCHEMA,"variant":variant,"source_sha256":source_sha,
        "radial_factors":CANDIDATES[variant],
        "effective_actor_factors":effective,
        "garment_clearance_accepted":False,"appearance_accepted":False,
    }
    if len(doc["skins"])!=2 or any(len(s["joints"])!=35 for s in doc["skins"]):
        raise ValueError("ABLATION_SKIN_CHANGED")
    output=glb_pack(doc,bb)
    result={
        "schema":SCHEMA+".receipt","variant":variant,
        "source_sha256":source_sha,
        "derived_sha256":hashlib.sha256(output).hexdigest(),
        "changed_style_vertices":count,
        "processed_style_vertices":processed,
        "effective_actor_factors":effective,
        "radial_factors":CANDIDATES[variant],
        "source_geometry_preserved":True,
        "motion_preserved":True,"garment_clearance_accepted":False,
        "realistic_morphology_accepted":False,"release_approved":False,
    }
    out_path.parent.mkdir(parents=True,exist_ok=True)
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    with out_path.open("xb") as f:f.write(output)
    with receipt_path.open("x",encoding="utf8") as f:
        f.write(json.dumps(result,indent=2,sort_keys=True)+"\n")
    if hashlib.sha256(source.read_bytes()).hexdigest()!=source_sha:
        raise ValueError("ABLATION_ORIGINAL_CHANGED")
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--source-receipt",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--receipt",required=True)
    ap.add_argument("--variant",choices=sorted(CANDIDATES),required=True)
    a=ap.parse_args()
    print(json.dumps(apply(a.input,a.source_receipt,a.out,
                           a.receipt,a.variant),sort_keys=True))
