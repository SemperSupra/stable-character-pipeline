#!/usr/bin/env python3
"""Independent GLB proof that a skinned torso and painted pinto survived export."""
import json,struct,sys
from pathlib import Path
def check(path,coat):
    b=Path(path).read_bytes()
    if b[:4]!=b"glTF" or struct.unpack_from("<I",b,8)[0]!=len(b):raise ValueError("invalid GLB")
    n,typ=struct.unpack_from("<II",b,12)
    if typ!=0x4E4F534A:raise ValueError("bad GLB JSON chunk")
    d=json.loads(b[20:20+n].decode().strip())
    names=[m.get("name","") for m in d["meshes"]]
    body=[m for m in d["meshes"] if "continuous_shetland_barrel_rump_shoulder" in m.get("name","")]
    if len(body)!=1:raise ValueError("unified torso missing")
    if any(x in names for x in ("barrel","rump","shoulder","white_collar","white_rump","white_belly")):
        raise ValueError("legacy disjoint torso or raised white pinto patches remain")
    if not d.get("skins") or max(len(x.get("joints",[])) for x in d["skins"])<26 or not d.get("animations"):
        raise ValueError("missing skin/rig/animation")
    prims=body[0]["primitives"]
    if not prims or any("JOINTS_0" not in m.get("attributes",{}) or "WEIGHTS_0" not in m.get("attributes",{}) for m in prims):
        raise ValueError("unskinned continuous torso")
    distinct={p.get("material",-1) for p in prims}
    if coat=="pinto" and len(distinct)<2:raise ValueError("pinto patch materials not exported")
    if coat!="pinto" and len(distinct)!=1:raise ValueError("unexpected base coat splits")
    return {"coat":coat,"rig_joint_count":max(len(x["joints"]) for x in d["skins"]),
            "torso_skin_primitives":len(prims),"torso_material_regions":len(distinct),
            "legacy_pinto_surface_blobs":False,"animation_count":len(d["animations"]),
            "visual_quality":"NOT_ACCEPTED"}
if __name__=="__main__":
    if len(sys.argv)!=3:raise SystemExit("usage: appearance_glb_verify.py file.glb black|pinto|white")
    print(json.dumps(check(sys.argv[1],sys.argv[2]),sort_keys=True))
