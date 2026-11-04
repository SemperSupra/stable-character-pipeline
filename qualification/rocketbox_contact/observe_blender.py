#!/usr/bin/env python3
"""Source-pinned native Blender 72f skeletal/mesh witness, NOT contact/biomechanical admission."""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

EXPECTED_SOURCE = "2e5c5fcc826c95d200b06cc2dcd22138944102426a86f1f683689ae458aff7ab"
ROOTS = ("RB_RB_F01_root", "RB_RB_F02_root")
JOINTS = (
    "Bip01 L Thigh", "Bip01 L Calf", "Bip01 L Foot", "Bip01 L Toe0",
    "Bip01 R Thigh", "Bip01 R Calf", "Bip01 R Foot", "Bip01 R Toe0",
)
FPS = 12
FRAMES = 72

def fail(code):
    raise RuntimeError(code)

def finite(values):
    if not all(math.isfinite(float(v)) for v in values):
        fail("NONFINITE_NATIVE_OBSERVATION")

def coords(value):
    vals = [float(v) for v in value]
    finite(vals)
    return vals

def owner_descendant(obj, root):
    p = obj.parent
    while p is not None:
        if p is root:
            return True
        p = p.parent
    return False

def observe_actor(root, frame, ground_z, deps):
    arms = [o for o in bpy.data.objects
            if o.type == "ARMATURE" and owner_descendant(o, root)]
    if len(arms) != 1:
        fail("UNIQUE_OWNER_ARMATURE_REQUIRED:" + root.name)
    arm = arms[0]
    if len(arm.data.bones) != 80:
        fail("NATIVE_BONE_COUNT_NOT_80:" + root.name)
    skins = [o for o in bpy.data.objects if o.type == "MESH" and
             any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
    if len(skins) != 1:
        fail("UNIQUE_NATIVE_SKIN_REQUIRED:" + root.name)
    ev_arm = arm.evaluated_get(deps)
    bone_heads = {}
    bone_tails = {}
    for name in JOINTS:
        bone = ev_arm.pose.bones.get(name)
        if bone is None:
            fail("NATIVE_REQUIRED_BONE_MISSING:" + name)
        bone_heads[name] = coords(ev_arm.matrix_world @ bone.head)
        bone_tails[name] = coords(ev_arm.matrix_world @ bone.tail)
    ev_mesh = skins[0].evaluated_get(deps)
    evaluated = ev_mesh.to_mesh()
    vertex_count = len(evaluated.vertices) if evaluated else 0
    try:
        if vertex_count < 1000:
            fail("NATIVE_MESH_VERTICES_MISSING:" + root.name)
        zmin = float("inf")
        for vertex in evaluated.vertices:
            x, y, z = coords(ev_mesh.matrix_world @ vertex.co)
            zmin = min(zmin, z)
    finally:
        ev_mesh.to_mesh_clear()
    root_pos = coords(root.matrix_world.translation)
    feet = {}
    for side in ("L", "R"):
        hip = Vector(bone_heads["Bip01 " + side + " Thigh"])
        knee = Vector(bone_heads["Bip01 " + side + " Calf"])
        ankle = Vector(bone_heads["Bip01 " + side + " Foot"])
        upper = hip - knee
        lower = ankle - knee
        if upper.length <= 1e-7 or lower.length <= 1e-7:
            fail("DEGENERATE_NATIVE_LIMB:" + root.name + ":" + side)
        c = max(-1., min(1., upper.normalized().dot(lower.normalized())))
        angle = float(math.degrees(math.acos(c)))
        toe_head = bone_heads["Bip01 " + side + " Toe0"]
        toe_tail = bone_tails["Bip01 " + side + " Toe0"]
        feet[side] = {
            "toe_head_world_m": toe_head,
            "toe_tail_world_m": toe_tail,
            "toe_tail_height_above_ground_m": toe_tail[2] - ground_z,
            "knee_interior_angle_deg_unqualified": angle,
        }
    return {
        "root": root.name,
        "root_world_m": root_pos,
        "evaluated_mesh_min_z_m": zmin,
        "evaluated_mesh_min_clearance_m": zmin - ground_z,
        "feet": feet,
        "sampled_native_mesh_vertices": vertex_count,
    }

def main(source, outdir):
    source = Path(source).resolve()
    outdir = Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if digest != EXPECTED_SOURCE:
        fail("IMMUTABLE_BLEND_SOURCE_DIGEST_MISMATCH")
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    if (scene.frame_start, scene.frame_end, scene.render.fps) != (0, 71, FPS):
        fail("SOURCE_CLOCK_OR_FRAME_SCOPE_CHANGED")
    ground = bpy.data.objects.get("SourceProbeGround")
    if not ground:
        fail("SOURCE_GROUND_REFERENCE_MISSING")
    plane_z = max(float((ground.matrix_world @ Vector(c)).z) for c in ground.bound_box)
    finite((plane_z,))
    roots = []
    for name in ROOTS:
        root = bpy.data.objects.get(name)
        if not root:
            fail("FROZEN_NATIVE_ROOT_MISSING:" + name)
        roots.append(root)
    observations = []
    for f in range(FRAMES):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        actors = [observe_actor(root, f, plane_z, deps) for root in roots]
        observations.append({"frame": f, "actors": actors})
    separation = [abs(r["actors"][0]["root_world_m"][0] -
                      r["actors"][1]["root_world_m"][0]) for r in observations]
    if separation[0] - separation[-1] < 1.0:
        fail("ROOT_APPROACH_NOT_SUPPORTED_BY_NATIVE_SCENE")
    proximity = {}
    for actor_idx, name in enumerate(ROOTS):
        proximity[name] = {}
        for side in ("L", "R"):
            near = 0
            suspect = 0
            max_step = 0.0
            for i in range(FRAMES - 1):
                a = observations[i]["actors"][actor_idx]["feet"][side]
                b = observations[i+1]["actors"][actor_idx]["feet"][side]
                aheight = a["toe_tail_height_above_ground_m"]
                bheight = b["toe_tail_height_above_ground_m"]
                if -0.04 <= aheight <= 0.065 and -0.04 <= bheight <= 0.065:
                    near += 1
                    start = a["toe_tail_world_m"]
                    finish = b["toe_tail_world_m"]
                    displacement = math.hypot(finish[0] - start[0],
                                              finish[1] - start[1])
                    max_step = max(max_step, displacement)
                    if displacement > 0.04:
                        suspect += 1
            proximity[name][side] = {
                "near_ground_consecutive_frame_pairs_proxy_only": near,
                "proxy_slide_gt_4cm_pairs": suspect,
                "maximum_proxy_horizontal_step_m": max_step,
            }
    receipt = {
        "schema": "scp.mit_native_all72_foot_mesh_proxy.v1",
        "status": "NATIVE_OBSERVED_72F_FOOT_AND_SKIN_ONLY",
        "source_zip_sha256": "2bbf1036744e4fcd614cd207bc9e9eb2147b943f59c53d9de7dff1b324320204",
        "source_blend_sha256": digest,
        "source_mit": "WITH_NOTICE",
        "source_names": list(ROOTS),
        "frame_count": FRAMES,
        "fps": FPS,
        "ground_surface_z_m": plane_z,
        "root_separation_start_end_m": [separation[0], separation[-1]],
        "toe_ground_proximity_heuristics": proximity,
        "observations": observations,
        "foot_contact_accepted": False,
        "joint_coordinate_system_calibrated": False,
        "normative_biomechanics_accepted": False,
        "human_gait": "UNKNOWN",
        "product_accepted": False,
    }
    target = outdir / "native_all72_foot_proxy_receipt.json"
    target.write_text(json.dumps(receipt, sort_keys=True, indent=2) + chr(10), encoding="utf-8")
    print(json.dumps({"status": receipt["status"],
                      "native_frames": len(observations),
                      "separation": receipt["root_separation_start_end_m"],
                      "toe_proximity": proximity,
                      "foot_contact_accepted": False}, sort_keys=True))

if __name__ == "__main__":
    if "--" not in sys.argv:
        fail("BLENDER_SCRIPT_ARGS_REQUIRED")
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) != 2:
        fail("USAGE_SOURCE_BLEND_AND_OUTPUT_DIRECTORY")
    main(args[0], args[1])
