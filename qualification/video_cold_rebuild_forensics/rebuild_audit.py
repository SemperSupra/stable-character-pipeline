#!/usr/bin/env python3
"""Diagnose bit-level source corpus cold-build drift without admitting changes.

Run the exact released original procedural generator against immutable hashed
original 22-case assets. Compare source joints, animation GLB and H264 at
individual case granularity. Never weaken production exact-hash custody;
the output is a research diagnostic explaining why it failed, not a repair.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"expanded_motion_corpus"))
import build_motion_batches as gen

BATCHES=("exercise_pose","dance_combat")
COUNTS={"exercise_pose":7,"dance_combat":5}

def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def audit(batch,original,output):
    if batch not in BATCHES:
        raise ValueError("UNKNOWN_ORIGINAL_BATCH")
    origin=Path(original)/batch
    manifest=json.loads((origin/"manifest.json").read_text())
    if manifest.get("schema")!="scp.expanded-original-3d-motion-corpus.v1" or manifest.get("rights")!="CC0-1.0 for original generated files":
        raise ValueError("UNVERIFIED_ORIGINAL_RIGHTS")
    names=[x["case"] for x in manifest["cases"]]
    if names!=gen.BATCHES[batch] or len(names)!=COUNTS[batch]:
        raise ValueError("ORIGINAL_CASE_SCOPE_MISMATCH")
    dest=Path(output)/batch
    dest.mkdir(parents=True,exist_ok=True)
    generated=gen.build_batch(batch,dest)
    if [x["case"] for x in generated["cases"]]!=names:
        raise ValueError("CASE_ORDER_CHANGED")
    cases=[]
    for before,after in zip(manifest["cases"],generated["cases"]):
        name=before["case"]
        files=(("model",".glb"),("ground_truth","_ground_truth.json"),("videos","_side.mp4"))
        provenance={}
        for group,suffix in files:
            original_file=origin/(name+suffix)
            new_file=dest/(name+suffix)
            prior=before[group][0] if group=="videos" else before[group]
            curr=after[group][0] if group=="videos" else after[group]
            if original_file.name!=prior["file"] or new_file.name!=curr["file"]:
                raise ValueError("SOURCE_FILE_NAME_DRIFT")
            actual=hash_file(original_file)
            new_actual=hash_file(new_file)
            if actual!=prior["sha256"] or new_actual!=curr["sha256"]:
                raise ValueError("INVALID_SOURCE_OR_CURRENT_MANIFEST_SHA")
            provenance[group]={"original":actual,"cold_build":new_actual,"byte_identical":actual==new_actual}
        old=json.loads((origin/(name+"_ground_truth.json")).read_text())
        new=json.loads((dest/(name+"_ground_truth.json")).read_text())
        if old["case"]!=new["case"] or old["spec"]!=new["spec"] or len(old["frames"])!=len(new["frames"]) or len(old["frames"])!=40:
            raise ValueError("SOURCE_METADATA_OR_FRAME_REGRESSION")
        max_delta=0.
        changed_components=0
        labels_equal=True
        contacts_equal=True
        for a,b in zip(old["frames"],new["frames"]):
            if a["contact"]!=b["contact"]:
                contacts_equal=False
            if a["joints"].keys()!=b["joints"].keys():
                raise ValueError("JOINT_SCHEMA_DRIFT")
            for k in a["joints"]:
                if len(a["joints"][k])!=3 or len(b["joints"][k])!=3:
                    raise ValueError("BAD_SOURCE_JOINT_VECTOR")
                for x,y in zip(a["joints"][k],b["joints"][k]):
                    if not (math.isfinite(x) and math.isfinite(y)):
                        raise ValueError("NONFINITE_REBUILD")
                    delta=abs(x-y)
                    if delta:
                        changed_components+=1
                        max_delta=max(max_delta,delta)
            if a!=b:
                labels_equal=False
        if not contacts_equal:
            raise ValueError("ORIGINAL_CONTACT_SEMANTICS_CHANGED")
        stripped_old=dict(old);stripped_new=dict(new)
        stripped_old.pop("gltf_sha256",None);stripped_new.pop("gltf_sha256",None)
        case={
            "case":name,
            "sha":provenance,
            "full_frame_semantics_identical":labels_equal,
            "labels_equal_without_embedded_glb_sha":stripped_old==stripped_new,
            "changed_numeric_joint_components":changed_components,
            "maximum_joint_coordinate_abs_difference_m":max_delta,
            "contact_labels_identical":contacts_equal,
            "substantive_joint_drift_over_1e6":max_delta>1e-6,
        }
        cases.append(case)
    return {"schema":"scp.original-cold-build-drift-forensic.v1",
            "batch":batch,"original_artifact_source_run":43137642662,
            "case_count":len(cases),"cases":cases,
            "counts":{
                "glb_bit_identical":sum(c["sha"]["model"]["byte_identical"] for c in cases),
                "label_bit_identical":sum(c["sha"]["ground_truth"]["byte_identical"] for c in cases),
                "h264_bit_identical":sum(c["sha"]["videos"]["byte_identical"] for c in cases),
                "unchanged_semantic_joint_fields":sum(c["full_frame_semantics_identical"] for c in cases),
                "source_coordinate_drift_gt_1e6":sum(c["substantive_joint_drift_over_1e6"] for c in cases)},
            "status":"FORENSIC_NONREPRODUCIBILITY_REPORT_NOT_SOURCE_PROMOTION",
            "limitations":["No input source labels or original media overwritten",
              "A small numerical difference is not a license to substitute a new artifact for an approved source SHA",
              "Separating GLB hash embedding from source kinematic semantics is not full animation or visual equivalence",
              "No anatomy, biomechanics, force or realism acceptance"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--batch",required=True,choices=BATCHES)
    p.add_argument("--original",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    r=audit(a.batch,a.original,a.out)
    path=Path(a.out)/a.batch/"cold-build-forensics.json"
    path.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    print("TRUE_SOURCE_COLD_REBUILD_FORENSICS",a.batch,r["counts"])

if __name__=="__main__":
    main()
