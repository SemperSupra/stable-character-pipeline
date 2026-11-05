#!/usr/bin/env python3
"""R009 source-original synthetic-human parameter contract (stdlib only).

This is a semantic/state interchange layer, NOT a clinical prediction, human
identity recognizer, or qualified anatomical mesh backend. No external assets.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import random
from datetime import date
from pathlib import Path

SCHEMA = "scp.r009.synthetic_human.parameters.v1"
SOURCE = "source_original_synthetic"
# Unit-bearing semantic controls; normalized controls carry no physical units.
CONTROLS = {
    "morphology.height_m": (1.2, 2.2, "m"),
    "morphology.shoulder_width_m": (0.28, 0.65, "m"),
    "morphology.waist_circumference_m": (0.50, 1.65, "m"),
    "morphology.hip_circumference_m": (0.65, 1.75, "m"),
    "morphology.adiposity": (0., 1., "unitless"),
    "morphology.muscularity": (0., 1., "unitless"),
    "morphology.jaw_width_ratio": (0.65, 1.45, "reference_ratio"),
    "morphology.nose_projection_ratio": (0.55, 1.55, "reference_ratio"),
    "morphology.lip_fullness": (0., 1., "unitless"),
    "morphology.brow_height_ratio": (0.65, 1.4, "reference_ratio"),
    "morphology.cheek_volume": (0., 1., "unitless"),
    "morphology.chin_projection_ratio": (0.6, 1.5, "reference_ratio"),
    "morphology.left_breast_volume": (0., 1., "relative"),
    "morphology.right_breast_volume": (0., 1., "relative"),
    "morphology.left_breast_projection": (0., 1., "relative"),
    "morphology.right_breast_projection": (0., 1., "relative"),
    "morphology.left_breast_ptosis": (0., 1., "unitless"),
    "morphology.right_breast_ptosis": (0., 1., "unitless"),
    "appearance.skin_melanin": (0., 1., "relative"),
    "appearance.skin_roughness": (0., 1., "unitless"),
    "appearance.hair_length_m": (0., 1.4, "m"),
    "appearance.hair_curl": (0., 1., "unitless"),
    "appearance.hair_density": (0., 1., "relative"),
}
ENUMS = {
    "appearance.skin_undertone": ("cool", "neutral", "warm", "olive"),
    "appearance.hair_style": ("none", "short", "straight", "wavy", "curly", "coiled", "braids", "updo"),
}
RGB_KEYS = ("appearance.left_iris_rgb", "appearance.right_iris_rgb", "appearance.hair_rgb")
ALL_PATHS = set(CONTROLS) | set(ENUMS) | set(RGB_KEYS)

class ContractError(ValueError):
    pass

def _assert(condition, reason):
    if not condition:
        raise ContractError(reason)

def _is_number(x):
    return type(x) in (int, float) and math.isfinite(x)

def _split(path):
    namespace, key = path.split(".", 1)
    return namespace, key

def _validate_control(path, value):
    _assert(path in ALL_PATHS, "UNKNOWN_CONTROL:" + path)
    if path in CONTROLS:
        lower, upper, _ = CONTROLS[path]
        _assert(_is_number(value) and lower <= value <= upper, "CONTROL_RANGE:" + path)
    elif path in ENUMS:
        _assert(type(value) is str and value in ENUMS[path], "CONTROL_ENUM:" + path)
    else:
        _assert(type(value) is list and len(value) == 3 and
                all(_is_number(v) and 0. <= v <= 1. for v in value), "CONTROL_RGB:" + path)

def _validate_value_groups(state):
    for group in ("morphology", "appearance"):
        _assert(type(state.get(group)) is dict, "MISSING_GROUP:" + group)
    actual = {"%s.%s" % (group, key)
              for group in ("morphology", "appearance")
              for key in state[group]}
    _assert(actual == ALL_PATHS, "CONTROL_SET_MISMATCH")
    for path in sorted(actual):
        group, key = _split(path)
        _validate_control(path, state[group][key])
    m = state["morphology"]
    ratio = m["shoulder_width_m"] / m["height_m"]
    _assert(0.16 <= ratio <= 0.35, "SHOULDER_HEIGHT_RATIO")
    _assert(m["hip_circumference_m"] >= m["waist_circumference_m"] * 0.72,
            "WAIST_HIP_RELATION")
    # These are engineering guards, not clinical population reference intervals.

def _valid_date(value):
    _assert(type(value) is str and date.fromisoformat(value).isoformat() == value,
            "INVALID_ISO_DATE")

def validate(state):
    _assert(type(state) is dict, "NOT_OBJECT")
    _assert(state.get("schema") == SCHEMA, "SCHEMA_MISMATCH")
    _assert(state.get("source_class") == SOURCE, "SOURCE_CLASS_MISMATCH")
    _assert(type(state.get("character_id")) is str and bool(state["character_id"].strip()),
            "MISSING_CHARACTER_ID")
    _assert(type(state.get("seed")) is int and state["seed"] >= 0, "INVALID_SEED")
    identity = state.get("identity")
    _assert(type(identity) is dict and set(identity) == {"stable_id", "body_latent", "face_latent"},
            "IDENTITY_STRUCTURE")
    _assert(identity["stable_id"] == state["character_id"], "IDENTITY_MISMATCH")
    for name in ("body_latent", "face_latent"):
        values = identity[name]
        _assert(type(values) is list and len(values) == 8 and
                all(_is_number(v) and -4 <= v <= 4 for v in values),
                "IDENTITY_LATENT:" + name)
    _validate_value_groups(state)
    timeline = state.get("timeline")
    _assert(type(timeline) is list, "TIMELINE_MISSING")
    previous = ""
    for event in timeline:
        _assert(type(event) is dict and set(event) ==
                {"date", "kind", "evidence", "changes"}, "EVENT_STRUCTURE")
        _valid_date(event["date"])
        _assert(event["date"] > previous, "EVENT_ORDER_OR_DUPLICATE_DATE")
        previous = event["date"]
        _assert(event["kind"] in ("aging", "body_change", "procedure", "styling", "observation"),
                "EVENT_KIND")
        _assert(event["evidence"] in ("synthetic", "artist_authored", "observed", "hypothesis"),
                "EVIDENCE_KIND")
        changes = event["changes"]
        _assert(type(changes) is dict and bool(changes), "EMPTY_EVENT")
        for path, value in changes.items():
            _validate_control(path, value)
    uncertainty = state.get("uncertainty", {})
    _assert(type(uncertainty) is dict, "UNCERTAINTY_STRUCTURE")
    for path, flag in uncertainty.items():
        _assert(path in ALL_PATHS, "UNKNOWN_UNCERTAINTY_PATH")
        _assert(flag in ("observed", "estimated", "unknown", "authored"),
                "UNCERTAINTY_ENUM")
    # Evaluate all dated states independently; avoid validating only the baseline.
    for event in timeline:
        at_date = event["date"]
        evaluated = snapshot(state, at_date, check=False)
        _validate_value_groups(evaluated)
    return True

def snapshot(state, at_date=None, check=True):
    if check:
        validate(state)
    result = copy.deepcopy(state)
    result["timeline"] = []
    if at_date is not None:
        _valid_date(at_date)
        for event in state["timeline"]:
            if event["date"] <= at_date:
                for path, value in event["changes"].items():
                    group, key = _split(path)
                    result[group][key] = copy.deepcopy(value)
    return result

def sample(seed, character_id=None):
    _assert(type(seed) is int and seed >= 0, "INVALID_SEED")
    rng = random.Random(seed)
    def uniform(a, b):
        return round(rng.uniform(a, b), 6)
    h = uniform(1.5, 1.95)
    adiposity = uniform(.15, .80)
    muscularity = uniform(.1, .9)
    # Correlated synthetic reference; this is NOT a demographically fitted model.
    shoulder = round(h * (.215 + .02 * muscularity + rng.uniform(-.015, .015)), 6)
    waist = round(.57 + .48 * adiposity + .06 * (h - 1.5) + rng.uniform(-.03, .03), 6)
    hip = round(max(waist * .95, .74 + .38 * adiposity + rng.uniform(-.04, .04)), 6)
    breast = uniform(.1, .85)
    iris = [uniform(.05,.9),uniform(.05,.9),uniform(.05,.9)]
    hair = [uniform(.02,.85),uniform(.02,.85),uniform(.02,.85)]
    ident = character_id or "Synthetic-%08d" % seed
    state = {
        "schema": SCHEMA, "source_class": SOURCE, "character_id": ident, "seed": seed,
        "identity": {"stable_id": ident,
                     "body_latent": [uniform(-1.5,1.5) for _ in range(8)],
                     "face_latent": [uniform(-1.5,1.5) for _ in range(8)]},
        "morphology": {
            "height_m": h, "shoulder_width_m": shoulder,
            "waist_circumference_m": waist, "hip_circumference_m": hip,
            "adiposity": adiposity, "muscularity": muscularity,
            "jaw_width_ratio": uniform(.78,1.24),
            "nose_projection_ratio": uniform(.75,1.3),
            "lip_fullness": uniform(.15,.85),
            "brow_height_ratio": uniform(.82,1.20),
            "cheek_volume": uniform(.2,.8),
            "chin_projection_ratio": uniform(.8,1.2),
            "left_breast_volume": breast,
            "right_breast_volume": round(max(0., min(1., breast + rng.uniform(-.035,.035))),6),
            "left_breast_projection": uniform(.2,.8),
            "right_breast_projection": uniform(.2,.8),
            "left_breast_ptosis": uniform(.05,.55),
            "right_breast_ptosis": uniform(.05,.55),
        },
        "appearance": {
            "skin_melanin": uniform(.05,.95), "skin_roughness": uniform(.18,.8),
            "skin_undertone": rng.choice(ENUMS["appearance.skin_undertone"]),
            "left_iris_rgb": iris, "right_iris_rgb": iris.copy(),
            "hair_rgb": hair, "hair_length_m": uniform(0.,1.0),
            "hair_curl": uniform(0.,1.), "hair_density": uniform(.15,1.),
            "hair_style": rng.choice(ENUMS["appearance.hair_style"]),
        },
        "timeline": [], "uncertainty": {}
    }
    validate(state)
    return state

def add_event(state, when, kind, evidence, changes):
    _assert(type(changes) is dict and bool(changes), "EMPTY_EVENT")
    derived = copy.deepcopy(state)
    derived["timeline"].append({"date": when, "kind": kind,
                                "evidence": evidence, "changes": copy.deepcopy(changes)})
    validate(derived)
    return derived

def canonical_bytes(state):
    validate(state)
    return (json.dumps(state, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                       allow_nan=False) + "\n").encode("utf-8")

def sha256(state):
    return hashlib.sha256(canonical_bytes(state)).hexdigest()

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--seed", type=int, required=True)
    g.add_argument("--character-id")
    g.add_argument("--out", type=Path)
    v = sub.add_parser("validate")
    v.add_argument("input", type=Path)
    c = sub.add_parser("catalog")
    s = sub.add_parser("snapshot")
    s.add_argument("input", type=Path)
    s.add_argument("--date", required=True)
    args = ap.parse_args()
    if args.command == "catalog":
        print(json.dumps({"schema": SCHEMA, "numeric": CONTROLS, "enum": ENUMS,
                          "rgb": RGB_KEYS}, sort_keys=True, indent=2))
        return
    if args.command == "generate":
        payload = sample(args.seed, args.character_id)
        encoded = canonical_bytes(payload)
        if args.out:
            with args.out.open("xb") as f:
                f.write(encoded)
        else:
            print(encoded.decode("utf-8"), end="")
        return
    state = json.loads(args.input.read_text("utf-8"))
    validate(state)
    if args.command == "validate":
        print(json.dumps({"valid": True, "sha256": sha256(state),
                          "character_id": state["character_id"]}))
    else:
        result = snapshot(state, args.date)
        print(canonical_bytes(result).decode("utf-8"), end="")

if __name__ == "__main__":
    main()
