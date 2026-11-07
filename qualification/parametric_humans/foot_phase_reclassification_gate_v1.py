#!/usr/bin/env python3
"""Fail-closed ankle-velocity + shoe-proximity reclassification of foot support.

The old persistent-shoe mask can include moving swing feet; this gate cannot
approve biomechanics, root correction, IK, Blender evaluation or release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = "scp.r009.ankle_sole_phase_witness.v1"
OUT_SCHEMA = "scp.r009.foot_phase_reclassification.v1"
OLD_SCHEMA = "scp.r009.shoe_sole_correspondence_cpu72.v1"
SOURCE_SHA256 = "b92f755607b9175b0e7874fa60f6d64eca1eb939d609947b672cc46b36e0d748"
ACTORS = ("AsterOriginal", "JuniperOriginal")
SIDES = ("L", "R")
ANKLE_MAX_M = .008
FLOOR_PROXIMITY_MAX_M = .008
PRIOR_CONFLICT_M = .020

class PhaseEvidenceError(ValueError):
    pass


def require(condition, why):
    if not condition:
        raise PhaseEvidenceError(why)


def is_number(value, lo=-20., hi=20.):
    return type(value) in (int, float) and math.isfinite(value) and lo <= value <= hi


def vec3_series(obj, label):
    require(type(obj) is list and len(obj) == 72, label + ":72")
    for p in obj:
        require(type(p) is list and len(p) == 3 and all(is_number(v) for v in p), label + ":XYZ")
    return obj


def heights(obj, label):
    require(type(obj) is list and len(obj) == 72 and all(is_number(x, -.1, .1) for x in obj), label)
    return obj


def distance_xz(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])


def evaluate(witness, prior, prior_raw: bytes | None = None):
    require(type(witness) is dict and witness.get("schema") == SCHEMA, "WITNESS_SCHEMA")
    require(witness.get("source_sha256") == SOURCE_SHA256, "WITNESS_SOURCE")
    require(witness.get("coordinate_up") == "Y" and type(witness.get("frames")) is int and witness["frames"] == 72, "WITNESS_FRAME_AXES")
    require(type(prior) is dict and prior.get("schema") == OLD_SCHEMA and prior.get("source_sha256") == SOURCE_SHA256, "PRIOR_SOURCE")
    require(prior.get("coordinate_up") == "Y" and type(prior.get("frames")) is int and prior["frames"] == 72, "PRIOR_FRAME_AXES")
    for flag in ("root_shift_applied", "foot_ik_applied", "native_blender_evaluated", "gait_accepted", "release_approved"):
        require(witness.get(flag) is False, "FALSE_ACCEPTANCE:" + flag)
    for flag in ("root_shift_applied", "native_blender_evaluated", "gait_accepted", "release_approved"):
        require(prior.get(flag) is False, "FALSE_PRIOR_ACCEPTANCE:" + flag)
    require(type(witness.get("actors")) is dict and set(witness["actors"]) == set(ACTORS), "WITNESS_ACTORS")
    require(type(prior.get("actors")) is dict and set(prior["actors"]) == set(ACTORS), "PRIOR_ACTORS")
    for key in ("sole_correspondence_sha256", "shoe_support_sha256"):
        digest = witness.get(key)
        require(type(digest) is str and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "INPUT_DIGEST:" + key)
    if prior_raw is not None:
        require(hashlib.sha256(prior_raw).hexdigest() == witness["sole_correspondence_sha256"], "PRIOR_BYTE_PIN")
    actors = {}
    for actor in ACTORS:
        observed = witness["actors"][actor]
        old = prior["actors"][actor]
        require(type(observed) is dict and set(observed) == {"ankle_world_xyz_m", "shoe_min_y_m", "diagnostic_root_lift_m"}, "ACTOR_FIELDS")
        require(type(old) is dict and type(old.get("transitions")) is list and len(old["transitions"]) == 71, "OLD_TRANSITIONS")
        require(type(observed["ankle_world_xyz_m"]) is dict and set(observed["ankle_world_xyz_m"]) == set(SIDES), "ANKLES")
        require(type(observed["shoe_min_y_m"]) is dict and set(observed["shoe_min_y_m"]) == set(SIDES), "SHOES")
        points = {s: vec3_series(observed["ankle_world_xyz_m"][s], "ANKLE:" + s) for s in SIDES}
        shoe = {s: heights(observed["shoe_min_y_m"][s], "SHOE:" + s) for s in SIDES}
        lift = heights(observed["diagnostic_root_lift_m"], "ROOT_LIFT")
        require(old.get("required_root_y_clearance_m") == lift, "ROOT_LIFT_MISMATCH")
        for f in range(72):
            require(abs(min(shoe[s][f] for s in SIDES) + lift[f]) <= 1e-7, "SOLE_GROUND_REFERENCE")
        old_conflicts = []
        reclassified = []
        dual_stationary = []
        support_by_side = {s: [] for s in SIDES}
        unsupported_old = []
        for i, record in enumerate(old["transitions"], 1):
            require(type(record) is dict and type(record.get("frame_to")) is int and record["frame_to"] == i, "TRANSITION_INDEX")
            feet = record.get("feet")
            require(type(feet) is dict and set(feet) == set(SIDES), "PRIOR_FEET")
            predicted = {}
            motion = {}
            for s in SIDES:
                n = feet[s].get("persistent_vertices")
                require(type(n) is int and 0 <= n <= 20000, "PERSISTENT_VERTEX_COUNT")
                if n >= 5:
                    v = feet[s].get("median_xz_motion_m")
                    require(type(v) is list and len(v) == 2 and all(is_number(x, -1, 1) for x in v), "PRIOR_MOTION")
                motion[s] = distance_xz(points[s][i], points[s][i-1])
                near = max(shoe[s][i] + lift[i], shoe[s][i-1] + lift[i-1]) <= FLOOR_PROXIMITY_MAX_M
                predicted[s] = near and motion[s] <= ANKLE_MAX_M
                if predicted[s]:
                    support_by_side[s].append(i)
            dual = record.get("dual_support_root_motion_disagreement_m")
            if all(feet[s]["persistent_vertices"] >= 5 for s in SIDES):
                lv, rv = (feet[s]["median_xz_motion_m"] for s in SIDES)
                assert isinstance(lv, list) and isinstance(rv, list)
                require(is_number(dual, 0, 2) and abs(dual - math.dist(lv, rv)) <= 1e-8, "OLD_CONFLICT_FORGED")
            else:
                require(dual is None, "SPURIOUS_PRIOR_CONFLICT")
            if predicted["L"] and predicted["R"]:
                delta_l = (points["L"][i][0] - points["L"][i-1][0], points["L"][i][2] - points["L"][i-1][2])
                delta_r = (points["R"][i][0] - points["R"][i-1][0], points["R"][i][2] - points["R"][i-1][2])
                dual_stationary.append({"frame_to": i, "ankle_motion_disagreement_m": math.dist(delta_l, delta_r)})
            if dual is not None and dual > PRIOR_CONFLICT_M:
                old_conflicts.append(i)
                item = {"frame_to": i, "ankle_motion_L_m": motion["L"], "ankle_motion_R_m": motion["R"],
                        "old_disagreement_m": dual, "bilateral_stationary": bool(predicted["L"] and predicted["R"])}
                if not item["bilateral_stationary"]:
                    reclassified.append(item)
                else:
                    unsupported_old.append(item)
        actors[actor] = {
            "old_conflicts": len(old_conflicts),
            "old_conflicts_reclassified_as_moving_foot": len(reclassified),
            "old_conflicts_retained_stationary": len(unsupported_old),
            "stationary_dual_transitions": len(dual_stationary),
            "stationary_dual_disagreement_max_m": max((r["ankle_motion_disagreement_m"] for r in dual_stationary), default=None),
            "stationary_support_transition_counts": {s: len(support_by_side[s]) for s in SIDES},
            "reclassified_first_red": reclassified,
            "true_stationary_examples": dual_stationary[:10],
        }
    return {
        "schema": OUT_SCHEMA, "source_sha256": SOURCE_SHA256,
        "shoe_support_sha256": witness["shoe_support_sha256"],
        "sole_correspondence_sha256": witness["sole_correspondence_sha256"],
        "ankle_stationary_threshold_m_per_frame": ANKLE_MAX_M,
        "shoe_ground_proximity_m": FLOOR_PROXIMITY_MAX_M,
        "actors": actors,
        "verdict": "CORRECT_PRIOR_DUAL_CONTACT_CONFOUND_RESEARCH_ONLY" if any(actors[a]["old_conflicts_reclassified_as_moving_foot"] for a in ACTORS) else "HOLD_NO_PRIOR_CONFOUND_EVIDENCE",
        "root_only_impossibility_proven": False,
        "root_shift_applied": False, "foot_ik_applied": False,
        "native_blender_evaluated": False,
        "physical_contact_accepted": False, "gait_accepted": False,
        "release_approved": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--witness", required=True, type=Path)
    ap.add_argument("--sole", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    require(args.out.resolve() not in (args.witness.resolve(), args.sole.resolve()) and not args.out.exists(), "NO_OVERWRITE")
    prior_raw = args.sole.read_bytes()
    result = evaluate(json.loads(args.witness.read_text()), json.loads(prior_raw), prior_raw)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"verdict": result["verdict"], "actors": {a: {k: v for k, v in row.items() if isinstance(v, int)} for a, row in result["actors"].items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
