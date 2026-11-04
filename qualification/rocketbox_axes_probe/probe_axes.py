"""Read-only source-native bone rest-axis perturbation experiment.

Purpose: diagnose visually rigid V1/V2 gait on the original immutable MIT
80-bone Blender scene. Reports actual native skinned foot-region displacement.
Never certifies biomechanical axes, physical contact, identity or product.
"""
from __future__ import annotations
import hashlib
import json
import math
import sys
from pathlib import Path

SOURCE_SHA = "2e5c5fcc826c95d200b06cc2dcd22138944102426a86f1f683689ae458aff7ab"
SCHEMA = "scp.r009.original_mit_native_rig_axis_probe.v1"
ROOTS = ("RB_RB_F01_root", "RB_RB_F02_root")
DELTA_RAD = 0.35


def source_sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1<<20), b""):
            h.update(data)
    return h.hexdigest()


def owner_armature(bpy, rootname):
    root = bpy.data.objects.get(rootname)
    if root is None:
        raise RuntimeError("PINNED_NATIVE_ROOT_MISSING:" + rootname)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE" and
            (o.parent == root or (o.parent is not None and o.parent.parent == root))]
    if len(arms) != 1 or len(arms[0].data.bones) != 80:
        raise RuntimeError("PINNED_NATIVE_80_BONE_OWNER_MISMATCH:" + rootname)
    return arms[0]


def skinned_source_mesh_selection(bpy, arm, side):
    foot_ids = ("Bip01 "+side+" Foot", "Bip01 "+side+" Toe0")
    selections = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not any(
            mod.type == "ARMATURE" and mod.object == arm for mod in ob.modifiers
        ):
            continue
        groups = [ob.vertex_groups.get(name) for name in foot_ids]
        if any(g is None for g in groups):
            continue
        group_ids = {g.index for g in groups}
        selected = []
        for vertex in ob.data.vertices:
            weighted = sum(link.weight for link in vertex.groups
                           if link.group in group_ids)
            if weighted >= .50:
                selected.append(vertex.index)
        if selected:
            selections.append((ob, selected))
    if sum(len(ids) for _, ids in selections) < 12:
        raise RuntimeError("ACTUAL_SKIN_WEIGHTED_FOOT_REGION_UNAVAILABLE:" + side)
    return selections


def observed_skin_centroid_world(bpy, selections):
    deps = bpy.context.evaluated_depsgraph_get()
    sx = sy = sz = 0.0
    n = 0
    for ob, indices in selections:
        evaluated = ob.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        try:
            if len(mesh.vertices) != len(ob.data.vertices):
                raise RuntimeError("NATIVE_EVALUATED_VERTEX_ORDER_CHANGED")
            mat = evaluated.matrix_world
            for idx in indices:
                v = mat @ mesh.vertices[idx].co
                sx += float(v.x); sy += float(v.y); sz += float(v.z)
                n += 1
        finally:
            evaluated.to_mesh_clear()
    if n < 12:
        raise RuntimeError("NATIVE_WEIGHTED_SAMPLE_EMPTY")
    vals = [sx/n, sy/n, sz/n]
    if not all(math.isfinite(v) for v in vals):
        raise RuntimeError("NATIVE_SKIN_CENTROID_NONFINITE")
    return vals, n


def vec_diff(after, before):
    return [round(a-b, 7) for a,b in zip(after,before)]


def run(source, dest):
    import bpy

    if source_sha(source) != SOURCE_SHA:
        raise RuntimeError("FROZEN_NATIVE_SOURCE_BLOB_MISMATCH")
    dest.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    if (scene.frame_start, scene.frame_end, scene.render.fps) != (0, 71, 12):
        raise RuntimeError("SOURCE_NATIVE_CLOCK_NOT_72F_12FPS")
    scene.frame_set(36)
    bpy.context.view_layer.update()
    rows = []
    records = {}
    for rootname in ROOTS:
        arm = owner_armature(bpy, rootname)
        records[rootname] = {"armature": arm.name, "bone_count": len(arm.data.bones)}
        for side in ("L", "R"):
            selections = skinned_source_mesh_selection(bpy, arm, side)
            baseline, count = observed_skin_centroid_world(bpy, selections)
            for joint in ("Thigh", "Calf"):
                bone_name = "Bip01 "+side+" "+joint
                bone = arm.pose.bones.get(bone_name)
                if bone is None:
                    raise RuntimeError("SOURCE_NATIVE_PROBE_BONE_MISSING:" + bone_name)
                if bone.rotation_mode != "XYZ":
                    raise RuntimeError("SOURCE_NATIVE_ROTATION_MODE_UNEXPECTED:" + bone_name)
                rest = [list(row) for row in bone.bone.matrix_local.to_3x3()]
                original = bone.rotation_euler.copy()
                for axis in range(3):
                    try:
                        bone.rotation_euler[axis] = original[axis] + DELTA_RAD
                        bpy.context.view_layer.update()
                        perturbed, observed = observed_skin_centroid_world(bpy, selections)
                    finally:
                        bone.rotation_euler = original.copy()
                        bpy.context.view_layer.update()
                    difference = vec_diff(perturbed, baseline)
                    rows.append({
                        "actor": rootname, "side": side, "joint": joint,
                        "local_axis": "XYZ"[axis], "sampled_frame": 36,
                        "perturb_radians": DELTA_RAD, "sampled_source_skin_vertices": count,
                        "source_rest_matrix3": rest,
                        "baseline_foot_region_world_xyz": baseline,
                        "perturbed_foot_region_world_xyz": perturbed,
                        "observed_skinned_world_displacement_xyz": difference,
                        "observed_displacement_m": round(math.sqrt(sum(v*v for v in difference)),7),
                        "human_sagittal_axis_certified": False,
                    })
    if len(rows) != 24:
        raise RuntimeError("SOURCE_NATIVE_AXIS_MATRIX_INCOMPLETE")
    max_observed = max(r["observed_displacement_m"] for r in rows)
    if max_observed < .003:
        raise RuntimeError("RIG_AXIS_PERTURBATIONS_HAVE_NO_REAL_SKIN_EFFECT")
    report = {
        "schema": SCHEMA, "status": "NATIVE_MIT_SKIN_AXIS_DIAGNOSTIC_ONLY",
        "source_blend_sha256": SOURCE_SHA, "frame": 36, "fps": 12,
        "rig_owners": records, "axis_probes": rows, "source_bones": "ORIGINAL_MIT_80_BONES",
        "method": "plus_0.35rad_actual_blender_pose_then_evaluated_weighted_foot_skin",
        "max_actual_weighted_foot_motion_m": max_observed,
        "native_source_skin_motion_observed": True,
        "signed_joint_coordinate_system": "NOT_CALIBRATED",
        "real_world_sagittal_basis": "UNKNOWN", "foot_contact": "UNKNOWN",
        "physical_sole_or_force_plate": "NOT_RUN",
        "original_naomi_alison_mvp": False, "product_accepted": False,
    }
    (dest/"native_rest_axis_skin_diagnostic.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False)+"\n")
    print(json.dumps({"status":report["status"],"rows":len(rows),
       "max_native_skin_motion_m":max_observed,"product_accepted":False}))


if __name__ == "__main__":
    if "--" not in sys.argv:
        raise RuntimeError("ARGS_REQUIRED")
    args = sys.argv[sys.argv.index("--")+1:]
    if len(args) != 2:
        raise RuntimeError("USAGE PINNED_SOURCE_BLEND OUTPUT_DIR")
    run(*(Path(v).resolve() for v in args))
