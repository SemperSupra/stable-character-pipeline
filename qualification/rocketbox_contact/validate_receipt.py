#!/usr/bin/env python3
"""Independent, stdlib fail-closed witness validator; contact remains NOT_ADMITTED."""
import argparse
import json
import math
from pathlib import Path

NAMES = ("RB_RB_F01_root", "RB_RB_F02_root")
SOURCE = "2e5c5fcc826c95d200b06cc2dcd22138944102426a86f1f683689ae458aff7ab"
ZIP = "2bbf1036744e4fcd614cd207bc9e9eb2147b943f59c53d9de7dff1b324320204"

def deny(text):
    raise ValueError(text)

def pairs(items):
    out = {}
    for k, v in items:
        if k in out:
            deny("DUPLICATE_JSON_KEY:" + k)
        out[k] = v
    return out

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=pairs,
                      parse_constant=lambda name: deny("INVALID_JSON_CONSTANT:" + name))

def vec(v, key):
    if not isinstance(v, list) or len(v) != 3:
        deny("VEC3_REQUIRED:" + key)
    if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in v):
        deny("NONFINITE_VEC3:" + key)
    return v

def num(n, key):
    if isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n):
        deny("NONFINITE_NUMBER:" + key)
    return float(n)

def validate(r):
    if not isinstance(r, dict):
        deny("RECEIPT_OBJECT_REQUIRED")
    required = {
        "schema": "scp.mit_native_all72_foot_mesh_proxy.v1",
        "status": "NATIVE_OBSERVED_72F_FOOT_AND_SKIN_ONLY",
        "source_zip_sha256": ZIP, "source_blend_sha256": SOURCE,
        "source_mit": "WITH_NOTICE", "source_names": list(NAMES),
        "frame_count": 72, "fps": 12,
        "foot_contact_accepted": False,
        "joint_coordinate_system_calibrated": False,
        "normative_biomechanics_accepted": False,
        "human_gait": "UNKNOWN", "product_accepted": False
    }
    for key, wanted in required.items():
        if key not in r or type(r[key]) is not type(wanted) or r[key] != wanted:
            deny("CLAIM_CONTRACT_MISMATCH:" + key)
    ground = num(r.get("ground_surface_z_m"), "ground")
    frames = r.get("observations")
    if not isinstance(frames, list) or len(frames) != 72:
        deny("ALL72_FRAME_SCOPE_REQUIRED")
    roots = [[], []]
    for i, frame in enumerate(frames):
        if not isinstance(frame, dict) or type(frame.get("frame")) is not int or frame["frame"] != i:
            deny("FRAME_ORDER:" + str(i))
        actors = frame.get("actors")
        if not isinstance(actors, list) or len(actors) != 2:
            deny("ACTOR_COUNT:" + str(i))
        for j, a in enumerate(actors):
            if not isinstance(a, dict) or a.get("root") != NAMES[j]:
                deny("SOURCE_NATIVE_ACTOR:" + str(i))
            position = vec(a.get("root_world_m"), "root")
            roots[j].append(position[0])
            count = a.get("sampled_native_mesh_vertices")
            if type(count) is not int or count < 1000:
                deny("NATIVE_MESH_VERTEX_COUNT")
            zmin = num(a.get("evaluated_mesh_min_z_m"), "zmin")
            clearance = num(a.get("evaluated_mesh_min_clearance_m"), "clearance")
            if abs(zmin-ground-clearance) > 1.e-5:
                deny("MESH_GROUND_CLEARANCE_ARITHMETIC")
            feet = a.get("feet")
            if not isinstance(feet, dict) or set(feet) != {"L", "R"}:
                deny("BOTH_NATIVE_FEET_REQUIRED")
            for side in ("L", "R"):
                foot = feet[side]
                head = vec(foot.get("toe_head_world_m"), "toe_head")
                tail = vec(foot.get("toe_tail_world_m"), "toe_tail")
                height = num(foot.get("toe_tail_height_above_ground_m"), "toe_height")
                angle = num(foot.get("knee_interior_angle_deg_unqualified"), "knee")
                if abs(tail[2]-ground-height) > 1.e-5:
                    deny("TOE_GROUND_CLEARANCE_ARITHMETIC")
                if angle < 0 or angle > 180:
                    deny("INVALID_UNQUALIFIED_KNEE_ANGLE")
    start = abs(roots[0][0]-roots[1][0])
    end = abs(roots[0][-1]-roots[1][-1])
    pair = r.get("root_separation_start_end_m")
    if not isinstance(pair, list) or len(pair) != 2:
        deny("ROOT_SEPARATION_MISSING")
    if abs(num(pair[0], "root_start")-start) > 1.e-5 or abs(num(pair[1], "root_end")-end) > 1.e-5:
        deny("ROOT_SEPARATION_FORGERY")
    if start-end < 1.:
        deny("NATIVE_ROOT_APPROACH_MISSING")
    proximity = r.get("toe_ground_proximity_heuristics")
    if not isinstance(proximity, dict) or set(proximity) != set(NAMES):
        deny("FOOT_HEURISTIC_OWNERSHIP_MISSING")
    for j, root in enumerate(NAMES):
        if set(proximity[root]) != {"L", "R"}:
            deny("FOOT_HEURISTIC_SIDES_MISSING")
        for side in ("L", "R"):
            near = suspect = 0
            max_step = 0.
            for i in range(71):
                a = frames[i]["actors"][j]["feet"][side]
                b = frames[i+1]["actors"][j]["feet"][side]
                ah = a["toe_tail_height_above_ground_m"]
                bh = b["toe_tail_height_above_ground_m"]
                if -.04 <= ah <= .065 and -.04 <= bh <= .065:
                    near += 1
                    axy, bxy = a["toe_tail_world_m"], b["toe_tail_world_m"]
                    dist = math.hypot(bxy[0]-axy[0], bxy[1]-axy[1])
                    max_step = max(max_step, dist)
                    if dist > .04:
                        suspect += 1
            supplied = proximity[root][side]
            if supplied.get("near_ground_consecutive_frame_pairs_proxy_only") != near:
                deny("REPORTED_NEAR_GROUND_COUNT_FORGERY")
            if supplied.get("proxy_slide_gt_4cm_pairs") != suspect:
                deny("REPORTED_SLIDE_COUNT_FORGERY")
            if abs(num(supplied.get("maximum_proxy_horizontal_step_m"), "maxstep")-max_step) > 1e-6:
                deny("REPORTED_MAX_STEP_FORGERY")
    return {"status": "INDEPENDENT_NATIVE_72F_STRUCTURAL_WITNESS_ONLY",
            "source_blend_sha256": SOURCE,
            "frames_verified": 72,
            "actor_count": 2,
            "root_separation_start_end_m": [start, end],
            "physical_contact": "NOT_ADMITTED",
            "human_gait": "UNKNOWN",
            "product_accepted": False}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--out")
    args = parser.parse_args()
    result = validate(load(args.input))
    text = json.dumps(result, sort_keys=True, indent=2) + chr(10)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
