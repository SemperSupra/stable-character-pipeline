#!/usr/bin/env python3
"""Independent three-dimensional two-link knee feasibility on 22 original 3D cases.

Reads immutable, rights-original source labels. The existing generator's planar
knee solver uses x/z projection and can make truly 3D bones artificially long
when hip/ankle y-coordinates differ. This audit DOES NOT repair labels,
overwrite the source, claim balance/forces, or qualify realistic humans.
Python standard library only.
"""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

BATCH_COUNTS = {"locomotion": 8, "exercise_pose": 7, "dance_combat": 5, "aquatic": 2}
LIMBS = {"male": (0.54, 0.53), "female": (0.52, 0.51)}
EPS = 1e-9
DEFECT_TOL_M = .01

def finite_vector(vector):
    if not isinstance(vector, list) or len(vector) != 3:
        raise ValueError("INVALID_JOINT_DIMENSION")
    if any(type(v) not in (float, int) or not math.isfinite(v) for v in vector):
        raise ValueError("NONFINITE_JOINT")
    return tuple(float(v) for v in vector)

def norm(vector):
    return math.sqrt(sum(v * v for v in vector))

def unit(vector):
    magnitude = norm(vector)
    if magnitude < EPS:
        raise ValueError("DEGENERATE_DIRECTION")
    return tuple(v / magnitude for v in vector)

def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def solve_3d(hip, ankle, thigh, shin, source_knee):
    h = finite_vector(hip)
    a = finite_vector(ankle)
    existing = finite_vector(source_knee)
    if type(thigh) not in (float, int) or type(shin) not in (float, int):
        raise ValueError("INVALID_LIMB_PARAMETER")
    if not (math.isfinite(thigh) and math.isfinite(shin) and thigh > 0 and shin > 0):
        raise ValueError("INVALID_LIMB_PARAMETER")
    displacement = tuple(y-x for x,y in zip(h,a))
    d = norm(displacement)
    if not (abs(thigh-shin) + EPS < d < thigh+shin-EPS):
        return {"status":"UNREACHABLE", "hip_ankle_distance_m":round(d,7),
                "old_max_bone_error_m":round(max(abs(norm(tuple(x-y for x,y in zip(h,existing)))-thigh),
                    abs(norm(tuple(x-y for x,y in zip(existing,a)))-shin)),7)}
    along = (thigh**2-shin**2+d*d)/(2*d)
    radial_squared = thigh**2-along**2
    if radial_squared < -EPS:
        raise ValueError("NUMERIC_TWO_LINK_FAILURE")
    radial = math.sqrt(max(0.,radial_squared))
    axis = unit(displacement)
    reference = (0.,1.,0.) if abs(axis[1]) < .95 else (1.,0.,0.)
    pole = unit(cross(axis,reference))
    mid = tuple(h[i]+axis[i]*along for i in range(3))
    choices=[tuple(mid[i]+sign*radial*pole[i] for i in range(3)) for sign in (-1,1)]
    knee=min(choices,key=lambda k: norm(tuple(k[i]-existing[i] for i in range(3))))
    error=max(abs(norm(tuple(knee[i]-h[i] for i in range(3)))-thigh),
              abs(norm(tuple(knee[i]-a[i] for i in range(3)))-shin))
    if error>1e-7:
        raise ValueError("CANDIDATE_BONE_LENGTH_INVARIANT")
    original_error=max(abs(norm(tuple(existing[i]-h[i] for i in range(3)))-thigh),
                       abs(norm(tuple(existing[i]-a[i] for i in range(3)))-shin))
    return {"status":"FEASIBLE", "hip_ankle_distance_m":round(d,7),
            "original_knee_bone_error_m":round(original_error,7),
            "candidate_knee_bone_error_m":round(error,7),
            "original_knee_displacement_m":round(norm(tuple(knee[i]-existing[i] for i in range(3))),7),
            "original_bad_bone":original_error>DEFECT_TOL_M,
            "off_plane_endpoint_displacement_m":round(abs(h[1]-a[1]),7),
            "candidate_knee_xyz":[round(v,9) for v in knee]}

