#!/usr/bin/env python3
"""Original-fictional adult body + removable wardrobe, non-destructive GLB derivative.

All geometry is newly scripted in this repository; no third-party body scans,
photographs, celebrity identities, licensed vendor models, or external textures.
Anatomically neutral adult unclothed base (no explicit sexual detailing) is
skinned to the exact same skeleton as separate outfit meshes. This is a
technical costume interchange candidate, NOT anatomical or collision approval.
"""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path
import humanization_v2 as h
from rig35_v2 import main_expand, glb_pack
from phase_gait35 import animate
from verify_original_glb import decode

ACTORS = ("AsterOriginal", "JuniperOriginal")
SLOTS = ("body", "hair", "top", "bottom", "footwear", "accessory", "alt_top", "alt_bottom")
PRESETS = {
    "unclothed": ("body", "hair"),
    "signature": ("body", "hair", "top", "bottom", "footwear", "accessory"),
    "alternate": ("body", "hair", "alt_top", "alt_bottom", "footwear")
}
CLOTH_MATERIAL = {
    "coralJacket":"top","tealJacket":"top",
    "slatePants":"bottom","ochrePants":"bottom",
    "darkBoots":"footwear","earthBoots":"footwear",
    "scarf":"accessory","ebonyHair":"hair","chestnutHair":"hair",
}
ALT_COLORS = {"AsterOriginal": {"alt_top":(.23,.37,.50,1.),"alt_bottom":(.36,.29,.24,1.)},
              "JuniperOriginal":{"alt_top":(.51,.22,.39,1.),"alt_bottom":(.18,.23,.38,1.)}}

def adult_body_geometry(which):
    """Body is physically present under clothing and separately weighted.

    Region transition surfaces overlap deliberately until independent body
    sculpt retopology is accepted. Preserve original 17-joint source namespace.
    """
    # Garment shells need clearance outside the complete body:
    # old stylized coat depth (.117m) was inside anatomical chest (.136m).
    # Apply only in this wardrobe variant; owner #291 silhouette stays immutable.
    old_torso=h.torso
    def garment_torso(g,material,widths):
        return old_torso(g,material,(widths[0]*1.07,max(widths[1],.167)))
    try:
        h.torso=garment_torso
        g=h.make_figure(which)
    finally:
        h.torso=old_torso
    skin="skinWarm" if which==0 else "skinCool"
    hips=.184 if which==0 else .193
    waist=.145 if which==0 else .139
    chest=.170 if which==0 else .164
    rings=[
      (.805,.0,hips*.83,.113),(.861,.0,hips,.121),
      (.934,0,hips*.91,.118),(1.014,0,waist,.102),
      (1.083,0,waist*.99,.107),(1.174,0,chest*.91,.129),
      (1.262,0,chest*1.1,.136),(1.330,0,chest,.116),
      (1.397,0,.091,.073),(1.443,0,.060,.057)]
    def torso_weights(y):
        if y<1.11:return ("pelvis","spine",max(0,min(1,(1.11-y)/.20)))
        return ("spine","chest",max(0,min(1,(1.38-y)/.27)))
    h.loft_anatomy(g,skin,rings,torso_weights,36)
    # Separate continuous pant waist/groin clothing shell hides skin bleed
    # at seated/standing hip joints. Still requires independent cloth fitting.
    trousers="slatePants" if which==0 else "ochrePants"
    pant_rings=[(.55,0,.117,.092),(.665,0,.175,.117),
                (.755,0,hips*1.095,.141),(.858,0,hips*1.12,.148),
                (.940,0,hips*1.025,.134),(1.020,0,waist*1.15,.121)]
    h.loft_anatomy(g,trousers,pant_rings,lambda y:("pelvis","spine",max(0,min(1,(1.08-y)/.18))),sides=36)
    # Neutral pelvis and groin bridge, not detailed genital geometry.
    g.ellipsoid(skin,(0,.820,.0),(hips*.90,.126,.106),"pelvis",16,24)
    for sign,side in ((-1,"L"),(1,"R")):
        hip,knee,ankle=[h.v1.POS[f"{role}_{side}"]
                         for role in ("hip","knee","ankle")]
        # Smooth under-layer: narrower radii than garment shells.
        g.tube(skin,hip,knee,.097,.069,
               f"hip_{side}",f"knee_{side}",steps=20,sides=24)
        g.tube(skin,knee,ankle,.069,.048,
               f"knee_{side}",f"ankle_{side}",steps=20,sides=24)
        g.ellipsoid(skin,(sign*.14,.05,-.093),
                    (.064,.044,.123),f"ankle_{side}",12,24)
        shoulder,elbow,wrist=[h.v1.POS[f"{role}_{side}"]
                             for role in ("shoulder","elbow","wrist")]
        under=(sign*.197,1.343,0)
        g.tube(skin,under,elbow,.061,.045,
               f"shoulder_{side}",f"elbow_{side}",steps=18,sides=24)
        g.tube(skin,elbow,wrist,.044,.033,
               f"elbow_{side}",f"wrist_{side}",steps=18,sides=24)
    # Head, neck, palms and feet already in the same skin material.
    return g

def build_body(input_path):
    prev=h.v1.figure_geometry
    try:
        h.v1.figure_geometry=adult_body_geometry
        receipt=h.v1.make_demo(input_path)
    finally:
        h.v1.figure_geometry=prev
    return receipt

