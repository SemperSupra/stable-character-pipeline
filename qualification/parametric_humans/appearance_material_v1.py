#!/usr/bin/env python3
"""Opt-in source-original PBR appearance preview, independently reversible.

Modifies only copies of source-original glTF material bindings and iris triangle
index subsets. DOES NOT simulate human pigmentation, cosmetics, surgery or
photo-derived identity. Left/right iris RGB are kept separate by triangle side.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import struct
from pathlib import Path

import parameters_v1 as contract
import morph_preview_35_v1 as morph
from verify_original_glb import decode, accessory
from rig35_v2 import glb_pack

SCHEMA="scp.r009.original_appearance_pbr_preview.v1"
ACTORS=("AsterOriginal","JuniperOriginal")
SLOTS={"body","hair"}

def linear(srgb):
    x=max(0.,min(1.,float(srgb)))
    return x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4

def skin_srgb(state):
    melanin=state["appearance"]["skin_melanin"]
    undertone=state["appearance"]["skin_undertone"]
    offsets={"cool":(.01,-.012,.025),"neutral":(0.,0.,0.),
             "warm":(.025,.012,-.015),"olive":(-.02,.01,-.015)}[undertone]
    # Purely stylized color mapping; not calibrated reflectance, skin classification,
    # or an anthropometric or dermatologic claim.
    return [max(.01,min(.96,v+o)) for v,o in zip(
        (.93-.66*melanin,.78-.58*melanin,.67-.51*melanin),offsets)]

def _write_index_accessor(data,bin_data,indices):
    while len(bin_data)%4:bin_data.append(0)
    off=len(bin_data)
    bin_data.extend(struct.pack("<"+"I"*len(indices),*indices))
    view=len(data["bufferViews"])
    data["bufferViews"].append({"buffer":0,"byteOffset":off,"byteLength":4*len(indices),
                                "target":34963})
    idx=len(data["accessors"])
    data["accessors"].append({"bufferView":view,"componentType":5125,
                             "count":len(indices),"type":"SCALAR"})
    return idx

def apply(raw,aster,juniper):
    states=(aster,juniper)
    for p in states:contract.validate(p)
    doc,binary=decode(raw)
    if doc.get("extras",{}).get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("SOURCE_RIGHTS_REJECTED")
    if doc.get("extras",{}).get("wardrobe_contract",{}).get("rig_joints_each")!=35:
        raise ValueError("EXPECTED_35_JOINT_WARDROBE")
    if len(doc.get("skins",[]))!=2 or any(len(s["joints"])!=35 for s in doc["skins"]):
        raise ValueError("RIG_BINDING_MISMATCH")
    if len(doc.get("animations",[]))!=1:
        raise ValueError("MOTION_NOT_PRESERVED")
    d=copy.deepcopy(doc)
    buf=bytearray(binary)
    materials_by_name={v["name"]:i for i,v in enumerate(doc["materials"])}
    witnesses={}
    for actor_idx,(actor,state) in enumerate(zip(ACTORS,states)):
        skin_name="skinWarm" if actor_idx==0 else "skinCool"
        hair_name="ebonyHair" if actor_idx==0 else "chestnutHair"
        controls=state["appearance"]
        rgb_map={
            skin_name:skin_srgb(state),
            hair_name:controls["hair_rgb"],
            "left_iris":controls["left_iris_rgb"],
            "right_iris":controls["right_iris_rgb"],
        }
        output_materials={}
        for name,rgb in rgb_map.items():
            original_name="iris" if name.endswith("_iris") else name
            if original_name not in materials_by_name:
                raise ValueError("SOURCE_MATERIAL_MISSING:"+original_name)
            material=copy.deepcopy(doc["materials"][materials_by_name[original_name]])
            material["name"]=actor+"_"+name+"_parametric"
            material.setdefault("pbrMetallicRoughness",{})["baseColorFactor"]=[
                linear(x) for x in rgb]+[1.]
            if name==skin_name:
                material["pbrMetallicRoughness"]["roughnessFactor"]=max(
                    .12,min(1.,controls["skin_roughness"]))
            output_materials[name]=len(d["materials"])
            d["materials"].append(material)
        touched={"skin":0,"hair":0,"left_iris_triangles":0,
                 "right_iris_triangles":0}
        for node in d["nodes"]:
            if not node.get("name","").startswith(actor+"_Wardrobe_") or "mesh" not in node:
                continue
            mesh=d["meshes"][node["mesh"]]
            rewritten=[]
            for prim in mesh["primitives"]:
                source_name=doc["materials"][prim["material"]]["name"]
                if source_name in (skin_name,hair_name):
                    p=copy.deepcopy(prim)
                    p["material"]=output_materials[source_name]
                    rewritten.append(p)
                    touched["skin" if source_name==skin_name else "hair"]+=1
                    continue
                if source_name!="iris":
                    rewritten.append(prim)
                    continue
                positions=accessory(doc,binary,prim["attributes"]["POSITION"])
                indices=accessory(doc,binary,prim["indices"])
                side_indices={"left_iris":[],"right_iris":[]}
                if len(indices)%3:
                    raise ValueError("IRIS_INDICES_NOT_TRIANGLES")
                for k in range(0,len(indices),3):
                    trio=[int(indices[t][0]) for t in range(k,k+3)]
                    xs=[positions[i][0] for i in trio]
                    if all(x<0 for x in xs):
                        side_indices["left_iris"].extend(trio)
                    elif all(x>0 for x in xs):
                        side_indices["right_iris"].extend(trio)
                    else:
                        raise ValueError("IRIS_MIDLINE_TRIANGLE_UNEXPECTED")
                if not all(side_indices.values()):
                    raise ValueError("IRIS_LEFT_RIGHT_MISSING")
                for label in ("left_iris","right_iris"):
                    clone=copy.deepcopy(prim)
                    clone["material"]=output_materials[label]
                    clone["indices"]=_write_index_accessor(d,buf,side_indices[label])
                    rewritten.append(clone)
                    touched[label+"_triangles"]+=len(side_indices[label])//3
            mesh["primitives"]=rewritten
        if not all(touched.values()):
            raise ValueError("ACTOR_APPEARANCE_NOT_REBOUND:"+actor+":"+str(touched))
        witnesses[actor]={
            "material_names":{name:d["materials"][idx]["name"]
                              for name,idx in output_materials.items()},
            "original_skin_and_hair_source_preserved":True,
            "per_eye_iris_materials":True,
            "modified_primitive_counts":touched,
            "source_parameter_sha256":contract.sha256(state),
            "real_skin_reflectance_validated":False,
            "texture_and_groom_geometry_qualified":False}
    d.setdefault("extras",{})["parametric_appearance"]={
        "schema":SCHEMA,"source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
        "surgery_prediction":"NONE","visual_acceptance":"UNKNOWN",
        "materials_original_retained":True,"source_geometry_accessors_preserved":True,
        "human_identity_claim":False}
    packed=glb_pack(d,buf)
    return packed,witnesses

def build(source,out,receipt,aster,juniper):
    if out.exists() or receipt.exists():
        raise FileExistsError("REFUSE_OVERWRITE")
    original=source.read_bytes()
    new,witnesses=apply(original,aster,juniper)
    result={"schema":SCHEMA,"source_sha256":hashlib.sha256(original).hexdigest(),
            "derived_sha256":hashlib.sha256(new).hexdigest(),
            "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
            "actor_witnesses":witnesses,"joints_each":35,
            "rig_or_motion_modified":False,"human_visual_accepted":False,
            "surgical_outcome_predicted":False,"release_approved":False}
    with out.open("xb") as f:f.write(new)
    with receipt.open("x",encoding="utf-8") as f:
        f.write(json.dumps(result,sort_keys=True,indent=2)+"\n")
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--receipt",required=True,type=Path)
    ap.add_argument("--aster",required=True,type=Path)
    ap.add_argument("--juniper",required=True,type=Path)
    ap.add_argument("--as-of")
    args=ap.parse_args()
    a=json.loads(args.aster.read_text(encoding="utf-8"))
    j=json.loads(args.juniper.read_text(encoding="utf-8"))
    if args.as_of:
        a=contract.snapshot(a,args.as_of)
        j=contract.snapshot(j,args.as_of)
    result=build(args.input,args.out,args.receipt,a,j)
    print(json.dumps({"derived_sha256":result["derived_sha256"],
                      "per_eye":True,"release_approved":False},sort_keys=True))
if __name__=="__main__":
    main()