def audit_batch(root, batch):
    if batch not in BATCH_COUNTS:
        raise ValueError("UNKNOWN_BATCH")
    root = Path(root).resolve(strict=True)
    folder = (root/batch).resolve(strict=True)
    if not folder.is_relative_to(root):
        raise ValueError("CASE_DIRECTORY_ESCAPES_ROOT")
    manifest_bytes = (folder/"manifest.json").read_bytes()
    manifest = json.loads(manifest_bytes)
    if (manifest.get("schema") != "scp.expanded-original-3d-motion-corpus.v1" or
        manifest.get("batch") != batch or
        manifest.get("rights") != "CC0-1.0 for original generated files" or
        len(manifest.get("cases",[])) != BATCH_COUNTS[batch]):
        raise ValueError("WRONG_CORPUS_RIGHTS_BATCH_OR_CASE_COUNT")
    cases=[]
    ids=set()
    for item in manifest["cases"]:
        name=item["case"]
        if (type(name) is not str or not name or
            any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in name) or name in ids):
            raise ValueError("BAD_OR_DUPLICATE_CASE_ID")
        ids.add(name)
        path=folder/(name+"_ground_truth.json")
        if item["ground_truth"]["file"]!=path.name:
            raise ValueError("SOURCE_LABEL_PATH_MISMATCH")
        raw=path.read_bytes()
        if len(raw)>5_000_000 or hashlib.sha256(raw).hexdigest()!=item["ground_truth"]["sha256"]:
            raise ValueError("SOURCE_LABEL_SHA_FAILURE")
        doc=json.loads(raw)
        if (doc.get("case")!=name or doc.get("fps")!=20 or len(doc.get("frames",[]))!=40 or
            doc.get("spec")!=item.get("spec")):
            raise ValueError("CASE_SPEC_OR_FRAME_MISMATCH")
        sex=doc["spec"].get("sex")
        if sex not in LIMBS:
            raise ValueError("UNKNOWN_MORPHOLOGY")
        thigh,shin=LIMBS[sex]
        observations=[]
        for index,frame in enumerate(doc["frames"]):
            joints=frame["joints"]
            for side in ("left","right"):
                result=solve_3d(joints[side+"_hip"],joints[side+"_ankle"],thigh,shin,joints[side+"_knee"])
                observations.append({"frame":index,"side":side,**result})
        counts=Counter("UNREACHABLE" if v["status"]=="UNREACHABLE" else
            "FEASIBLE_ORIGINAL_BAD_BONE" if v["original_bad_bone"] else
            "FEASIBLE_ORIGINAL_GOOD_BONE" for v in observations)
        cases.append({
            "case":name,"source_labels_sha256":hashlib.sha256(raw).hexdigest(),
            "observation_count":len(observations),"counts":dict(counts),
            "max_off_plane_endpoint_m":max(v.get("off_plane_endpoint_displacement_m",0) for v in observations),
            "max_original_bone_error_m":max(v.get("original_knee_bone_error_m",
                v.get("old_max_bone_error_m",0)) for v in observations),
            "observations":observations,
        })
    if len(cases)!=BATCH_COUNTS[batch]:
        raise ValueError("SOURCE_CASE_COUNT_CHANGED")
    result_counts=Counter()
    for row in cases:
        result_counts.update(row["counts"])
    return {
        "schema":"scp.original-3d-two-link-ik-feasibility.v1",
        "batch":batch,"case_count":len(cases),
        "joint_observations":sum(c["observation_count"] for c in cases),
        "source_manifest_sha256":hashlib.sha256(manifest_bytes).hexdigest(),
        "counts":dict(result_counts),"cases":cases,
        "status":"RESEARCH_SOURCE_KINEMATIC_DIAGNOSTIC_ONLY",
        "limits":[
            "Mathematically reachable 3D two-link geometry is not physiologically permissible joint articulation",
            "Choosing the pole closest to an erroneous source knee is not a physical knee-polarity proof",
            "No stance, torque, balance, force, contact patch, visual realism, soft-tissue or human validation",
            "The original GLB/H264 and labels are read-only and not modified"]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True,type=Path)
    p.add_argument("--batch",required=True,choices=BATCH_COUNTS.keys())
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    result=audit_batch(args.root,args.batch)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("SOURCE_THREED_IK_FEASIBILITY",args.batch,result["joint_observations"],result["counts"])

if __name__=="__main__":
    main()
