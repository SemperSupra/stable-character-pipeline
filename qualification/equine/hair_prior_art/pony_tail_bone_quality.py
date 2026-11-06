"""Independent original-source caudal root/bone chain versus rump proximity.

Pose-bone centerlines are NOT skinned caudal surfaces; comparing distances
only informs whether modeling a real tail shaft is the next anatomical work.
Reject forged source/segment projections, source rights or science claims.
"""
import json
import math
from pony_source_trajectory import classify as source_gate, xyz, distance
from pony_body_follicle_quality import evaluate as body_quality

def check(source,body,caudal):
    gate=source_gate(source)
    qualified_body=body_quality(source,body)
    if type(caudal)!=dict or set(caudal)!={"schema","source_blend_sha256","source_capsule_sha256","source_kind","rig","frames","bone_names","tail_cards","bone_centerline_is_surface","new_tail_shaft_generated","source_roots_snapped_to_bones","anatomical_acceptance","scientific_hold","release_or_CPE_admission"}:
        raise ValueError("unknown/missing original caudal evidence fields")
    if caudal["schema"]!="equine.pony.original_caudal_bone_centerline_48f.v1" or caudal["source_blend_sha256"]!=source["source_blend_sha256"] or caudal["source_capsule_sha256"]!=gate["source_capsule_sha256"]:
        raise ValueError("caudal original source not SHA bound")
    if caudal["source_kind"]!="original_synthetic" or caudal["rig"]!="PonyRig30" or caudal["frames"]!=48 or caudal["bone_names"]!=["tail_1","tail_2","tail_3"]:
        raise ValueError("unknown caudal source skeleton")
    if any(caudal[k] is not False for k in ("bone_centerline_is_surface","new_tail_shaft_generated","source_roots_snapped_to_bones","anatomical_acceptance","release_or_CPE_admission")) or caudal["scientific_hold"]!="KEEP":
        raise ValueError("caudal surrogate incorrectly admitted as anatomical geometry")
    if type(caudal["tail_cards"])!=list or len(caudal["tail_cards"])!=2:
        raise ValueError("expected exactly two original tail source cards")
    originals={g["card_id"]:g for g in source["guides"] if g["region"]=="tail"}
    if len(originals)!=2 or type(body["cards"])!=list:
        raise ValueError("original tail/root evidence missing")
    bybody={g["card_id"]:g for g in body["cards"] if g["region"]=="tail"}
    if set(bybody)!=set(originals):
        raise ValueError("body source tail card mismatch")
    seen=set();per_card=[]
    for item in caudal["tail_cards"]:
        if type(item)!=dict or set(item)!={"card_id","region","owner_bone","frames"}:
            raise ValueError("unexpected caudal card fields")
        id=item["card_id"]
        if type(id)!=int or id not in originals or id in seen or item["owner_bone"]!=originals[id]["owner_bone"] or item["region"]!="tail":
            raise ValueError("unqualified original caudal owner/card")
        seen.add(id)
        frames=item["frames"]
        if type(frames)!=list or len(frames)!=48:
            raise ValueError("missing caudal 48-frame observations")
        distnear=[];distowner=[];owner_nearest=0
        for k,record in enumerate(frames):
            if type(record)!=dict or set(record)!={"frame","source_root_m","closest_tail_bone","source_owner_tail_bone","candidate_bone_distances"}:
                raise ValueError("unexpected caudal native segment witness")
            if type(record["frame"])!=int or record["frame"]!=k+1:
                raise ValueError("source caudal frame out of order")
            root=xyz(record["source_root_m"])
            if distance(root,xyz(originals[id]["samples"][k]["root_m"]))>1e-6:
                raise ValueError("source caudal root not identical to SHA-bound capsule")
            candidates=record["candidate_bone_distances"]
            if type(candidates)!=list or len(candidates)!=3 or [r.get("bone") for r in candidates]!=["tail_1","tail_2","tail_3"]:
                raise ValueError("missing or duplicate true caudal bones")
            def verify(x):
                if type(x)!=dict or set(x)!={"bone","root_distance_to_bone_centerline_m","bone_segment_fraction","nearest_bone_centerline_point_m"}:
                    raise ValueError("forged bone witness geometry")
                if x["bone"] not in ("tail_1","tail_2","tail_3"):
                    raise ValueError("bone centerline not original tail skeleton")
                q=xyz(x["nearest_bone_centerline_point_m"])
                dist=distance(root,q)
                claimed=x["root_distance_to_bone_centerline_m"]
                t=x["bone_segment_fraction"]
                if type(claimed) not in (int,float) or not math.isfinite(claimed) or abs(dist-claimed)>1e-5:
                    raise ValueError("distance to caudal bone centerline not independently verified")
                if type(t) not in (int,float) or not math.isfinite(t) or not 0<=t<=1:
                    raise ValueError("closest caudal segment fraction false")
                return dist
            values={x["bone"]:verify(x) for x in candidates}
            closest=record["closest_tail_bone"]
            owner=record["source_owner_tail_bone"]
            dc=verify(closest);do=verify(owner)
            if abs(dc-min(values.values()))>1e-5 or closest["bone"]!=min(values,key=lambda n:(values[n],n)):
                raise ValueError("nearest original caudal bone contradicted by measurements")
            if owner["bone"]!=item["owner_bone"] or abs(do-values[owner["bone"]])>1e-5:
                raise ValueError("forged owner caudal bone correspondence")
            distnear.append(dc);distowner.append(do)
            if closest["bone"]==item["owner_bone"]:owner_nearest+=1
        body_rest=bybody[id]["rest_anchor"]["rest_root_to_skin_distance_m"]
        body_max=max(x["nearest_unsigned_distance_m"] for x in bybody[id]["frames"])
        first=distnear[0]
        per_card.append({
            "card_id":id,"source_owner_bone":item["owner_bone"],
            "rest_root_to_nearest_tail_bone_m":round(first,8),
            "rest_root_to_own_tail_bone_m":round(distowner[0],8),
            "rest_root_to_tested_rump_surface_m":round(float(body_rest),8),
            "rest_nearest_bone_vs_tested_rump_ratio":round(first/max(float(body_rest),1e-10),7),
            "maximum_48f_nearest_caudal_bone_m":round(max(distnear),8),
            "maximum_48f_nearest_tested_body_m":round(float(body_max),8),
            "owner_is_nearest_in_frames":owner_nearest,
            "frames":48,
            "nearer_to_cauda_bone_than_tested_rump_at_rest":first<float(body_rest)})
    if seen!=set(originals):
        raise ValueError("caudal observations not same source cardinality")
    return {"schema":"equine.pony.source_caudal_bone_vs_rump_48f.v1",
        "source_blend_sha256":source["source_blend_sha256"],
        "source_capsule_sha256":gate["source_capsule_sha256"],
        "caudal_bone_centerline_distances":sorted(per_card,key=lambda x:x["card_id"]),
        "body_projection_source_confirmed":qualified_body["schema"],
        "bone_centerline_not_skinned_surface":True,
        "tail_shaft_geometry_missing_or_undetermined":True,
        "no_anatomical_snapping_or_new_surface":True,
        "science_hold":"KEEP","release_or_CPE_admission":False}
def main():
    from pathlib import Path
    import sys
    if len(sys.argv)!=5:
        raise SystemExit("usage: pony_tail_bone_quality.py source.json body.json caudal.json output.json")
    source,body,caudal=[json.loads(Path(p).read_text()) for p in sys.argv[1:4]]
    r=check(source,body,caudal)
    out=Path(sys.argv[4])
    if out.exists():raise ValueError("refuse overwrite source/bone receipt")
    out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("ORIGINAL_CAUDAL_BONE_IS_NOT_TAIL_SHAFT",json.dumps(r,sort_keys=True))
if __name__=="__main__":main()
