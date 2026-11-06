"""Independent stdlib source capsule validator for original 30-joint equine guides."""
import hashlib
import json
import math

SCHEMA="equine.pony.guide_source_48f.v1"
REGIONS=("mane","forelock","tail")
REGION_BOUNDS={"mane":(0,440),"forelock":(440,670),"tail":(670,1050)}
REGION_BONES={"mane":{"neck","head"},"forelock":{"head"},"tail":{"tail_1","tail_2","tail_3"}}

def xyz(p):
    if type(p) not in (list,tuple) or len(p)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>100 for x in p):
        raise ValueError("nonfinite/unbounded source 3D point")
    return tuple(float(x) for x in p)
def distance(a,b):
    return math.sqrt(sum((a[k]-b[k])**2 for k in range(3)))
def classify(c):
    if type(c)!=dict or set(c)!={"schema","source_kind","source_blend_sha256","rig","cards_total","vertices_per_card","fps","frames","guides","visual_science_hold"}:
        raise ValueError("missing or undeclared source claims")
    if c["schema"]!=SCHEMA or c["source_kind"]!="original_synthetic" or c["rig"]!="PonyRig30" or c["cards_total"]!=1050 or c["vertices_per_card"]!=10:
        raise ValueError("wrong original source topology")
    if c["fps"]!=24 or c["frames"]!=48 or c["visual_science_hold"]!="KEEP":
        raise ValueError("wrong timeline/science admission")
    sha=c["source_blend_sha256"]
    if type(sha)!=str or len(sha)!=64 or any(x not in "0123456789abcdef" for x in sha):
        raise ValueError("unverified source blend digest")
    if type(c["guides"])!=list or len(c["guides"])!=6:
        raise ValueError("wrong source guide count")
    seen=set()
    chosen={r:[] for r in REGIONS}
    for g in c["guides"]:
        if type(g)!=dict or set(g)!={"card_id","region","owner_bone","samples"}:
            raise ValueError("unqualified source guide fields")
        card,region,bone=g["card_id"],g["region"],g["owner_bone"]
        if type(card)!=int or region not in REGION_BOUNDS or not REGION_BOUNDS[region][0]<=card<REGION_BOUNDS[region][1] or card in seen:
            raise ValueError("wrong/duplicate source follicle ID")
        seen.add(card)
        chosen[region].append(bone)
        if bone not in REGION_BONES[region]:
            raise ValueError("unknown skinned pony source")
        if type(g["samples"])!=list or len(g["samples"])!=48:
            raise ValueError("incomplete 48-frame pony root/tip")
        previous=None
        for index,item in enumerate(g["samples"]):
            if type(item)!=dict or set(item)!={"frame","root_m","tip_m"} or type(item["frame"])!=int or item["frame"]!=index+1:
                raise ValueError("reordered/forged frame")
            root,tip=xyz(item["root_m"]),xyz(item["tip_m"])
            length=distance(root,tip)
            if length<.02 or length>1.0:
                raise ValueError("wrong guide segment length")
            if previous and distance(root,previous)>1:
                raise ValueError("unbounded source root motion between adjacent frames")
            previous=root
    if any(len(chosen[r])!=2 for r in REGIONS):
        raise ValueError("two distinct sampled follicles required per region")
    if set(chosen["mane"])!={"head","neck"}:
        raise ValueError("mane source must cover neck and head attachments")
    if len(set(chosen["tail"]))!=2:
        raise ValueError("tail source must cover two distinct animated bone owners")
    raw=json.dumps(c,sort_keys=True,separators=(",",":")).encode()
    return {"schema":"equine.pony.guide_source_check.v1",
            "source_capsule_sha256":hashlib.sha256(raw).hexdigest(),
            "source_blend_sha256":sha,"frame_count":48,"guides":6,
            "owner_regions":list(REGIONS),"verdict":"PASS_REAL_SOURCE_GEOMETRY_ONLY",
            "physical_hair_simulation_proven":False,
            "collision_acceptance":False,"release_admission":False}

