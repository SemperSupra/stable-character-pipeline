#!/usr/bin/env python3
"""Forensic four remaining FAILED seven-fix rights-original source trajectories.

No generator, source oracle, labels, model/video, contact flag, or original
negative control is modified. Delivers deterministic per-frame actionable
research evidence for independent actor work without prescribing fake repairs.
"""
import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"expanded_motion_corpus"))
sys.path.insert(0,str(ROOT/"video_ik_science"))
import motion_math
from audit_3d_feasibility import solve_3d

ADMITTED={
 "male_jump_slippers":"locomotion",
 "female_jumping_jacks_sandals":"exercise_pose",
 "female_cartwheel_barefoot":"exercise_pose",
 "male_diving_barefoot":"aquatic",
}
LIMBS={"male":(.54,.53),"female":(.52,.51)}
ISSUE_CODES={"LIMB_LENGTH_INVARIANT_VIOLATION","LABELED_STANCE_FOOT_SLIDE"}

def audit(root,case):
    if case not in ADMITTED:
        raise ValueError("UNADMITTED_CASE")
    batch=ADMITTED[case]
    folder=(Path(root).resolve(strict=True)/batch).resolve(strict=True)
    if not folder.is_relative_to(Path(root).resolve(strict=True)):
        raise ValueError("SOURCE_PATH_ESCAPE")
    manifest=json.loads((folder/"manifest.json").read_text())
    if manifest.get("schema")!="scp.expanded-original-3d-motion-corpus.v1" or manifest.get("rights")!="CC0-1.0 for original generated files" or manifest.get("batch")!=batch:
        raise ValueError("UNVERIFIED_SOURCE_MANIFEST")
    matching=[c for c in manifest.get("cases",[]) if c.get("case")==case]
    if len(matching)!=1:
        raise ValueError("SOURCE_CASE_NOT_UNIQUE")
    item=matching[0]
    label=folder/(case+"_ground_truth.json")
    raw=label.read_bytes()
    if item["ground_truth"]["file"]!=label.name or hashlib.sha256(raw).hexdigest()!=item["ground_truth"]["sha256"]:
        raise ValueError("SOURCE_LABEL_SHA_MISMATCH")
    if item["model"]["file"]!=case+".glb":
        raise ValueError("SOURCE_GLB_CASE_MISMATCH")
    model=folder/(case+".glb")
    if hashlib.sha256(model.read_bytes()).hexdigest()!=item["model"]["sha256"] or model.read_bytes()[:4]!=b"glTF":
        raise ValueError("SOURCE_GLTF_SHA_MISMATCH")
    if len(item["videos"])!=1 or item["videos"][0]["file"]!=case+"_side.mp4":
        raise ValueError("H264_CASE_MISMATCH")
    video=folder/(case+"_side.mp4")
    if hashlib.sha256(video.read_bytes()).hexdigest()!=item["videos"][0]["sha256"]:
        raise ValueError("H264_SHA_MISMATCH")
    source=json.loads(raw)
    if source.get("case")!=case or source.get("fps")!=20 or len(source.get("frames",[]))!=40:
        raise ValueError("CLOCK_OR_CASE_INVALID")
    sex=source["spec"]["sex"]
    if sex not in LIMBS:raise ValueError("INVALID_MORPHOLOGY")
    original=motion_math.audit_case(label,LIMBS)
    if original["status"]!="FAIL" or original["defect_count"]<1 or any(f["code"] not in ISSUE_CODES for f in original["findings"]):
        raise ValueError("SOURCE_NOT_ORIGINAL_TARGET_FAILURE")
    thigh,shin=LIMBS[sex]
    frame_windows=[]
    stat=Counter()
    for i,frame in enumerate(source["frames"]):
        joints=frame["joints"]
        hits=[x for x in original["findings"] if x["frame"]==i]
        by_side={}
        for side in ("left","right"):
            solution=solve_3d(joints[side+"_hip"],joints[side+"_ankle"],thigh,shin,joints[side+"_knee"])
            reach=solution["status"]
            stat["IK_"+reach]+=1
            ankle=joints[side+"_ankle"]
            if not all(type(v) in (float,int) and math.isfinite(v) for v in ankle):
                raise ValueError("INVALID_SOURCE_ANKLE")
            contact=frame["contact"][side]
            if type(contact) is not bool:
                raise ValueError("UNTRUSTWORTHY_CONTACT_FLAG")
            speed=None
            if i and contact and source["frames"][i-1]["contact"][side]:
                prior=source["frames"][i-1]["joints"][side+"_ankle"]
                speed=math.dist(prior,ankle)*20.
                if speed>.025:stat["SPEED_OVER_ORACLE"]+=1
            if reach=="UNREACHABLE":stat["SOURCE_GEOMETRY_REQUIRES_HIP_OR_ANKLE_CHANGE"]+=1
            by_side[side]={
                "contact":contact,
                "ankle_xyz_m":[round(v,7) for v in ankle],
                "ankle_z_m":round(ankle[2],7),
                "stance_speed_m_s":None if speed is None else round(speed,7),
                "three_d_ik_status":reach,
                "hip_ankle_distance_m":solution.get("hip_ankle_distance_m"),
                "three_d_original_bone_error_m":solution.get("original_knee_bone_error_m",solution.get("old_max_bone_error_m")),
            }
        frame_windows.append({
            "frame":i,"time_s":i/20,
            "has_source_findings":bool(hits),
            "source_finding_codes":sorted(set(h["code"] for h in hits)),
            "legs":by_side,
        })
        for x in hits:stat[x["code"]]+=1
    if stat["LIMB_LENGTH_INVARIANT_VIOLATION"]+stat["LABELED_STANCE_FOOT_SLIDE"]!=original["defect_count"]:
        raise ValueError("SOURCE_ORACLE_DEFECT_COUNTS_DIVERGED")
    groups=[];active=None
    for row in frame_windows:
        if row["has_source_findings"]:
            if active is None:active=[row["frame"],row["frame"]]
            else:active[1]=row["frame"]
        elif active:
            groups.append({"first_frame":active[0],"last_frame":active[1]})
            active=None
    if active:groups.append({"first_frame":active[0],"last_frame":active[1]})
    return {
       "schema":"scp.original-seven-fix-residual-source-triage.v1",
       "source_run_id":43160358584,
       "case":case,"batch":batch,"source_sha256":original["source_sha256"],
       "source_model_sha256":item["model"]["sha256"],
       "source_video_sha256":item["videos"][0]["sha256"],
       "source_morphology_preset":sex,
       "original_oracle_status":original["status"],
       "original_oracle_defect_count":original["defect_count"],
       "findings":original["findings"],
       "counts":dict(stat),
       "consecutive_defect_frame_windows":groups,
       "frames":frame_windows,
       "science":"DIAGNOSTICS_ONLY_NO_SOURCE_CHANGES_OR_CORRECTIVE_PROMOTION",
       "limits":[
          "Original oracle and seven-fix source/GLB/H264 remain byte-identical and untouched",
          "Reachability is mathematical two-link geometry, not human ankle/hip/torque admissibility",
          "Stance labels originate in source, not independent floor pressure/contact sensors",
          "Do not fix an unreachable leg by changing labels, hiding output, or clamping the knee",
          "No image-pixel naturalism, human anatomy, biomechanics or identity acceptance",
       ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--case",required=True,choices=ADMITTED)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    result=audit(a.root,a.case)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("INDEPENDENT_RESIDUAL_FOUR_SOURCE_TRIAGE",a.case,result["original_oracle_defect_count"],result["counts"])

if __name__=="__main__":
    main()
