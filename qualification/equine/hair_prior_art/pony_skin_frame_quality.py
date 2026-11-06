"""Independent source-only test for original 30j card-vs-bone-vs-5.2 rigid frames."""
import json
import math
from pony_source_trajectory import classify as validate_source,xyz,distance

def metric(xs):
    if not xs or any(not math.isfinite(x) or x<0 or x>100 for x in xs):
        raise ValueError("nonfinite source-frame residual")
    ordered=sorted(xs)
    return {"max_m":round(max(xs),8),
            "p95_m":round(ordered[math.ceil(.95*len(xs))-1],8),
            "median_m":round(ordered[len(xs)//2],8)}
def assess(capsule,frames,animation):
    source=validate_source(capsule)
    if not isinstance(frames,dict) or set(frames)!={"schema","source_blend_sha256","source_capsule_sha256","source_kind","rig","frame_count","cards","bone_transport_proof","wind_morphs_disabled","scientific_hold","hair_material_accepted","release_or_CPE_admission"}:
        raise ValueError("unknown/missing original bone frame source fields")
    if frames["schema"]!="equine.pony.source_skin_bone_frame_48f.v1" or frames["source_blend_sha256"]!=capsule["source_blend_sha256"] or frames["source_capsule_sha256"]!=source["source_capsule_sha256"]:
        raise ValueError("bone-frame observer not source bound")
    if frames["source_kind"]!="original_synthetic" or frames["rig"]!="PonyRig30" or frames["frame_count"]!=48 or frames["bone_transport_proof"]!="rest-to-pose source rig matrix, world-space" or frames["wind_morphs_disabled"] is not True:
        raise ValueError("original source bone-motion provenance missing")
    if frames["scientific_hold"]!="KEEP" or frames["hair_material_accepted"] is not False or frames["release_or_CPE_admission"] is not False:
        raise ValueError("source scientific and rights hold violated")
    if not isinstance(animation,dict) or animation.get("schema")!="equine.pony52.attached_original_groom_48f.v1" or animation.get("mode")!="animation" or animation.get("modifier_mode")!="Animation":
        raise ValueError("not a real 5.2 rigid Animation control")
    if animation.get("source_blend_sha256")!=capsule["source_blend_sha256"] or animation.get("source_capsule_sha256")!=source["source_capsule_sha256"] or animation.get("source_surface")!="geometric_coat_mane_tail" or animation.get("rest_capture_order")!="armature_then_capture":
        raise ValueError("5.2 control different source/experiment")
    if animation.get("errors") or animation.get("status")!="48F_ORIGINAL_SKIN_GROOM_NATIVE_GEOMETRY_OBSERVED" or animation.get("frame_count")!=48 or animation.get("guide_count")!=6:
        raise ValueError("rigid control failed native 48f gate")
    if animation.get("science_hold")!="KEEP" or animation.get("release_admission") is not False:
        raise ValueError("rigid control bypasses science hold")
    if type(frames["cards"])!=list or len(frames["cards"])!=6 or type(animation.get("frames"))!=list or len(animation["frames"])!=48:
        raise ValueError("incomplete source-fiber trajectory")
    cards={g["card_id"]:g for g in capsule["guides"]}
    seen=set()
    region={g["region"]:{"bone_root":[],"bone_tip":[],"native_rigid":[],"bone_vs_rigid":[],"f1_rigid":[],"f7_rigid":[]} for g in capsule["guides"]}
    for record in frames["cards"]:
        if type(record)!=dict or set(record)!={"card_id","region","owner_bone","frames"}:
            raise ValueError("unknown source bone frame metadata")
        id=record["card_id"]
        if type(id)!=int or id not in cards or id in seen or record["owner_bone"]!=cards[id]["owner_bone"] or record["region"]!=cards[id]["region"]:
            raise ValueError("forged source owner/card identity")
        seen.add(id)
        if type(record["frames"])!=list or len(record["frames"])!=48:
            raise ValueError("incomplete source bone trajectory")
        for k,row in enumerate(record["frames"]):
            if type(row)!=dict or set(row)!={"frame","source_root_m","source_tip_m","bone_transport_predicted_root_m","bone_transport_predicted_tip_m","bone_transport_delta_quat_wxyz","source_bone_transport_root_error_m","source_bone_transport_tip_error_m"}:
                raise ValueError("unknown original bone frame witness")
            if type(row["frame"])!=int or row["frame"]!=k+1:
                raise ValueError("source bone frame order failure")
            expected=cards[id]["samples"][k]
            root,tip=xyz(row["source_root_m"]),xyz(row["source_tip_m"])
            if distance(root,xyz(expected["root_m"]))>1e-6 or distance(tip,xyz(expected["tip_m"]))>1e-6:
                raise ValueError("native original 4.5 source mismatches source capsule")
            pr,pt=xyz(row["bone_transport_predicted_root_m"]),xyz(row["bone_transport_predicted_tip_m"])
            quat=row["bone_transport_delta_quat_wxyz"]
            if type(quat)!=list or len(quat)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1.001 for x in quat) or abs(sum(x*x for x in quat)-1)>.00001:
                raise ValueError("nonunit/quaternion source bone transform")
            er,et=distance(root,pr),distance(tip,pt)
            for label,measured in (("source_bone_transport_root_error_m",er),("source_bone_transport_tip_error_m",et)):
                value=row[label]
                if type(value) not in (float,int) or not math.isfinite(value) or abs(value-measured)>1e-5:
                    raise ValueError("source bone residual receipt falsified")
            ar=animation["frames"][k]
            if type(ar)!=dict or ar.get("frame")!=k+1 or type(ar.get("guides"))!=list or len(ar["guides"])!=6:
                raise ValueError("source vs 5.2 control timeline mismatch")
            matches=[g for g in ar["guides"] if g.get("card_id")==id]
            if len(matches)!=1 or matches[0].get("region")!=record["region"]:
                raise ValueError("source/5.2 card id mismatch")
            native=matches[0]
            animdir=xyz(native["tip_minus_root_m"])
            native_root=xyz(native["actual_root_m"])
            native_tip=xyz(native["actual_tip_m"])
            if distance(tuple(native_tip[j]-native_root[j] for j in range(3)),animdir)>2e-6:
                raise ValueError("forged actual rigid tip vector")
            if distance(native_root,root)>.015:
                raise ValueError("5.2 native rigid root detached")
            observed=tuple(tip[j]-root[j] for j in range(3))
            transported=tuple(pt[j]-pr[j] for j in range(3))
            bname=record["region"]
            region[bname]["bone_root"].append(er)
            region[bname]["bone_tip"].append(et)
            region[bname]["native_rigid"].append(distance(animdir,observed))
            region[bname]["bone_vs_rigid"].append(distance(animdir,transported))
            if k==0:region[bname]["f1_rigid"].append(distance(animdir,observed))
            if k==6:region[bname]["f7_rigid"].append(distance(animdir,observed))
    if seen!=set(cards):raise ValueError("incomplete source owner/card coverage")
    report={r:{k:metric(v) for k,v in group.items()} for r,group in region.items()}
    bone_error=max(report[r]["bone_tip"]["max_m"] for r in report)
    rigid_error=max(report[r]["native_rigid"]["max_m"] for r in report)
    cause=("BONE_TRANSPORT_MATCHES_SOURCE_RIGID_52_SURFACE_FRAME_DRIFTS" if bone_error<=.005 and rigid_error>=.01
           else "SOURCE_BONE_TRANSPORT_ITSELF_NOT_VERIFIED" if bone_error>.005
           else "NO_STRONG_SOURCE_RIGID_MISMATCH_AT_THIS_SAMPLE")
    return {
        "schema":"equine.pony.source_bone_vs_52_rigid_oracle.v1",
        "source_blend_sha256":capsule["source_blend_sha256"],
        "source_capsule_sha256":source["source_capsule_sha256"],
        "frames":48,"cards":6,"regions":report,"hypothesis":cause,
        "bone_transport_source_precision_threshold_m":.005,
        "original_source_rig_rights":"original_synthetic",
        "rest_frame_attachment_and_tangent_calibrated":False,
        "source_body_root_anatomy_accepted":False,
        "material_visual_accepted":False,"scientific_hold":"KEEP","release_or_CPE_admission":False}
def main():
    from pathlib import Path
    import sys
    if len(sys.argv)!=5:raise SystemExit("usage: pony_skin_frame_quality.py source_capsule.json source_bone.json rigid_52_animation.json out.json")
    c,b,a=[json.loads(Path(f).read_text()) for f in sys.argv[1:4]]
    r=assess(c,b,a)
    p=Path(sys.argv[4])
    if p.exists():raise ValueError("will not overwrite first-frame evidence")
    p.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print("SOURCE_BONE_VS_52_RIGID_FRAME_ORACLE",json.dumps(r,sort_keys=True))
if __name__=="__main__":main()