def _slot_for_material(name):
    return CLOTH_MATERIAL.get(name,"body")

def split_skinned_layers(src,out,manifest_path):
    original=Path(src).read_bytes()
    d,b=decode(original)
    if d["extras"].get("source_class")!="ORIGINAL_SELF_AUTHORED_SYNTHETIC":
        raise ValueError("NOT_ORIGINAL_SOURCE")
    if len(d["skins"])!=2 or len(d["meshes"])!=2:
        raise ValueError("EXPECTED_TWO_35_JOINT_SOURCE_MESHES")
    if any(len(s["joints"])!=35 for s in d["skins"]):
        raise ValueError("EXPECTED_35_JOINTS")
    old_meshes=d["meshes"]
    new_meshes=[]
    placements={}
    slots={}
    names={n["name"]:i for i,n in enumerate(d["nodes"])}
    for actor_i,actor in enumerate(ACTORS):
        root=names[actor+"_SceneRoot"]
        source_node=names[actor+"_SkinnedGeometry"]
        grouped={s:[] for s in SLOTS}
        for prim in old_meshes[actor_i]["primitives"]:
            mat=d["materials"][prim["material"]]["name"]
            grouped[_slot_for_material(mat)].append(prim)
        for required in ("body","hair","top","bottom","footwear"):
            if not grouped[required]:raise ValueError("MISSING_CLOTHING_SLOT:"+required)
        # Material variations are independent skinned nodes (same cut for MVP).
        for slot,fromslot in (("alt_top","top"),("alt_bottom","bottom")):
            altmat=len(d["materials"])
            base_mat=d["materials"][grouped[fromslot][0]["material"]]
            m=json.loads(json.dumps(base_mat))
            m["name"]=actor+"_"+slot+"_alternate"
            m["pbrMetallicRoughness"]["baseColorFactor"]=list(ALT_COLORS[actor][slot])
            d["materials"].append(m)
            for prim in grouped[fromslot]:
                duplicate=json.loads(json.dumps(prim))
                duplicate["material"]=altmat
                grouped[slot].append(duplicate)
        placements[actor]={}
        for slot,prims in grouped.items():
            if not prims:continue
            meshid=len(new_meshes)
            new_meshes.append({"name":actor+"_"+slot+"_SeparateSkinnedMesh",
                               "primitives":prims})
            node_name=actor+"_Wardrobe_"+slot
            if slot=="body":
                node=d["nodes"][source_node]
                node["name"]=node_name
                node["mesh"]=meshid
                node["skin"]=actor_i
                idx=source_node
            else:
                idx=len(d["nodes"])
                d["nodes"].append({"name":node_name,"mesh":meshid,"skin":actor_i,
                  "extras":{"wardrobe_slot":slot,"actor":actor,
                            "mutable":True}})
                d["nodes"][root].setdefault("children",[]).append(idx)
            placements[actor][slot]={"node":idx,"mesh":meshid,"skin":actor_i,
                                       "material_ids":sorted(set(p["material"] for p in prims))}
        slots[actor]=sorted(placements[actor])
    d["meshes"]=new_meshes
    d["extras"]["wardrobe_contract"]={
      "schema":"scp.original_wardrobe.v1",
      "rig_joints_each":35,
      "default_preset":"signature",
      "presets":{k:list(v) for k,v in PRESETS.items()},
      "nude_base":"adult_anatomically_neutral_unclothed_mesh_no_explicit_detail",
      "interchange":"separately skinned mesh nodes, one shared skin per actor",
      "body_unmodified_by_preset":True,
      "appearance_approved":False}
    outbytes=glb_pack(d,b)
    Path(out).write_bytes(outbytes)
    manifest={
       "schema":"scp.original_wardrobe_manifest.v1",
       "source_sha256":hashlib.sha256(original).hexdigest(),
       "derived_sha256":hashlib.sha256(outbytes).hexdigest(),
       "source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
       "subjects":list(ACTORS),"presets":{k:list(v) for k,v in PRESETS.items()},
       "actor_slots":placements,
       "editable_in":"Blender imported scene; garments share respective 35-joint armature",
       "default_visible":"signature",
       "separate_new_geometry_for_alternate":False,
       "alternate_differences":"independently selectable material/color variations, same initial garment cut",
       "body_detail":"anatomically neutral adult base, no explicit anatomical detailing",
       "known_limits":["body surface is a bounded procedural sculpt, not high fidelity",
         "garment/body intersection and physical cloth dynamics NOT QUALIFIED",
         "hair is a separable groom layer",
         "no force/pressure/ROM or human realism pass"],
       "source_preserved":True,"release_approved":False}
    Path(manifest_path).write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest

def build(out,manifest):
    with tempfile.TemporaryDirectory() as root:
        root=Path(root)
        generated=root/"adult_base_17.glb"
        rig=root/"adult_base_35.glb"
        gait=root/"adult_gait35.glb"
        build_body(generated)
        main_expand(generated,rig)
        animate(rig,gait)
        return split_skinned_layers(gait,out,manifest)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",required=True)
    ap.add_argument("--manifest",required=True)
    args=ap.parse_args()
    result=build(args.out,args.manifest)
    print(json.dumps({"derived_sha256":result["derived_sha256"],
      "slots":{k:list(v) for k,v in result["actor_slots"].items()},
      "presets":result["presets"]},sort_keys=True))
