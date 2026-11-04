"""Independent fail-closed native MIT axis/weighted-skin receipt syntax reviewer.

Structural integrity only. Never human joint-axis or foot-ground certification.
"""
import argparse
import json
import math
from pathlib import Path
from probe_axes import SCHEMA, ROOTS, SOURCE_SHA


class Rejected(ValueError):
    pass


def finite(v):
    return type(v) in (float, int) and math.isfinite(v)


def check(doc):
    if type(doc) is not dict or doc.get("schema") != SCHEMA:
        raise Rejected("BAD_NATIVE_PROBE_SCHEMA")
    if doc.get("source_blend_sha256") != SOURCE_SHA or doc.get("fps") != 12 or doc.get("frame") != 36:
        raise Rejected("FROZEN_SOURCE_CLOCK_DIGEST")
    if doc.get("status") != "NATIVE_MIT_SKIN_AXIS_DIAGNOSTIC_ONLY":
        raise Rejected("PROBE_STATUS_NOT_DIAGNOSTIC")
    if (doc.get("product_accepted") is not False or
        doc.get("original_naomi_alison_mvp") is not False or
        doc.get("signed_joint_coordinate_system") != "NOT_CALIBRATED" or
        doc.get("foot_contact") != "UNKNOWN" or
        doc.get("real_world_sagittal_basis") != "UNKNOWN"):
        raise Rejected("FORGED_HUMAN_CONTACT_PRODUCT_PROMOTION")
    owners=doc.get("rig_owners")
    if type(owners) is not dict or set(owners) != set(ROOTS):
        raise Rejected("NATIVE_RIG_OWNER_SET")
    if any(type(owners[k]) is not dict or owners[k].get("bone_count") != 80 for k in ROOTS):
        raise Rejected("NATIVE_80_BONE_NOT_PROVEN")
    rows=doc.get("axis_probes")
    if type(rows) is not list or len(rows) != 24:
        raise Rejected("INCOMPLETE_AXIS_PROBE_CARDINALITY")
    unique=set()
    max_displacement=0.0
    for row in rows:
        if type(row) is not dict:
            raise Rejected("MALFORMED_PROBE_ROW")
        key=(row.get("actor"),row.get("side"),row.get("joint"),row.get("local_axis"))
        if (key[0] not in ROOTS or key[1] not in ("L","R") or
            key[2] not in ("Thigh","Calf") or key[3] not in ("X","Y","Z") or key in unique):
            raise Rejected("FORGED_OR_DUPLICATE_SOURCE_AXIS")
        unique.add(key)
        if row.get("sampled_frame") != 36 or row.get("perturb_radians") != 0.35:
            raise Rejected("SOURCE_PROBE_PERTURBATION_MISMATCH")
        if type(row.get("sampled_source_skin_vertices")) is not int or row["sampled_source_skin_vertices"] < 12:
            raise Rejected("MISSING_REAL_WEIGHTED_SKIN_POPULATION")
        if row.get("human_sagittal_axis_certified") is not False:
            raise Rejected("FALSE_BIOMECHANICAL_AXIS_CLAIM")
        rest=row.get("source_rest_matrix3")
        if type(rest) is not list or len(rest)!=3 or any(type(a) is not list or len(a)!=3 or any(not finite(v) for v in a) for a in rest):
            raise Rejected("NATIVE_REST_MATRIX_NONFINITE")
        for field in ("baseline_foot_region_world_xyz","perturbed_foot_region_world_xyz","observed_skinned_world_displacement_xyz"):
            v=row.get(field)
            if type(v) is not list or len(v)!=3 or any(not finite(y) for y in v):
                raise Rejected("NATIVE_WORLD_WITNESS_NONFINITE:"+field)
        move=row.get("observed_displacement_m")
        if not finite(move) or move < 0:
            raise Rejected("INVALID_OBSERVED_NATIVE_MOTION")
        delta=row["observed_skinned_world_displacement_xyz"]
        if abs(math.sqrt(sum(x*x for x in delta))-move)>1.e-5:
            raise Rejected("FORGED_NATIVE_SKIN_DISPLACEMENT")
        max_displacement=max(max_displacement,move)
    if len(unique)!=24 or max_displacement<.003:
        raise Rejected("NONMOVING_SOURCE_SKIN_OR_DROPPED_AXIS")
    claimed=doc.get("max_actual_weighted_foot_motion_m")
    if not finite(claimed) or abs(claimed-max_displacement)>1.e-5:
        raise Rejected("FORGED_GLOBAL_NATIVE_MAX")
    if doc.get("native_source_skin_motion_observed") is not True:
        raise Rejected("MISSING_NATIVE_LIVENESS_WITNESS")
    return {"status":"AXIS_MATRIX_STRUCTURAL_ONLY","axis_rows":24,
            "source_original_mit":True,"physical_gait":"UNKNOWN","product_accepted":False}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--receipt",type=Path,required=True)
    args=p.parse_args()
    if args.receipt.is_symlink() or not args.receipt.is_file() or args.receipt.stat().st_size>1<<20:
        raise Rejected("NATIVE_RECEIPT_NOT_BOUNDED_REGULAR_FILE")
    raw=args.receipt.read_text(encoding="utf-8")
    doc=json.loads(raw,parse_constant=lambda s:(_ for _ in ()).throw(Rejected("NONFINITE_JSON")))
    print(json.dumps(check(doc),sort_keys=True))


if __name__=="__main__":
    main()
