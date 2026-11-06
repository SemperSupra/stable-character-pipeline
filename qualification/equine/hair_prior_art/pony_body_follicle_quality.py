"""Independent, source-only gate for real pony skin/body hair root candidates.

This validates a persistent f1 barycentric triangle/vertex anchor and 48-frame
actual body proximity as diagnostic observations. It NEVER snaps a follicle,
asserts closed/signed geometry, or accepts anatomy/material/visual science.
"""
import json
import math
from pony_source_trajectory import classify as classify_source,xyz,distance
from pony52_actual_surface_native import REGION_TARGETS

def percentile(values,p):
    ordered=sorted(values)
    if not ordered or any(not math.isfinite(v) or not 0<=v<=100 for v in ordered):
        raise ValueError("invalid measured distance")
    return round(ordered[math.ceil(p*len(ordered))-1],8)
def normal(v):
    p=xyz(v)
    if abs(sum(x*x for x in p)-1)>.001:raise ValueError("nonunit source surface normal")
    return p
def weights(v):
    if type(v)!=list or len(v)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) or x<-1e-4 or x>1.0001 for x in v) or abs(sum(v)-1)>1e-5:
        raise ValueError("invalid actual triangle barycentric")
    return v
def evaluate(source,projection):
    gate=classify_source(source)
    if type(projection)!=dict or set(projection)!={"schema","source_blend_sha256","source_capsule_sha256","source_kind","rig","source_original_body_mesh_count","source_mesh_names","frame_count","guide_count","cards","body_closed_volume_validated","nearest_geometry_is_signed_inside_outside","original_source_roots_snapped","projection_admitted_as_animated_follicle","visual_scientific_hold","release_or_CPE_admission"}:
        raise ValueError("unbounded or missing original body source witness")
    if projection["schema"]!="equine.pony.original_body_follicle_projection_48f.v1" or projection["source_blend_sha256"]!=source["source_blend_sha256"] or projection["source_capsule_sha256"]!=gate["source_capsule_sha256"]:
        raise ValueError("body projection not same source")
    if projection["source_kind"]!="original_synthetic" or projection["rig"]!="PonyRig30" or projection["frame_count"]!=48 or projection["guide_count"]!=6:
        raise ValueError("source rig/frames invalid")
    if projection["source_original_body_mesh_count"]!=5 or type(projection["source_mesh_names"])!=list or len(projection["source_mesh_names"])!=5 or len(set(projection["source_mesh_names"]))!=5:
        raise ValueError("original measured body area count invalid")
    if not set(projection["source_mesh_names"])==set(name for group in REGION_TARGETS.values() for name in group):
        raise ValueError("missing/forged original body surface target")
    if projection["body_closed_volume_validated"] is not False or projection["nearest_geometry_is_signed_inside_outside"] is not False or projection["original_source_roots_snapped"] is not False or projection["projection_admitted_as_animated_follicle"] is not False or projection["visual_scientific_hold"]!="KEEP" or projection["release_or_CPE_admission"] is not False:
        raise ValueError("unsafe body source admission")
    if type(projection["cards"])!=list or len(projection["cards"])!=6:
        raise ValueError("not all original source card/body tracks")
    originals={g["card_id"]:g for g in source["guides"]}
    seen=set();by_region={r:{"dist":[],"persistent":[],"offset_drift":[],"hops":0,"rest_dist":[]} for r in REGION_TARGETS}
    anchors=[]
    for item in projection["cards"]:
        if type(item)!=dict or set(item)!={"card_id","region","owner_bone","frames","rest_anchor"}:
            raise ValueError("unexpected per-card body projection fields")
        id=item["card_id"]
        if type(id)!=int or id not in originals or id in seen or item["region"]!=originals[id]["region"] or item["owner_bone"]!=originals[id]["owner_bone"]:
            raise ValueError("forged hair card/body group")
        seen.add(id)
        original=originals[id]
        anchor=item["rest_anchor"]
        if type(anchor)!=dict or set(anchor)!={"source_body_object","rest_triangle_index","rest_triangle_vertex_ids","rest_barycentric","rest_projection_m","rest_root_to_skin_distance_m","rest_normal_m","rest_root_minus_anchor_m"}:
            raise ValueError("invalid rest body barycentric source fields")
        surface=anchor["source_body_object"]
        if surface not in REGION_TARGETS[item["region"]]:
            raise ValueError("root registered to wrong original anatomy")
        index=anchor["rest_triangle_index"]
        vids=anchor["rest_triangle_vertex_ids"]
        if type(index)!=int or index<0 or index>2000000 or type(vids)!=list or len(vids)!=3 or len(set(vids))!=3 or any(type(v)!=int or not 0<=v<2000000 for v in vids):
            raise ValueError("invalid persistent source surface triangle id")
        weights(anchor["rest_barycentric"])
        restpos=xyz(anchor["rest_projection_m"])
        rest_root=xyz(original["samples"][0]["root_m"])
        delta=xyz(anchor["rest_root_minus_anchor_m"])
        if distance(tuple(rest_root[k]-restpos[k] for k in range(3)),delta)>1e-5:
            raise ValueError("rest root and world surface offset not reconciled")
        n=normal(anchor["rest_normal_m"])
        restdist=distance(restpos,rest_root)
        if type(anchor["rest_root_to_skin_distance_m"]) not in (int,float) or abs(restdist-anchor["rest_root_to_skin_distance_m"])>1e-5:
            raise ValueError("rest root source-to-body distance not measured")
        records=item["frames"]
        if type(records)!=list or len(records)!=48:raise ValueError("body 48-frame trajectory incomplete")
        for fi,r in enumerate(records):
            if type(r)!=dict or set(r)!={"frame","source_root_m","nearest_body_object","nearest_face_index","nearest_face_vertex_ids","nearest_barycentric","nearest_body_point_m","nearest_surface_normal","nearest_unsigned_distance_m","normal_directional_offset_m","rest_persistent_anchor_point_m","rest_anchor_current_unsigned_distance_m","world_fixed_offset_drift_m"}:
                raise ValueError("unexpected source body observer fields")
            if type(r["frame"])!=int or r["frame"]!=fi+1 or distance(xyz(r["source_root_m"]),xyz(original["samples"][fi]["root_m"]))>1e-6:
                raise ValueError("source bone/root frame mismatch")
            body=r["nearest_body_object"]
            if body not in REGION_TARGETS[item["region"]]:
                raise ValueError("wrong body mesh for region")
            face=r["nearest_face_index"];v=r["nearest_face_vertex_ids"]
            if type(face)!=int or face<0 or face>2000000 or type(v)!=list or len(v)!=3 or len(set(v))!=3 or any(type(x)!=int or not 0<=x<2000000 for x in v):
                raise ValueError("invalid nearest face")
            weights(r["nearest_barycentric"])
            closest=xyz(r["nearest_body_point_m"])
            surface_n=normal(r["nearest_surface_normal"])
            observed=xyz(r["source_root_m"])
            nearest=distance(closest,observed)
            if type(r["nearest_unsigned_distance_m"]) not in (int,float) or abs(nearest-r["nearest_unsigned_distance_m"])>1e-5:
                raise ValueError("false source-root nearest body distance")
            signed=sum((observed[i]-closest[i])*surface_n[i] for i in range(3))
            if type(r["normal_directional_offset_m"]) not in (int,float) or not math.isfinite(r["normal_directional_offset_m"]) or abs(signed-r["normal_directional_offset_m"])>1e-5:
                raise ValueError("body normal projection not internally consistent")
            fixed=xyz(r["rest_persistent_anchor_point_m"])
            d_fixed=distance(fixed,observed)
            if type(r["rest_anchor_current_unsigned_distance_m"]) not in (int,float) or abs(d_fixed-r["rest_anchor_current_unsigned_distance_m"])>1e-5:
                raise ValueError("original barycentric anchor drift falsified")
            drift=distance(tuple(observed[i]-fixed[i] for i in range(3)),delta)
            if type(r["world_fixed_offset_drift_m"]) not in (int,float) or not math.isfinite(r["world_fixed_offset_drift_m"]) or abs(drift-r["world_fixed_offset_drift_m"])>1e-5:
                raise ValueError("static source offset drift receipt false")
            if fi==0 and (body!=surface or face!=index or distance(fixed,restpos)>1e-5 or nearest>restdist+1e-5):
                raise ValueError("rest candidate does not match first-frame native evidence")
            reg=by_region[item["region"]]
            reg["dist"].append(nearest)
            reg["persistent"].append(d_fixed)
            reg["offset_drift"].append(drift)
            if fi and (body!=surface or face!=index):reg["hops"]+=1
        by_region[item["region"]]["rest_dist"].append(restdist)
        anchors.append({"card_id":id,"region":item["region"],"source_bone":item["owner_bone"],
                        "body_surface":surface,"rest_face":index,"rest_vertex_ids":vids,
                        "rest_barycentric":anchor["rest_barycentric"],
                        "rest_root_unsigned_distance_m":round(restdist,8)})
    if seen!=set(originals):raise ValueError("original body track not complete")
    sections={}
    for key,values in by_region.items():
        sections[key]={
            "nearest_root_to_body_min_m":round(min(values["dist"]),8),
            "nearest_root_to_body_p95_m":percentile(values["dist"],.95),
            "nearest_root_to_body_max_m":round(max(values["dist"]),8),
            "persistent_rest_face_root_distance_p95_m":percentile(values["persistent"],.95),
            "world_fixed_offset_drift_p95_m":percentile(values["offset_drift"],.95),
            "nearest_face_changes_from_rest_count":values["hops"],
            "first_frame_root_distance_max_m":round(max(values["rest_dist"]),8),
            "sample_count":len(values["dist"])}
    return {"schema":"equine.pony.source_body_follicle_qualification.v1",
        "source_blend_sha256":source["source_blend_sha256"],
        "source_capsule_sha256":gate["source_capsule_sha256"],
        "frames":48,"guides":6,"regions":sections,
        "rest_source_body_anchor_proposals":sorted(anchors,key=lambda x:x["card_id"]),
        "candidate_is_retargetable":False,
        "normal_directional_offset_is_signed_volume":False,
        "watertight_body_mesh_validated":False,
        "original_source_root_snapping_performed":False,
        "source_follicle_anatomy_visual_accepted":False,
        "science_hold":"KEEP","release_admission":False}
def main():
    import sys
    from pathlib import Path
    if len(sys.argv)!=4:raise SystemExit("usage: pony_body_follicle_quality.py source.json native_body.json out.json")
    source,obs=[json.loads(Path(x).read_text()) for x in sys.argv[1:3]]
    result=evaluate(source,obs)
    p=Path(sys.argv[3])
    if p.exists():raise ValueError("would overwrite body evidence")
    p.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("SOURCE_ORIGINAL_BODY_BARYCENTRIC_CANDIDATES_UNADMITTED",json.dumps(result,sort_keys=True))
if __name__=="__main__":main()
