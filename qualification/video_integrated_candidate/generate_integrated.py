#!/usr/bin/env python3
"""Integrate four independently measured original source repairs into a 22-case candidate.

Every original synthetic baseline file is read-only and SHA-verified against its
manifest. No original negative-control file is edited or relabelled. No result
implies real-world motion dynamics, anatomical realism or professional dance.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

THIS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(THIS/"video_motion_repair"))
sys.path.insert(0,str(THIS/"video_dance_repair"))
from planted_stance_ab import gen, patched_stand, patched_judo, audit, LIMBS
from dance_ab import candidate_dance

TARGETS=frozenset({
    "male_stand_barefoot","female_judo_kata_barefoot",
    "female_dance_high_heels","male_dance_boots",
})
COUNTS={"locomotion":8,"exercise_pose":7,"dance_combat":5,"aquatic":2}
ORIGINAL_FUNCTIONS=(gen.stand_motion,gen.judo_motion,gen.dance_motion)

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check_batch(batch,root,original_root):
    if batch not in COUNTS:
        raise ValueError("UNKNOWN_BATCH")
    root,original_root=Path(root),Path(original_root)
    original_dir=original_root/batch
    old_manifest=json.loads((original_dir/"manifest.json").read_text())
    if old_manifest.get("schema")!="scp.expanded-original-3d-motion-corpus.v1" or old_manifest.get("rights")!="CC0-1.0 for original generated files":
        raise ValueError("INVALID_ORIGINAL_RIGHTS_OR_SCHEMA")
    prior={item["case"]:item for item in old_manifest["cases"]}
    if len(prior)!=COUNTS[batch]:
        raise ValueError("ORIGINAL_BATCH_COUNT")
    candidate_dir=root/batch
    try:
        gen.stand_motion,gen.judo_motion,gen.dance_motion=patched_stand,patched_judo,candidate_dance
        new_manifest=gen.build_batch(batch,candidate_dir)
    finally:
        gen.stand_motion,gen.judo_motion,gen.dance_motion=ORIGINAL_FUNCTIONS
    if len(new_manifest["cases"])!=COUNTS[batch] or new_manifest["rights"]!="CC0-1.0 for original generated files":
        raise ValueError("CANDIDATE_COUNT_OR_RIGHTS_CHANGED")
    records=[]
    for item in new_manifest["cases"]:
        name=item["case"]
        if name not in prior:
            raise ValueError("NEW_UNAPPROVED_CASE")
        old=prior[name]
        o_label=original_dir/(name+"_ground_truth.json")
        n_label=candidate_dir/(name+"_ground_truth.json")
        o_video=original_dir/(name+"_side.mp4")
        n_video=candidate_dir/(name+"_side.mp4")
        o_glb=original_dir/(name+".glb")
        n_glb=candidate_dir/(name+".glb")
        for path,sha in ((o_label,old["ground_truth"]["sha256"]),
                         (o_video,old["videos"][0]["sha256"]),
                         (o_glb,old["model"]["sha256"]),
                         (n_label,item["ground_truth"]["sha256"]),
                         (n_video,item["videos"][0]["sha256"]),
                         (n_glb,item["model"]["sha256"])):
            if digest(path)!=sha:
                raise ValueError("SOURCE_OR_MODEL_MEDIA_SHA_MISMATCH")
        original=audit.audit_case(o_label,LIMBS)
        candidate=audit.audit_case(n_label,LIMBS)
        updated=(original["source_sha256"]!=candidate["source_sha256"])
        if name in TARGETS:
            if not updated or original["status"]!="FAIL" or candidate["status"]!="PASS":
                raise ValueError("EXPECTED_SOURCE_REPAIR_NOT_REALIZED")
            if old["model"]["sha256"]==item["model"]["sha256"] or old["videos"][0]["sha256"]==item["videos"][0]["sha256"]:
                raise ValueError("REPAIRED_VIDEO_OR_MESH_NOT_CHANGED")
            old_frames=json.loads(o_label.read_text())["frames"]
            new_frames=json.loads(n_label.read_text())["frames"]
            if [v["contact"] for v in old_frames]!=[v["contact"] for v in new_frames]:
                raise ValueError("RELABELLED_CONTACT_PROHIBITED")
        else:
            if updated or old["model"]["sha256"]!=item["model"]["sha256"]:
                raise ValueError("NON_TARGET_GEOMETRY_REGRESSION")
            if original["status"]!=candidate["status"] or original["defect_count"]!=candidate["defect_count"]:
                raise ValueError("NON_TARGET_AUDIT_REGRESSION")
        records.append({
            "case":name,"repair_target":name in TARGETS,
            "original_status":original["status"],"candidate_status":candidate["status"],
            "original_defects":original["defect_count"],"candidate_defects":candidate["defect_count"],
            "original_joint_labels_sha256":original["source_sha256"],
            "candidate_joint_labels_sha256":candidate["source_sha256"],
            "original_h264_sha256":old["videos"][0]["sha256"],
            "candidate_h264_sha256":item["videos"][0]["sha256"],
            "original_glb_sha256":old["model"]["sha256"],
            "candidate_glb_sha256":item["model"]["sha256"],
            "contact_labels_modified":False,
        })
    if len(records)!=COUNTS[batch]:
        raise ValueError("CASE_COUNT_CHANGED")
    result={"schema":"scp.integrated-original-22-4fix-candidate-batch.v1",
            "batch":batch,"case_count":len(records),
            "cases":records,"improved_cases":[r["case"] for r in records if r["repair_target"]],
            "original_counts":dict(Counter(r["original_status"] for r in records)),
            "candidate_counts":dict(Counter(r["candidate_status"] for r in records)),
            "scientific_status":"TARGETED_KINEMATIC_CONTACT_ONLY_NO_PRODUCT_ACCEPTANCE"}
    (candidate_dir/"integration-receipt.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--batch",required=True,choices=COUNTS.keys())
    p.add_argument("--root",required=True)
    p.add_argument("--original-root",required=True)
    a=p.parse_args()
    r=check_batch(a.batch,a.root,a.original_root)
    print("INTEGRATED_ORIGINAL_SOURCE_CANDIDATE",a.batch,r["case_count"],r["improved_cases"],
          r["original_counts"],r["candidate_counts"])

if __name__=="__main__":
    main()
