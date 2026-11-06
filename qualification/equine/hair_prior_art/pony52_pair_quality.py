"""Independent measured 5.2 six-source-follicle Physics vs Animation oracle.

This validates actual body-derived root motion only on six artificial proxy
emitter spheres. It NEVER claims full equine fur collision/biology/renderer.
"""
import hashlib
import json
import math
from pony_source_trajectory import classify,REGIONS,xyz,distance

def quality(source,physics,animation):
    src=classify(source)
    by_region={r:tuple(g["card_id"] for g in source["guides"] if g["region"]==r) for r in REGIONS}
    expected=set(i for ids in by_region.values() for i in ids)
    result={}
    for mode,data in (("physics",physics),("animation",animation)):
        if type(data)!=dict or data.get("schema")!="equine.pony.xpbd_source_proxy_48f.v1" or data.get("mode")!=mode:
            raise ValueError("invalid native experiment class")
        if data.get("source_capsule_sha256")!=src["source_capsule_sha256"] or data.get("source_blend_sha256")!=source["source_blend_sha256"]:
            raise ValueError("not the exact authoritative pony source")
        if data.get("source_rig")!="PonyRig30" or data.get("source_cards_total")!=1050 or data.get("errors") or data.get("status")!="SOURCE_48F_PROXY_GEOMETRY_MEASURED_NO_SCIENCE":
            raise ValueError("missing source/accepted data is an error")
        if data.get("not_original_body_collision") is not True or data.get("production_blender_4_5_15_untouched") is not True or data.get("science_hold")!="KEEP" or data.get("release_admission") is not False:
            raise ValueError("undocumented science/rights admission")
        if data.get("frame_count")!=48 or data.get("guide_count")!=6 or type(data.get("frames"))!=list or len(data["frames"])!=48:
            raise ValueError("missing six by 48 source observations")
        parsed=[]
        for idx,frame in enumerate(data["frames"]):
            if type(frame)!=dict or type(frame.get("frame")) is not int or frame["frame"]!=idx+1 or type(frame.get("samples"))!=list or len(frame["samples"])!=6:
                raise ValueError("missing or reordered native frame")
            observed={}
            for row in frame["samples"]:
                if type(row)!=dict or set(row)!={"card_id","region","root_world_m","tip_world_m","source_root_m","tip_minus_root_m","source_skin_root_error_m"}:
                    raise ValueError("forged sampled region or field")
                card=row["card_id"]
                if type(card)!=int or card not in expected or card in observed or row["region"]!=next(r for r,ids in by_region.items() if card in ids):
                    raise ValueError("wrong source card")
                original=next(x for x in source["guides"] if x["card_id"]==card)
                target=xyz(original["samples"][idx]["root_m"])
                root,tip,claim=xyz(row["root_world_m"]),xyz(row["tip_world_m"]),xyz(row["tip_minus_root_m"])
                if distance(root,target)>.02 or distance(root,xyz(row["source_root_m"]))>.02:
                    raise ValueError("head/skin follicle attachment lost")
                if distance(tuple(tip[k]-root[k] for k in range(3)),claim)>1e-6:
                    raise ValueError("forged relative tip position")
                err=row["source_skin_root_error_m"]
                if type(err) not in (int,float) or not math.isfinite(err) or abs(err-distance(root,target))>1e-6:
                    raise ValueError("bad root error receipt")
                observed[card]=claim
            if set(observed)!=expected:raise ValueError("source group cardinality changed")
            parsed.append(observed)
        result[mode]=parsed
    moves={};control={}
    for region,card_ids in by_region.items():
        moves[region]=max(distance(result["physics"][f][card],result["physics"][0][card])
            for f in range(48) for card in card_ids)
        control[region]=max(distance(result["animation"][f][card],result["animation"][0][card])
            for f in range(48) for card in card_ids)
    maxdiff=max(distance(result["physics"][f][card],result["animation"][f][card])
        for f in range(48) for card in expected)
    # Some actual pony root groups may be static. Distinguish failures
    # without inventing an imposed sinusoidal source trajectory.
    independent=max(moves.values())>=.001 and maxdiff>=.001
    negative_ok=max(control.values())<=.0001
    if not negative_ok or not independent:
        raise ValueError("source-derived XPBD secondary motion not separated from rigid skin")
    return {"schema":"equine.pony.xpbd_source_proxy.paired_quality.v1",
            "source_blend_sha256":source["source_blend_sha256"],
            "source_capsule_sha256":src["source_capsule_sha256"],
            "frames":48,"guides":6,"regions":["mane","forelock","tail"],
            "max_physics_tip_delta_m_by_region":{k:round(v,7) for k,v in moves.items()},
            "max_animation_control_delta_m_by_region":{k:round(v,7) for k,v in control.items()},
            "max_physics_vs_animation_diff_m":round(maxdiff,7),
            "verdict":"SOURCE_PONY_PROXY_SECONDARY_MOTION_ENGINEERING_ONLY",
            "body_and_hair_collision":"NOT_TESTED","visual_quality":"UNKNOWN",
            "material_calibration":"UNKNOWN","science_hold":"KEEP",
            "release_or_CPE_admission":False}
def main():
    import pathlib,sys
    if len(sys.argv)!=5:raise SystemExit("usage: pony52_pair_quality.py source.json physics.json animation.json receipt.json")
    objs=[json.loads(pathlib.Path(x).read_text()) for x in sys.argv[1:4]]
    r=quality(*objs)
    out=pathlib.Path(sys.argv[4])
    if out.exists():raise ValueError("refuse overwrite")
    out.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("PONY_30J_SOURCE_XPBD_VS_RIGID_ENGINEERING_ONLY",r)
if __name__=="__main__":main()
