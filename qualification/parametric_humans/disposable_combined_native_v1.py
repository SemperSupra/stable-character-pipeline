#!/usr/bin/env python3
"""Original-synthetic native witness for a source-combined, disposable R009 worktree.

Runs only after disposable_parent_integration_trial.py has pinned the public
#308 parent source and #336 child workcell. Invoked explicitly in a public CPU
runner with Blender 4.5.15. Does not mutate remote Git and never authorizes
biology/identity/rights/merge/release/CPE acceptance.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys

SCHEMA = "scp.r009.disposable_combined_native.v1"
ACTORS = ("AsterOriginal", "JuniperOriginal")
SLOTS = ("top", "bottom", "footwear")
FRAMES = list(range(0, 143, 2))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def run(args, *, cwd):
    p = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if p.returncode:
        raise RuntimeError("COMBINED_NATIVE_COMMAND_FAILED: " + repr(args[:4]) +
                           " exit=" + str(p.returncode) + " stderr=" + p.stderr[-1600:] +
                           " stdout=" + p.stdout[-1000:])
    print("COMBINED_NATIVE_COMMAND_PASS", args[0], args[1:4])


def validate_native_receipts(folder):
    """Independent exact-source shape/byte and diagnostic hold verification.

    A positive native receipt is NOT accepted without full 72 sampled BVH and
    garment-proximity evidence and eight actually hashed camera PNG witnesses.
    """
    folder = Path(folder)
    summaries = {}
    for state in ("before", "after"):
        native_path = folder / (state + "_native_blender.json")
        require(native_path.is_file(), "NATIVE_RECEIPT_MISSING:" + state)
        native = json.loads(native_path.read_text(encoding="utf-8"))
        require(native.get("native_import_render_technical_pass") is True,
                "NATIVE_IMPORT_NOT_PASSED:" + state)
        require(native.get("per_actor_per_eye_materials_confirmed") is True,
                "IRIS_MATERIALS_NOT_PASSED:" + state)
        require(native.get("imported_armatures", 0) >= 2 and
                native.get("imported_meshes", 0) >= 8,
                "ACTOR_MESH_OR_ARMATURE_MISSING:" + state)
        require(native.get("human_visual_accepted") is False and
                native.get("release_approved") is False,
                "ILLEGAL_NATIVE_SCIENCE_PROMOTION:" + state)
        require(native.get("native_diagnostic_camera") ==
                "BLENDER_Z_UP_ACTOR_SPECIFIC_WORLD_X_FRONT",
                "CAMERA_FRAME_UNKNOWN:" + state)
        require(native.get("closeups_generated") is True,
                "NATIVE_CLOSEUPS_MISSING:" + state)
        bvh_path = folder / (state + "_surface_bvh.json")
        near_path = folder / (state + "_garment_proximity.json")
        require(bvh_path.is_file() and near_path.is_file(),
                "SURFACE_OR_PROXIMITY_RECEIPT_MISSING:" + state)
        require(native.get("bvh_surface_receipt_sha256") == sha256(bvh_path),
                "BVH_RECEIPT_SHA_MISMATCH:" + state)
        require(native.get("garment_proxy_receipt_sha256") == sha256(near_path),
                "GAP_RECEIPT_SHA_MISMATCH:" + state)
        bvh = json.loads(bvh_path.read_text(encoding="utf-8"))
        gap = json.loads(near_path.read_text(encoding="utf-8"))
        require(bvh.get("schema") == "scp.r009.original_bvh_surface_contact.v2",
                "COMBINED_PARENT_BVH_V2_SCHEMA_REQUIRED:" + state)
        require(bvh.get("motion_frames_evaluated") == 72 and
                bvh.get("frame_indices") == FRAMES and
                bvh.get("all_72_motion_frames_evaluated_for_bvh") is True,
                "BVH_ALL_72_FRAMES_REQUIRED:" + state)
        require(bvh.get("native_bvh_positive_negative_calibration") is True,
                "BVH_CALIBRATION_MISSING:" + state)
        require(bvh.get("collision_free_proven") is False and
                bvh.get("garment_fit_accepted") is False and
                bvh.get("human_visual_accepted") is False and
                bvh.get("release_approved") is False,
                "BVH_SCIENTIFIC_GATE_FORGED:" + state)
        require(bvh.get("actor_count") == 2 and bvh.get("slots") == list(SLOTS),
                "BVH_ACTOR_OR_SLOT_DRIFT:" + state)
        require(gap.get("motion_frames_evaluated") == 72 and
                gap.get("frame_indices") == FRAMES and
                gap.get("actor_count") == 2 and
                gap.get("collision_qualified") is False,
                "PROXIMITY_MUST_BE_DIAGNOSTIC_72F:" + state)
        counts = {}
        require(set(bvh.get("per_actor_slot", {})) == set(ACTORS),
                "BVH_MISSING_ACTOR:" + state)
        for actor in ACTORS:
            slots = bvh["per_actor_slot"][actor]
            require(set(slots) == set(SLOTS), "BVH_MISSING_SLOT:" + state + actor)
            counts[actor] = {}
            for slot in SLOTS:
                record = slots[slot]
                samples = record.get("samples", [])
                require(record.get("sample_count") == 72 and len(samples) == 72 and
                        [r.get("frame") for r in samples] == FRAMES,
                        "BVH_SAMPLED_FRAMES_FORGED:" + actor + ":" + slot)
                total = sum(r.get("surface_overlap_triangle_pairs", -1) for r in samples)
                require(all(isinstance(r.get("surface_overlap_triangle_pairs"), int) and
                            not isinstance(r.get("surface_overlap_triangle_pairs"), bool) and
                            r["surface_overlap_triangle_pairs"] >= 0 and
                            r.get("collision_free_proven") is False for r in samples),
                        "BVH_PAIRS_OR_PER_SAMPLE_HOLD_INVALID:" + actor + ":" + slot)
                require(record.get("pairs_total") == total and
                        record.get("frames_with_surface_overlaps") ==
                        sum(r["surface_overlap_triangle_pairs"] > 0 for r in samples),
                        "BVH_METRICS_NOT_RECOMPUTABLE:" + actor + ":" + slot)
                counts[actor][slot] = total
        images = native.get("generated_renders", [])
        require(len(images) == 8, "EXPECTED_EIGHT_NATIVE_IMAGES:" + state)
        seen = set()
        for image in images:
            file = image.get("file", "")
            require(isinstance(file, str) and file and Path(file).name == file,
                    "UNSAFE_RENDER_PATH:" + state)
            key = (image.get("frame"), image.get("view"), file)
            require(key not in seen, "DUPLICATE_RENDER_WITNESS:" + state)
            seen.add(key)
            p = folder / file
            require(p.is_file() and p.stat().st_size > 2000,
                    "NATIVE_PNG_MISSING_OR_TINY:" + file)
            raw = p.read_bytes()
            require(raw[:8] == b"\x89PNG\r\n\x1a\n" and
                    struct.unpack(">II", raw[16:24]) == (720, 480) and
                    image.get("sha256") == hashlib.sha256(raw).hexdigest(),
                    "PNG_BYTE_OR_DIMENSION_MISMATCH:" + file)
        summaries[state] = {
            "source_sha256": native.get("source_sha256"),
            "bvh_sha256": sha256(bvh_path),
            "gap_sha256": sha256(near_path),
            "render_sha256": {i["file"]: i["sha256"] for i in images},
            "triangle_surface_overlap_pairs_by_actor_slot": counts,
            "frames_bvh_evaluated": 72,
            "native_views_verified": 8,
        }
    require(summaries["before"]["source_sha256"] !=
            summaries["after"]["source_sha256"],
            "BEFORE_AFTER_SOURCE_MUST_DIFFER")
    return {"schema": SCHEMA,
            "native_blender_72_frame_v2_receipts_checked": True,
            "states": summaries,
            "blender_native_states": 2,
            "per_state_bvh_actor_slot_samples": 432,
            "total_native_diagnostic_views": 16,
            "real_photo_fit": "NOT_RUN",
            "scientific_anatomy": "UNKNOWN",
            "garment_fit_accepted": False,
            "visual_realism_accepted": False,
            "merge_release_CPE_approval": False}


def execute(source_worktree, folder, blender):
    """Build two historical original-only source states and run actual Blender."""
    source_worktree = Path(source_worktree).resolve()
    folder = Path(folder).resolve()
    blender = Path(blender).resolve()
    require(blender.is_file() and os.access(blender, os.X_OK),
            "BLENDER_4_5_15_PINNED_BINARY_REQUIRED")
    require(not folder.exists(), "REFUSE_OVERWRITE_NATIVE_EVIDENCE")
    folder.mkdir(parents=True)
    code = source_worktree / "qualification/parametric_humans"
    require(code.is_dir(), "ORIGINAL_PARAMETRIC_SOURCE_MISSING")
    sys.path.insert(0, str(code))
    try:
        from parameters_v1 import sample, add_event, canonical_bytes
        a = sample(73, "AsterSynthetic")
        a = add_event(a, "2026-05-01", "procedure", "hypothesis", {
            "morphology.left_breast_volume": .75,
            "morphology.right_breast_volume": .72,
            "morphology.jaw_width_ratio": 1.09,
            "morphology.lip_fullness": .78})
        a = add_event(a, "2026-05-15", "styling", "artist_authored", {
            "appearance.hair_rgb": [.14, .25, .61],
            "appearance.left_iris_rgb": [.09, .58, .42],
            "appearance.skin_melanin": .66})
        j = sample(74, "JuniperSynthetic")
    finally:
        sys.path.remove(str(code))
    a_path, j_path = folder / "aster.json", folder / "juniper.json"
    a_path.write_bytes(canonical_bytes(a))
    j_path.write_bytes(canonical_bytes(j))
    for state, date in (("before", "2026-04-01"), ("after", "2026-06-01")):
        geom = folder / (state + ".geometry.glb")
        appearance = folder / (state + ".appearance.glb")
        run([sys.executable, "morph_preview_35_v1.py", "--aster", str(a_path),
             "--juniper", str(j_path), "--as-of", date,
             "--out", str(geom), "--manifest", str(folder / (state + ".geometry_manifest.json")),
             "--receipt", str(folder / (state + ".geometry_receipt.json"))], cwd=code)
        run([sys.executable, "appearance_material_v1.py", "--input", str(geom),
             "--aster", str(a_path), "--juniper", str(j_path), "--as-of", date,
             "--out", str(appearance),
             "--receipt", str(folder / (state + ".appearance_receipt.json"))], cwd=code)
        run(["xvfb-run", "-a", "-s", "-screen 0 1280x720x24", "env",
             "LIBGL_ALWAYS_SOFTWARE=1", str(blender), "-b", "--factory-startup",
             "--python-exit-code", "9", "--python", str(code / "native_blender_observer_v1.py"),
             "--", "--input", str(appearance), "--out-dir", str(folder), "--label", state],
            cwd=source_worktree)
    return validate_native_receipts(folder)
