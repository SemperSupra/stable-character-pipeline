#!/usr/bin/env python3
"""Independent rights-original jumping-jacks A/B stance/flight geometry research.

Unlike original synthetic all-contact labels, the candidate has explicitly
defined grounded holds and moving airborne intervals. Contact is derived from
physical support in the proposed motion, never edited after generation to
change the independent audit verdict. No other source is patched or changed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
sys.path.insert(0, str(ROOT / "expanded_motion_corpus"))
import build_motion_batches as gen
import motion_math

CASE = "female_jumping_jacks_sandals"
BATCH = "exercise_pose"
ORIGINAL = gen.jumping_jacks_motion
FRAMES = gen.FRAMES
FPS = gen.FPS
SUPPORT_Z = gen.FOOTWEAR["sandals"].toe_thickness + 0.058
# Explicit bounded motion-state sequence, seconds synchronized to 20 FPS.
CLOSED_END = 0.125
OPEN_TOUCHDOWN = 0.50
OPEN_END = 0.625
FRAME_PERIOD_SECONDS = 1.2

def phase_at(t: float) -> float:
    return (t / FRAME_PERIOD_SECONDS) % 1.0

def contract_state(t: float):
    phase = phase_at(t)
    if phase < CLOSED_END:
        return "closed_stance", 0., 0., True
    if phase < OPEN_TOUCHDOWN:
        u = (phase - CLOSED_END) / (OPEN_TOUCHDOWN - CLOSED_END)
        return "opening_flight", gen.smooth01(u), 0.105 * math.sin(math.pi*u), False
    if phase < OPEN_END:
        return "open_stance", 1., 0., True
    u = (phase - OPEN_END) / (1.0 - OPEN_END)
    return "closing_flight", 1. - gen.smooth01(u), 0.105 * math.sin(math.pi*u), False

def proposed_jacks(t, body, shoe):
    # All contact/flight positions derive from one deterministic phase law.
    # Feet remain world fixed in each stance (closed/open) without labels
    # being post-hoc changed. Airborne feet animate through the same 3D path.
    state, spread, rise, contact = contract_state(t)
    root = gen.np.array([0.26, 0., body.torso_base + 0.045 * math.sin(math.pi * rise / 0.105)])
    feet = {
        "left": gen.np.array([0.24 - .15*spread, -body.hip_half - .070*spread, SUPPORT_Z + rise]),
        "right": gen.np.array([0.28 + .15*spread, body.hip_half + .070*spread, SUPPORT_Z + rise])
    }
    return root, feet, {"left":contact,"right":contact}, spread

def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_original(original_root: Path):
    folder=original_root/BATCH
    manifest=json.loads((folder/"manifest.json").read_text())
    if (manifest.get("schema")!="scp.expanded-original-3d-motion-corpus.v1"
        or manifest.get("batch")!=BATCH
        or manifest.get("rights")!="CC0-1.0 for original generated files"):
        raise ValueError("UNTRUSTED_ORIGINAL_MANIFEST")
    cases=[x for x in manifest.get("cases",[]) if x.get("case")==CASE]
    if len(cases)!=1:
        raise ValueError("ORIGINAL_CASE_MISSING_OR_DUPLICATE")
    item=cases[0]
    for field, suffix in ((item["ground_truth"], "_ground_truth.json"),
                          (item["model"], ".glb"),
                          (item["videos"][0], "_side.mp4")):
        if field.get("file")!=CASE+suffix or file_sha(folder/field["file"])!=field.get("sha256"):
            raise ValueError("ORIGINAL_SOURCE_MEDIA_SHA_MISMATCH")
    audit=motion_math.audit_case(folder/(CASE+"_ground_truth.json"), {"male":(.54,.53),"female":(.52,.51)})
    if audit["status"]!="FAIL" or audit["defect_count"]!=78:
        raise ValueError("ORIGINAL_NEGATIVE_CONTROL_CHANGED")
    return item,audit

def independent_contact_witness(frames):
    if len(frames)!=FRAMES:
        raise ValueError("INVALID_CANDIDATE_FRAME_COUNT")
    counts={"closed_stance":0,"open_stance":0,"opening_flight":0,"closing_flight":0}
    changed_labels=0
    flight_heights=[]
    supported_intervals=0
    for i,f in enumerate(frames):
        if f.get("frame")!=i:
            raise ValueError("FRAME_INDEX_CHANGED")
        state,spread,rise,is_contact=contract_state(i/FPS)
        counts[state]+=1
        for side in ("left","right"):
            if type(f["contact"][side]) is not bool or f["contact"][side]!=is_contact:
                raise ValueError("CONTACT_NOT_DERIVED_FROM_MOTION_PHASE")
            ankle=f["joints"][side+"_ankle"]
            expected_x=(0.24-.15*spread) if side=="left" else (0.28+.15*spread)
            expected_y=(-gen.BODIES["female"].hip_half-.070*spread) if side=="left" else (gen.BODIES["female"].hip_half+.070*spread)
            if math.dist(ankle,[expected_x,expected_y,SUPPORT_Z+rise])>1e-7:
                raise ValueError("CONTACT_AND_KINEMATIC_SOURCE_NOT_ALIGNED")
            if is_contact and abs(ankle[2]-SUPPORT_Z)>1e-8:
                raise ValueError("GROUNDED_ANKLE_SUPPORT_HEIGHT_INCONSISTENT")
            if not is_contact and rise>0.0001:
                flight_heights.append(ankle[2]-SUPPORT_Z)
            if i and f["contact"][side] and frames[i-1]["contact"][side]:
                supported_intervals+=1
                if math.dist(ankle,frames[i-1]["joints"][side+"_ankle"])>1e-7:
                    raise ValueError("CONTACT_TRUE_BUT_WORLD_ANKLE_SLIDES")
        if not is_contact:
            changed_labels+=1
    if (counts["closed_stance"]<2 or counts["open_stance"]<2
        or counts["opening_flight"]<6 or counts["closing_flight"]<6
        or changed_labels<20 or supported_intervals<6
        or not flight_heights or max(flight_heights)<0.095):
        raise ValueError("NO_GENUINE_TAKEOFF_LANDING_OR_STANCE_EVIDENCE")
    return {"sampled_phase_frame_counts":counts,
            "airborne_frames_per_side":changed_labels,
            "grounded_stance_intervals_both_feet":supported_intervals,
            "max_ankle_rise_above_support_m":round(max(flight_heights),8),
            "support_ankle_z_m":SUPPORT_Z,
            "limitation":"Flight and contact kinematics are procedural, not measured forces or human biomechanics"}

def evaluate(original_root: Path, out_root: Path):
    original_root=Path(original_root)
    item,original_audit=load_original(original_root)
    root=Path(out_root)/BATCH
    root.mkdir(parents=True, exist_ok=True)
    if gen.jumping_jacks_motion is not ORIGINAL:
        raise ValueError("SOURCE_GENERATOR_ALREADY_PATCHED")
    try:
        gen.jumping_jacks_motion=proposed_jacks
        candidate=gen.build_case(CASE,root)
    finally:
        gen.jumping_jacks_motion=ORIGINAL
    candidate_audit=motion_math.audit_case(root/(CASE+"_ground_truth.json"), {"male":(.54,.53),"female":(.52,.51)})
    if candidate_audit["status"]!="PASS" or candidate_audit["defect_count"]!=0:
        raise ValueError("CANDIDATE_SOURCE_RESEARCH_GATE_FAILED:"+json.dumps(candidate_audit["findings"][:8]))
    if (item["model"]["sha256"]==candidate["model"]["sha256"]
        or item["videos"][0]["sha256"]==candidate["videos"][0]["sha256"]
        or item["ground_truth"]["sha256"]==candidate["ground_truth"]["sha256"]):
        raise ValueError("NO_REAL_ORIGINAL_TO_CANDIDATE_MEDIA_CHANGE")
    old=json.loads((original_root/BATCH/(CASE+"_ground_truth.json")).read_text())
    new=json.loads((root/(CASE+"_ground_truth.json")).read_text())
    if len(old["frames"])!=len(new["frames"]) or len(new["frames"])!=FRAMES:
        raise ValueError("SOURCE_CLOCK_CHANGED")
    if any(f["contact"]!={"left":True,"right":True} for f in old["frames"]):
        raise ValueError("ORIGINAL_ALL_CONTACT_NEGATIVE_CONTROL_CHANGED")
    witness=independent_contact_witness(new["frames"])
    manifest={"schema":"scp.expanded-original-3d-motion-corpus.v1", "batch":BATCH,
              "rights":"CC0-1.0 for original generated files","fps":FPS,"frames":FRAMES,
              "resolution":[gen.SIZE,gen.SIZE],"cases":[candidate],
              "research_original_case_is_not_modified":True}
    (root/"manifest.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n")
    report={"schema":"scp.visualqa.jacks-grounded-flight-ab.v1","case":CASE,
            "original_case_sha":{"labels":item["ground_truth"]["sha256"],
                                 "glb":item["model"]["sha256"],"h264":item["videos"][0]["sha256"]},
            "candidate_case_sha":{"labels":candidate["ground_truth"]["sha256"],
                                  "glb":candidate["model"]["sha256"],"h264":candidate["videos"][0]["sha256"]},
            "original_audit":original_audit,
            "candidate_audit":candidate_audit,
            "contact_witness":witness,
            "verdict":"TARGETED_SOURCE_KINEMATIC_CANDIDATE_ONLY",
            "limitations":[
                "Original all-contact source labels retained immutable in prior artifact; candidate modifies both physically represented trajectories and contact semantics",
                "Candidate foot and root trajectory designed independently from source audit: never relabel after a failed source verdict",
                "No momentum, impulse, contact force, center of mass, joint-limit, footwear mechanics or human realism acceptance",
                "No production source/GLB/H264 release, original negative-control overwrite, or MAC actor source conflict"]}
    (root/"jacks-ab-receipt.json").write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-root",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    report=evaluate(Path(a.original_root),Path(a.out))
    print("ORIGINAL_JACKS_TRUE_MOTION_AB",report["original_audit"]["defect_count"],
          report["candidate_audit"]["defect_count"],report["contact_witness"])

if __name__=="__main__":
    main()
