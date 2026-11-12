#!/usr/bin/env python3
"""Independent finite-difference temporal 3-D witness for the original 8-fix corpus.

No motion re-generation, no evaluator/ground-truth changes, no physically
calibrated thresholds: velocity, acceleration and jerk are measured from the
actual 40-frame source joint tracks and reported as diagnostic quantities.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

FAMILIES = {"locomotion":8,"exercise_pose":7,"dance_combat":5,"aquatic":2}
CASE_SCHEMA = "scp.expanded-original-3d-motion-labels.v1"
MANIFEST_SCHEMA = "scp.expanded-original-3d-motion-corpus.v1"
OUTPUT_SCHEMA = "scp.visualqa.original-8fix-source-temporal-witness.v1"
FPS = 20
FRAMES = 40

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def difference_peak(points: list[list[float]], fps: int = FPS) -> dict:
    """First/second/third ordered 3D differences and their temporal witnesses."""
    if not isinstance(points,list) or len(points)<4 or fps<=0:
        raise ValueError("MISSING_TEMPORAL_OBSERVATIONS")
    if any(len(p)!=3 or any(type(x) not in (int,float) or not math.isfinite(x) for x in p) for p in points):
        raise ValueError("NONFINITE_OR_MALFORMED_JOINT")
    stages=[points]
    result={}
    for order,name in ((1,"speed_m_s"),(2,"accel_m_s2"),(3,"jerk_m_s3")):
        prior=stages[-1]
        current=[[fps*(now[k]-before[k]) for k in range(3)]
                 for before,now in zip(prior,prior[1:])]
        stages.append(current)
        norms=[math.dist(v,(0.,0.,0.)) for v in current]
        idx=max(range(len(norms)),key=lambda i:norms[i])
        result[name]={"peak":round(norms[idx],8),"at_frame":idx+order,
                      "rms":round(math.sqrt(sum(x*x for x in norms)/len(norms)),8)}
    return result

def inspect_case(folder: Path, item: dict):
    name=item.get("case")
    if not isinstance(name,str) or not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in name):
        raise ValueError("UNTRUSTWORTHY_CASE")
    expected={"model":name+".glb","ground_truth":name+"_ground_truth.json",
              "videos":name+"_side.mp4"}
    assets=[(item["model"],expected["model"]),(item["ground_truth"],expected["ground_truth"])]
    vids=item["videos"]
    if len(vids)!=1:
        raise ValueError("UNEXPECTED_VIDEO_COUNT")
    assets.append((vids[0],expected["videos"]))
    for meta,filename in assets:
        if meta.get("file")!=filename or _sha(folder/filename)!=meta.get("sha256"):
            raise ValueError("CANDIDATE_ASSET_SHA_OR_PATH_MISMATCH")
    doc=json.loads((folder/expected["ground_truth"]).read_text())
    frames=doc.get("frames")
    if (doc.get("schema")!=CASE_SCHEMA or doc.get("case")!=name or doc.get("fps")!=FPS
        or not isinstance(frames,list) or len(frames)!=FRAMES):
        raise ValueError("SOURCE_FRAME_CLOCK_OR_SCHEMA_INVALID")
    joint_keys=None
    per_joint={}
    contacts={side:[] for side in ("left","right")}
    for i,fr in enumerate(frames):
        if fr.get("frame")!=i or abs(fr.get("time_s",-1)-i/FPS)>1e-6:
            raise ValueError("UNTRUSTWORTHY_FRAME_INDEX_OR_TIME")
        joints=fr.get("joints")
        if not isinstance(joints,dict) or not joints:
            raise ValueError("NO_SOURCE_JOINTS")
        if joint_keys is None:
            joint_keys=set(joints)
            if len(joint_keys)>256:
                raise ValueError("UNBOUNDED_JOINT_SET")
        if set(joints)!=joint_keys:
            raise ValueError("JOINT_KEYS_CHANGED_BETWEEN_FRAMES")
        for joint,coords in joints.items():
            per_joint.setdefault(joint,[]).append(coords)
        for side in contacts:
            state=fr["contact"].get(side)
            if type(state) is not bool:
                raise ValueError("INVALID_GROUND_CONTACT")
            contacts[side].append(state)
    peaks = {joint:difference_peak(track,FPS) for joint,track in per_joint.items()}
    extrema={}
    for unit in ("speed_m_s","accel_m_s2","jerk_m_s3"):
        j=max(peaks,key=lambda k:peaks[k][unit]["peak"])
        extrema[unit]={"joint":j, **peaks[j][unit]}
    contact_changes={side:[i for i in range(1,FRAMES)
                       if contacts[side][i]!=contacts[side][i-1]]
                     for side in contacts}
    return {
        "case":name,
        "source_joint_labels_sha256":item["ground_truth"]["sha256"],
        "source_glb_sha256":item["model"]["sha256"],
        "source_h264_sha256":vids[0]["sha256"],
        "fps":FPS,"frames":FRAMES,
        "joint_count":len(joint_keys),
        "world_3d_extrema":extrema,
        "ground_contact_transition_frame_indices":contact_changes,
        "status":"NUMERICAL_WITNESS_ONLY",
    }

def inspect_batch(root: Path,batch: str):
    if batch not in FAMILIES:
        raise ValueError("UNADMITTED_ORIGINAL_FAMILY")
    folder=Path(root)/batch
    manifest=json.loads((folder/"manifest.json").read_text())
    if (manifest.get("schema")!=MANIFEST_SCHEMA or manifest.get("batch")!=batch
        or manifest.get("rights")!="CC0-1.0 for original generated files"
        or manifest.get("fps")!=FPS or manifest.get("frames")!=FRAMES):
        raise ValueError("CANDIDATE_MANIFEST_NOT_AUTHENTIC")
    items=manifest.get("cases")
    if not isinstance(items,list) or len(items)!=FAMILIES[batch]:
        raise ValueError("CASE_FAMILY_INCOMPLETE")
    cases=[inspect_case(folder,item) for item in items]
    if len({x["case"] for x in cases})!=len(cases):
        raise ValueError("DUPLICATE_CASE")
    return {
        "schema":OUTPUT_SCHEMA,"family":batch,"case_count":len(cases),
        "manifest_sha256":_sha(folder/"manifest.json"),
        "cases":cases,
        "research_disposition":"HOLD_UNCALIBRATED_TEMPORAL_OBSERVATION",
        "limitations":["Source-kinematics-only finite differences; no image-derived pose, force or inertia",
                       "High jerk is a diagnostic ranking, not a physical threshold or FAIL",
                       "No production, real-human motion, skin, identity or injury-safety acceptance"],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--family",required=True,choices=FAMILIES)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    result=inspect_batch(Path(a.root),a.family)
    out=Path(a.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("ACTUAL_8FIX_TEMPORAL_SOURCE_WITNESS",a.family,len(result["cases"]),
          [(x["case"],x["world_3d_extrema"]["jerk_m_s3"]["peak"]) for x in result["cases"]])

if __name__=="__main__":
    main()
