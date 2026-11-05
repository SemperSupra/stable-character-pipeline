#!/usr/bin/env python3
"""R009 source-original semantic-to-geometry effect coverage witness, NOT anatomy QA.

Checks the real AsterOriginal skin/body preview adapter for every control path.
Does NOT pretend appearance controls modify geometry or are Blender-material wired.
Source-only, deterministic, offline, stdlib and no protected characters.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import parameters_v1 as contract
import morph_preview_35_v1 as adapter

SCHEMA = "scp.r009.parametric_control_effect_coverage.v1"

def variants(base, path):
    group, key = path.split(".", 1)
    current = base[group][key]
    if path in contract.CONTROLS:
        lower, upper, _ = contract.CONTROLS[path]
        width = upper - lower
        candidates = [min(upper, current + width * factor)
                      for factor in (.06, .12)]
        candidates += [max(lower, current - width * factor)
                       for factor in (.06, .12)]
    elif path in contract.ENUMS:
        candidates = [v for v in contract.ENUMS[path] if v != current]
    else:
        candidates = [list(current)]
        candidates[0][0] = 1.0 if current[0] < .5 else 0.0
    for candidate in candidates:
        if candidate == current:
            continue
        state = copy.deepcopy(base)
        state[group][key] = candidate
        try:
            contract.validate(state)
        except contract.ContractError:
            continue
        yield state

def geometric_changes(baseline, comparison):
    changes = {}
    if set(baseline.parts) != set(comparison.parts):
        raise ValueError("MATERIAL_SET_CHANGED")
    for key in baseline.parts:
        a, b = baseline.parts[key], comparison.parts[key]
        for immutable in ("i", "j", "w"):
            if a[immutable] != b[immutable]:
                raise ValueError("NONDESTRUCTIVE_INVARIANT_BROKEN:" + immutable)
        if len(a["p"]) != len(b["p"]):
            raise ValueError("TOPOLOGY_COUNT_CHANGED")
        diff = sum(x != y for x, y in zip(a["p"], b["p"]))
        if diff:
            changes[key] = diff
    return changes

def witness(seed=73):
    baseline_state = contract.sample(seed)
    baseline_mesh, _ = adapter.apply_original_shape(0, baseline_state)
    rows = []
    for path in sorted(contract.ALL_PATHS):
        proof = []
        for candidate in variants(baseline_state, path):
            mesh, _ = adapter.apply_original_shape(0, candidate)
            proof = geometric_changes(baseline_mesh, mesh)
            if proof:
                break
        status = "GEOMETRY_EFFECT_CONFIRMED" if proof else "NO_GEOMETRY_EFFECT"
        rows.append({"path": path, "status": status,
                     "changed_coordinate_counts_by_material": proof,
                     "native_blender_render_verified": False,
                     "garment_retarget_verified": False})
    active = sum(r["status"] == "GEOMETRY_EFFECT_CONFIRMED" for r in rows)
    return {
        "schema": SCHEMA,
        "source_class": contract.SOURCE,
        "seed": seed,
        "source_character_sha256": contract.sha256(baseline_state),
        "control_count": len(rows),
        "geometry_effect_controls": active,
        "not_geometry_effect_controls": len(rows)-active,
        "all_controls_implemented": False,
        "appearance_materials_implemented": False,
        "clinically_validated": False,
        "human_visual_accepted": False,
        "method": "per-control source-original geometrical counterfactual, fixed baseline seed",
        "controls": rows,
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=73)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    data = witness(args.seed)
    output = json.dumps(data, sort_keys=True, indent=2) + "\n"
    if args.out:
        with args.out.open("x", encoding="utf-8") as stream:
            stream.write(output)
    else:
        print(output, end="")

if __name__ == "__main__":
    main()
