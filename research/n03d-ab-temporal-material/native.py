"""N03D-AB: read-only temporal five-link IK trial on real pinned CC0 shoe mesh.

No writes to the source action/scene, no contact-phase inference or released motion.
Bounded 4x24Hz source-anchored candidate per shoe/window, independently replayed
at 9 subframe times (60Hz plus exact 24Hz endpoint).
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from policy import assess
sys.path.insert(0, str(HERE.parent / "n03d-y-material"))
from material import select_ids, snapshot
sys.path.insert(0, str(HERE.parent / "n03d-x-sole-jacobian"))
from jacobian import jacobian, update
sys.path.insert(0, str(HERE.parent / "r090-dressed"))
from measure import stable_sole_sample


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seek(t):
    frame = int(math.floor(t * 12 + 1e-8))
    bpy.context.scene.frame_set(frame, subframe=t * 12 - frame)
    bpy.context.view_layer.update()


def world(shoe):
    deps = bpy.context.evaluated_depsgraph_get()
    evaluated = shoe.evaluated_get(deps)
    mesh = evaluated.to_mesh()
    try:
        require(len(mesh.vertices) == len(shoe.data.vertices), "MESH_TOPOLOGY_CHANGED")
        return [tuple(float(v) for v in (evaluated.matrix_world @ vertex.co)) for vertex in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def indices(shoe, part):
    xs = [float(v.co.x) for v in shoe.data.vertices]
    split = (min(xs) + max(xs)) / 2
    return [i for i, x in enumerate(xs) if ((x < split) == (part == "rest_local_x_negative"))]


def geometry(mesh, ids, half):
    s = snapshot(mesh, ids)
    return [s["centroid_xyz_m"][0], s["centroid_xyz_m"][1], s["min_z_m"]], min(mesh[i][2] for i in half)


def rotation(rig, chain):
    evaluated = rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return {n: evaluated.pose.bones[n].matrix.to_quaternion().copy() for n in chain}


def bound_angle(baseline, other):
    # q and -q encode the same physical orientation. Raw quaternion angle
    # can be 2*pi for a sign flip; do not mistake that for a joint rotation.
    angles = []
    for k in baseline:
        qa, qb = baseline[k], other[k]
        na = math.sqrt(sum(qa[i]*qa[i] for i in range(4)))
        nb = math.sqrt(sum(qb[i]*qb[i] for i in range(4)))
        require(na > 1e-12 and nb > 1e-12, "INVALID_POSE_QUATERNION")
        dot = abs(sum(qa[i]*qb[i] for i in range(4)) / (na*nb))
        angles.append(2*math.acos(min(1.0, max(0.0, dot))))
    return max(angles)


def observed(t, xyz, min_z, delta, angle, gap):
    return {"time_s": t, "xy_m": [xyz[0], xyz[1]], "min_z_m": min_z,
            "ik_delta_m": float(delta.length), "max_joint_pose_rotation_rad": float(angle),
            "nonlinear_gap_m": float(gap)}


def start_context(frame):
    # Preserve the R090 sequential source-scene time evaluation convention.
    for i in range(frame + 1):
        seek(i / 24.0)


def replay(start, rate, rig, shoe, foot, chain, ik, target, ids, half, deltas, gaps):
    src, dst = [], []
    local_times = [j / rate for j in range(4 if rate == 24 else 8)]
    if rate == 60:
        local_times.append(3 / 24)
    for x in local_times:
        t = start / 24 + x
        ik.influence = 0.0
        seek(t)
        source_mesh = world(shoe)
        first, pz = geometry(source_mesh, ids, half)
        root_tail = (rig.matrix_world @ foot.tail).copy()
        original_pose = rotation(rig, chain)
        src.append(observed(t, first, pz, Vector((0, 0, 0)), 0., 0.))
        q = max(0., min(3., x * 24))
        lower = min(2, int(math.floor(q)))
        frac = q - lower
        d = deltas[lower] * (1 - frac) + deltas[lower + 1] * frac
        ik.influence = 1.0
        target.location = root_tail + d
        bpy.context.view_layer.update()
        after_mesh = world(shoe)
        after, az = geometry(after_mesh, ids, half)
        joint = bound_angle(original_pose, rotation(rig, chain))
        conservative_gap = max(gaps[lower], gaps[lower + 1])
        dst.append(observed(t, after, az, d, joint, conservative_gap))
    return src, dst


def main():
    parser = argparse.ArgumentParser()
    for name in ("scene", "sha", "wardrobe", "retarget", "trace", "correspondence", "out"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    require(sha(args.scene) == args.sha, "SOURCE_SCENE_SHA")
    scene = bpy.context.scene
    require(scene.get("r078_source") == "ORIGINAL_FICTIONAL_MPFBCORE_CC0"
            and scene.get("r082_wardrobe") == "CC0_EXACT_ASSET_PROCEDURAL_MATERIAL",
            "PROTECTED_OR_UNKNOWN_ASSET")
    require((scene.frame_start, scene.frame_end, scene.render.fps) == (0, 71, 12),
            "SCENE_TIMEBASE_DRIFT")
    wardrobe = json.loads(Path(args.wardrobe).read_text())
    retarget = json.loads(Path(args.retarget).read_text())
    trace = json.loads(Path(args.trace).read_text())
    corr = json.loads(Path(args.correspondence).read_text())
    require(retarget.get("candidate_blend_sha256") == args.sha
            and retarget.get("input_scene_sha256") == wardrobe.get("blend_sha256"),
            "RETARGET_WARDROBE_JOIN")
    require(trace.get("source_scene_sha256") == args.sha
            and corr.get("source_scene_sha256") == args.sha
            and corr.get("source_trace_sha256") == sha(args.trace), "PROVENANCE_JOIN")
    require(trace.get("schema") == "scp.n03d-g.evaluated-foot-contact-observer.v1"
            and trace.get("frame_rate_hz") == 24
            and trace.get("sample_count_per_side") == 143, "NATIVE_SOURCE_CLOCK")
    require(len(trace["actors"]) == 2 and
            sorted(row["actor"] for row in trace["actors"]) == ["AsterOriginal", "JuniperOriginal"],
            "SOURCE_ACTORS")
    windows = []
    for actor in trace["actors"]:
        name = actor["actor"]
        rig = bpy.data.objects.get(name + "_MPFBRig")
        require(rig is not None and len(rig.data.bones) == 163, "REAL_163BONE_RIG")
        owner = next(row for row in wardrobe["characters"] if row["name"] == name)
        matches = [row for row in owner["garments"] if row["pack"] == "shoes01"]
        require(len(matches) == 1, "CC0_SHOE_MISSING")
        shoe = bpy.data.objects.get(matches[0]["native_object"])
        require(shoe is not None and any(m.type == "ARMATURE" and m.object == rig for m in shoe.modifiers),
                "SHOE_NOT_SKINNED")
        c = next(row for row in corr["actors"] if row["actor"] == name)
        for part in c["partitions"]:
            actual = "R" if part["rest_local_partition"] == "rest_local_x_negative" else "L"
            require(part["candidate_rig_side"]["label"] == actual
                    and part["candidate_rig_side"]["dominance"] > .95, "SHOE_SIDE_NOT_QUALIFIED")
        for start in (24, 48):
            for side, part in (("L", "rest_local_x_positive"), ("R", "rest_local_x_negative")):
                start_context(start)
                half = indices(shoe, part)
                ids = select_ids(world(shoe), half)
                anchor = geometry(world(shoe), ids, half)[0]
                foot = rig.pose.bones["foot." + side]
                chain = [n + "." + side for n in
                         ("foot", "lowerleg02", "lowerleg01", "upperleg02", "upperleg01")]
                require(all(rig.data.bones[chain[j]].parent.name == chain[j+1] for j in range(4)),
                        "NATIVE_LEG_CHAIN")
                target = bpy.data.objects.new("N03D_AB_ephemeral_" + name + side, None)
                scene.collection.objects.link(target)
                ik = foot.constraints.new("IK")
                ik.target = target
                ik.chain_count = 5
                ik.iterations = 100
                ik.use_stretch = False
                ik.use_rotation = False
                ik.use_location = True
                try:
                    corrections, gaps = [], []
                    for i in range(start, start + 4):
                        t = i / 24.
                        ik.influence = 0.
                        seek(t)
                        baseline_mesh = world(shoe)
                        src, z = geometry(baseline_mesh, ids, half)
                        dynamic = stable_sole_sample(shoe)[part]
                        trace_row = actor["sides"][part]["samples"][i]
                        source_dynamic = (trace_row["xy_m"][0], trace_row["xy_m"][1], trace_row["z_m"])
                        require(math.dist((dynamic["xy_m"][0], dynamic["xy_m"][1], dynamic["z_m"]),
                                          source_dynamic) < .0005, "SOURCE_NULL_24HZ_DRIFT")
                        tail = (rig.matrix_world @ foot.tail).copy()
                        ik.influence = 1.
                        target.location = tail
                        bpy.context.view_layer.update()
                        base = geometry(world(shoe), ids, half)[0]
                        plus, minus = [], []
                        step = .002
                        for axis in range(3):
                            delta = Vector(tuple(step if k == axis else 0. for k in range(3)))
                            target.location = tail + delta
                            bpy.context.view_layer.update()
                            plus.append(geometry(world(shoe), ids, half)[0])
                            target.location = tail - delta
                            bpy.context.view_layer.update()
                            minus.append(geometry(world(shoe), ids, half)[0])
                        j = jacobian(plus, minus, step)
                        residual = [base[0] - anchor[0], base[1] - anchor[1], base[2]]
                        update_row = update(j, residual, .1, .010)
                        d = Vector(update_row["target_delta_m"])
                        target.location = tail + d
                        bpy.context.view_layer.update()
                        realized = geometry(world(shoe), ids, half)[0]
                        predicted = [base[k] + sum(j[k][axis] * d[axis] for axis in range(3))
                                     for k in range(3)]
                        gap = math.dist(realized, predicted)
                        require(math.isfinite(gap) and d.length <= .010001, "IK_TRIAL_INVALID")
                        corrections.append(d.copy())
                        gaps.append(gap)
                    source24, candidate24 = replay(start, 24, rig, shoe, foot, chain, ik,
                                                   target, ids, half, corrections, gaps)
                    source60, candidate60 = replay(start, 60, rig, shoe, foot, chain, ik,
                                                   target, ids, half, corrections, gaps)
                    windows.append({"actor": name, "side": side, "mesh_part": part,
                                    "start_sample_24hz": start,
                                    "persistent_vertex_count": len(ids),
                                    "persistent_vertex_ids": ids,
                                    "source_24": source24, "candidate_24": candidate24,
                                    "source_60": source60, "candidate_60": candidate60})
                finally:
                    foot.constraints.remove(ik)
                    bpy.data.objects.remove(target, do_unlink=True)
                    bpy.context.view_layer.update()
    report = {
        "schema": "scp.n03d-ab.native-material-temporal-ik.v1",
        "source_class": "ORIGINAL_FICTIONAL_CC0",
        "source_scene_sha256": args.sha,
        "source_trace_sha256": sha(args.trace),
        "source_100style_sha256": trace["source_100style_sha256"],
        "blender_version": bpy.app.version_string,
        "source_motion_changed": False, "corrected_blend_saved": False,
        "source_stance_unverified": True, "contact_material_cohort_fixed_per_window": True,
        "sixty_hz_gap_is_conservative_adjacent_24hz_bound": True,
        "five_link_ik_without_root_correction": True,
        "original_CC0_shoe_side_min_z_evaluated": True,
        "physical_contact_accepted": False, "mvp_accepted": False,
        "windows": windows
    }
    # Preserve exact original native witness even if independent critic REDs.
    Path(args.out).write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False)+"\n")
    critic = assess(report)
    Path(args.out).with_name("n03d-ab-independent-critic.json").write_text(
        json.dumps(critic, sort_keys=True, indent=2, allow_nan=False)+"\n")
    print("N03D_AB_ACTUAL_NATIVE_TEMPORAL_WITNESS",
          json.dumps({"window_count": len(windows), "critic_status": critic["status"],
                      "conclusions": [{"actor": row["actor"], "side": row["side"],
                                       "start": row["start_sample_24hz"],
                                       "source_60": row["source_60"],
                                       "candidate_60": row["candidate_60"],
                                       "reasons": row["reasons"]}
                                      for row in critic["windows"]]}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
