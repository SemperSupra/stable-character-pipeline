"""Fail-closed independent multi-frame native shoe witness policy (stdlib only).

SOURCE/CANDIDATE geometry metrics are diagnostic. No temporary IK probe grants
stance, force, identity, visual naturalness, or product release acceptance.
"""
import math
import re

HEX = re.compile(r"^[0-9a-f]{64}$")
ACTORS = ("AsterOriginal", "JuniperOriginal")
SIDES = ("L", "R")
STARTS = (24, 48)


def require(ok, code):
    if not ok:
        raise ValueError(code)


def number(x):
    require(type(x) in (int, float) and math.isfinite(x), "NONFINITE_OBSERVATION")
    return float(x)


def sample(row):
    require(isinstance(row, dict), "OBSERVATION_SHAPE")
    require(set(row) == {"time_s", "xy_m", "min_z_m", "ik_delta_m", "max_joint_pose_rotation_rad", "nonlinear_gap_m"}, "OBSERVATION_FIELDS")
    require(isinstance(row["xy_m"], list) and len(row["xy_m"]) == 2, "OBSERVATION_XY")
    xy = [number(v) for v in row["xy_m"]]
    t, z = number(row["time_s"]), number(row["min_z_m"])
    ik, pose, gap = (number(row[k]) for k in ("ik_delta_m", "max_joint_pose_rotation_rad", "nonlinear_gap_m"))
    require(all(abs(v) < 100 for v in xy) and abs(z) < 10 and 0 <= t <= 6, "BOUNDED_GEOMETRY")
    require(0 <= ik <= .010001, "IK_TRUST_BUDGET_EXCEEDED")
    require(0 <= pose <= math.pi and 0 <= gap <= 100, "NEGATIVE_POSE_OR_GAP")
    return (t, xy, z, ik, pose, gap)


def kinematics(rows, fps):
    samples = [sample(row) for row in rows]
    require(len(samples) == (4 if fps == 24 else 9), "SAMPLE_RATE_LENGTH")
    require(all(abs(b[0] - a[0] - 1/fps) <= 1e-5 for a, b in zip(samples, samples[1:8 if fps == 60 else 4])), "IRREGULAR_TIMEBASE")
    if fps == 60:
        # The last 60Hz witness is the exact 24Hz endpoint at +0.125s,
        # i.e. +.008333...s after the seventh regular 60Hz step.
        require(abs(samples[-1][0] - samples[0][0] - 3/24) < 1e-5, "MISALIGNED_HELDOUT_ENDPOINT")
    speeds = [math.dist(a[1], b[1]) * fps for a, b in zip(samples, samples[1:])]
    if fps == 60:
        speeds[-1] = math.dist(samples[-2][1], samples[-1][1]) / (samples[-1][0] - samples[-2][0])
    near = [v for i, v in enumerate(speeds) if abs(samples[i][2]) <= .012 and abs(samples[i+1][2]) <= .012]
    return {
        "max_penetration_m": round(max(0, -min(row[2] for row in samples)), 6),
        "max_near_ground_slide_mps": round(max(near), 6) if near else None,
        "near_ground_adjacent_pairs": len(near),
        "max_all_speed_mps": round(max(speeds), 6),
        "max_ik_delta_m": round(max(row[3] for row in samples), 6),
        "max_joint_pose_rotation_rad": round(max(row[4] for row in samples), 6),
        "max_nonlinear_gap_m": round(max(row[5] for row in samples), 6),
    }


def assess(report):
    require(report.get("schema") == "scp.n03d-ab.native-material-temporal-ik.v1", "SCHEMA")
    require(report.get("source_class") == "ORIGINAL_FICTIONAL_CC0", "RIGHTS")
    require(report.get("source_motion_changed") is False and report.get("corrected_blend_saved") is False, "SOURCE_MUTATION")
    require(report.get("physical_contact_accepted") is False and report.get("mvp_accepted") is False, "FORGED_ACCEPTANCE")
    for field in ("source_scene_sha256", "source_trace_sha256", "source_100style_sha256"):
        require(isinstance(report.get(field), str) and HEX.fullmatch(report[field]) and report[field] != "0" * 64, "PROVENANCE_SHA")
    require(isinstance(report.get("windows"), list) and len(report["windows"]) == 8, "WINDOW_COUNT")
    ids = set()
    evaluated = []
    for w in report["windows"]:
        require(w.get("actor") in ACTORS and w.get("side") in SIDES and w.get("start_sample_24hz") in STARTS, "ACTOR_SIDE_FRAME")
        key = (w["actor"], w["side"], w["start_sample_24hz"])
        require(key not in ids, "DUPLICATE_WINDOW")
        ids.add(key)
        require(type(w.get("persistent_vertex_count")) == int and 8 <= w["persistent_vertex_count"] < 10000, "PERSISTENT_COHORT_INVALID")
        stat = {}
        for label in ("source_24", "candidate_24", "source_60", "candidate_60"):
            require(isinstance(w.get(label), list), "WITNESS_MISSING")
            fps = 24 if label.endswith("24") else 60
            require(abs(number(w[label][0]["time_s"]) - w["start_sample_24hz"]/24) < 1e-5, "WINDOW_CLOCK_JOIN")
            stat[label] = kinematics(w[label], fps)
        errors = []
        c = stat["candidate_60"]
        s = stat["source_60"]
        if c["max_penetration_m"] > .010:
            errors.append("REAL_SHOE_PENETRATION_GT_10MM")
        if c["near_ground_adjacent_pairs"] < 3:
            errors.append("UNKNOWN_CONSECUTIVE_CONTACT")
        if c["max_near_ground_slide_mps"] is None or c["max_near_ground_slide_mps"] > .08:
            errors.append("MATERIAL_SLIDING_UNQUALIFIED")
        if c["max_joint_pose_rotation_rad"] > .35:
            errors.append("JOINT_POSE_CHANGE_GT_0P35RAD")
        if c["max_nonlinear_gap_m"] > .002:
            errors.append("LOCAL_MODEL_RESPONSE_UNQUALIFIED")
        if not (c["max_penetration_m"] < s["max_penetration_m"] or c["max_all_speed_mps"] < s["max_all_speed_mps"]):
            errors.append("NO_OBSERVED_METRIC_IMPROVEMENT")
        errors.extend(["SOURCE_STANCE_UNKNOWN", "ANATOMICAL_HEEL_TOE_UNVERIFIED",
                       "INDEPENDENT_VISUAL_REVIEW_MISSING", "ROOT_JOINT_COUPLING_UNTESTED"])
        evaluated.append({
            "actor": w["actor"], "side": w["side"], "start_sample_24hz": w["start_sample_24hz"],
            "source_60": s, "candidate_60": c,
            "source_24": stat["source_24"], "candidate_24": stat["candidate_24"],
            "reasons": errors, "contact_accepted": False
        })
    require(len(ids) == 8, "INCOMPLETE_FULL_FACTORIAL")
    return {"schema": "scp.n03d-ab.independent-temporal-critic.v1",
            "status": "HOLD", "windows": evaluated,
            "physical_contact_accepted": False, "natural_gait_accepted": False,
            "mvp_accepted": False, "release_authorized": False}
