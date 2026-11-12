#!/usr/bin/env python3
"""Compose one independently qualified jumping-jacks correction into eight-fix.

The local Mac actor's slipper-jump work remains strictly read-only/byte-identical.
Every other eight-fix source/model/video is SHA-verified and carried over unchanged.
Do not recalculate or rerender other negative controls or research cases.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"expanded_motion_corpus"))
import motion_math

CASE = "female_jumping_jacks_sandals"
FAMILY = "exercise_pose"
FAMILIES = {"locomotion":8,"exercise_pose":7,"dance_combat":5,"aquatic":2}
MEDIA_KEYS = ("model","ground_truth","videos")

def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verified_manifest(folder: Path,batch: str,expected_cases: int):
    data=json.loads((folder/"manifest.json").read_text())
    if (data.get("schema")!="scp.expanded-original-3d-motion-corpus.v1"
        or data.get("batch")!=batch
        or data.get("rights")!="CC0-1.0 for original generated files"
        or data.get("fps")!=20 or data.get("frames")!=40):
        raise ValueError("WRONG_SOURCE_MANIFEST_RIGHTS_OR_CLOCK")
    cases=data.get("cases",[])
    if not isinstance(cases,list) or len(cases)!=expected_cases:
        raise ValueError("WRONG_SOURCE_FAMILY_CASE_SET")
    names=[c.get("case") for c in cases]
    if len(set(names))!=len(names):
        raise ValueError("DUPLICATE_FAMILY_SOURCE_CASE")
    for c in cases:
        name=c["case"]
        if not isinstance(name,str) or any(z not in "abcdefghijklmnopqrstuvwxyz0123456789_" for z in name):
            raise ValueError("MALFORMED_SOURCE_CASE_NAME")
        if len(c.get("videos",[]))!=1:
            raise ValueError("UNTRUSTWORTHY_ORIGINAL_VIDEO_COUNT")
        for obj,suffix in ((c["model"],".glb"),(c["ground_truth"],"_ground_truth.json"),(c["videos"][0],"_side.mp4")):
            fn=name+suffix
            if obj.get("file")!=fn or sha_file(folder/fn)!=obj.get("sha256"):
                raise ValueError("MANIFEST_SOURCE_MEDIA_SHA_MISMATCH:"+fn)
    return data

def compose(eight_root: Path,jacks_root: Path,out_root: Path):
    eight_root,jacks_root,out_root=map(Path,(eight_root,jacks_root,out_root))
    replacement=verified_manifest(jacks_root/FAMILY,FAMILY,1)
    if replacement["cases"][0]["case"]!=CASE:
        raise ValueError("NOT_APPROVED_JUMPING_JACKS_REPLACEMENT")
    newitem=replacement["cases"][0]
    research=json.loads((jacks_root/FAMILY/"jacks-ab-receipt.json").read_text())
    if (research.get("schema")!="scp.visualqa.jacks-grounded-flight-ab.v1"
        or research.get("case")!=CASE
        or research["original_audit"]["status"]!="FAIL"
        or research["original_audit"]["defect_count"]!=78
        or research["candidate_audit"]["status"]!="PASS"
        or research["candidate_audit"]["defect_count"]!=0
        or research.get("verdict")!="TARGETED_SOURCE_KINEMATIC_CANDIDATE_ONLY"):
        raise ValueError("JACKS_RESEARCH_GATE_OR_ORIGINAL_NEGATIVE_CONTROL_NOT_MET")
    old_records=[]
    changed=[]
    for batch,case_count in FAMILIES.items():
        old_dir=eight_root/batch
        old=verified_manifest(old_dir,batch,case_count)
        newdir=out_root/batch
        newdir.mkdir(parents=True,exist_ok=True)
        newcases=[]
        for item in old["cases"]:
            cid=item["case"]
            source=jacks_root/FAMILY if cid==CASE else old_dir
            new=newitem if cid==CASE else item
            if cid==CASE:
                if batch!=FAMILY:
                    raise ValueError("WRONG_JACKS_FAMILY")
                for key,field in (("labels","ground_truth"),("glb","model"),("h264","videos")):
                    lhs=item[field][0]["sha256"] if field=="videos" else item[field]["sha256"]
                    rhs=new[field][0]["sha256"] if field=="videos" else new[field]["sha256"]
                    if lhs!=research["original_case_sha"][key] or rhs!=research["candidate_case_sha"][key] or lhs==rhs:
                        raise ValueError("JACKS_A_B_ORIGINAL_CUSTODY_MISMATCH")
                changed.append(cid)
            for obj in (new["model"],new["ground_truth"],new["videos"][0]):
                filename=obj["file"]
                if not (source/filename).is_file() or sha_file(source/filename)!=obj["sha256"]:
                    raise ValueError("SOURCE_MEDIA_NOT_VERIFIED:"+filename)
                shutil.copyfile(source/filename,newdir/filename)
                if sha_file(newdir/filename)!=obj["sha256"]:
                    raise ValueError("DESTINATION_MEDIA_SHA_MISMATCH")
            for suffix in (".glb","_ground_truth.json","_side.mp4"):
                key=(["model","ground_truth","videos"])[[".glb","_ground_truth.json","_side.mp4"].index(suffix)]
                before=item[key][0]["sha256"] if key=="videos" else item[key]["sha256"]
                after=new[key][0]["sha256"] if key=="videos" else new[key]["sha256"]
                if cid!=CASE and before!=after:
                    raise ValueError("NONTARGET_HASH_DRIFT")
            old_records.append({"case":cid,"changed":cid==CASE,"original_labels_sha256":item["ground_truth"]["sha256"],
                                "candidate_labels_sha256":new["ground_truth"]["sha256"],
                                "original_glb_sha256":item["model"]["sha256"],
                                "candidate_glb_sha256":new["model"]["sha256"],
                                "original_h264_sha256":item["videos"][0]["sha256"],
                                "candidate_h264_sha256":new["videos"][0]["sha256"]})
            newcases.append(new)
        outmanifest=dict(old)
        outmanifest["cases"]=newcases
        outmanifest["notes"]=list(old.get("notes",[]))+[
          "Nine-fix candidate composes exact SHA-verified eight-fix rights-original 22-case corpus",
          "Only female_jumping_jacks_sandals replaced with separately validated stance/flight source+GLB+H264",
          "Unmodified 21 other cases (including local actor male_jump_slippers) are carried byte-identically",
          "Contact semantics changed only because motion is physically regenerated; original controls never rewritten",
          "No contact impulse/mass balance/biomechanical realism acceptance; no stale preview contact sheet"]
        (newdir/"manifest.json").write_text(json.dumps(outmanifest,sort_keys=True,indent=2)+"\n")
    if changed!=[CASE] or len(old_records)!=22 or len([x for x in old_records if x["changed"]])!=1:
        raise ValueError("WRONG_TARGET_COUNT")
    audit=motion_math.audit_corpus(out_root)
    if audit["counts"]!={"PASS":19,"FAIL":2,"UNKNOWN":1}:
        raise ValueError("FULL_22_SOURCE_GATE_NOT_QUALIFIED:"+str(audit["counts"]))
    residual={x["case"] for x in audit["cases"] if x["status"]=="FAIL"}
    if residual!={"male_jump_slippers","female_cartwheel_barefoot"}:
        raise ValueError("UNEXPECTED_REMAINING_SOURCE_FAILURES:"+str(residual))
    if {x["case"] for x in audit["cases"] if x["status"]=="UNKNOWN"}!={"female_swimming_barefoot"}:
        raise ValueError("SWIMMING_ABSTENTION_NOT_PRESERVED")
    report={"schema":"scp.visualqa.original-22-nine-fix-join.v1","case_count":22,
            "admitted_source_replacements":changed,"unchanged_case_count":21,
            "source_counts":{"PASS":19,"FAIL":2,"UNKNOWN":1},
            "cases":old_records,
            "original_jacks_fail_78_preserved_in_external_research":True,
            "limits":["Targeted source contact and limb geometry only; no human realism acceptance",
                      "Original all-contact negative control external artifact is untouched",
                      "Mac actor slipper-jump remains SHA-identical source, GLB and H264 to prior eight-fix",
                      "Cartwheel is unchanged and source FAIL; swimming remains UNKNOWN",
                      "This composition does not render stale contact sheets or mutate prior cases"]}
    (out_root/"ninefix-receipt.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    (out_root/"source-math.json").write_text(json.dumps(audit,sort_keys=True,indent=2)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--eight-root",required=True)
    p.add_argument("--jacks-root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    r=compose(Path(a.eight_root),Path(a.jacks_root),Path(a.out))
    print("NINE_FIX_SOURCE_INTEGRATION",r["source_counts"],r["admitted_source_replacements"],r["unchanged_case_count"])

if __name__=="__main__":
    main()
