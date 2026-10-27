#!/usr/bin/env python3
"""G3: real Blender MMD Tools VMD motion and VPD pose import, tested independently."""
import argparse
import json
import os
from pathlib import Path
import sys

def main():
    parser = argparse.ArgumentParser()
    for field in ("source", "model", "motion", "pose", "out"):
        parser.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    import bpy
    from mathutils import Vector
    assert bpy.app.version >= (4, 2, 0), bpy.app.version
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sys.path.insert(0, str(args.source.resolve()))
    import mmd_tools
    mmd_tools.register()
    result = bpy.ops.mmd_tools.import_model(filepath=str(args.model.resolve()),
      types={"MESH", "ARMATURE"}, scale=1.0, rename_bones=False, fix_bone_order=False)
    assert "FINISHED" in result, "PMX import failed"
    rigs = [obj for obj in bpy.data.objects if obj.type == "ARMATURE"]
    assert len(rigs) == 1, f"Unexpected armatures: {len(rigs)}"
    rig = rigs[0]
    bone = rig.pose.bones.get("センター")
    assert bone is not None, "Imported rig lost source MMD Japanese bone name"
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    result = bpy.ops.mmd_tools.import_vmd(filepath=str(args.motion.resolve()),
      scale=1.0, margin=0, bone_mapper="PMX", update_scene_settings=False)
    assert "FINISHED" in result, "MMD Tools VMD operator failed"
    samples = {}
    for frame in (0, 15, 30):
        bpy.context.scene.frame_set(frame)
        samples[str(frame)] = [float(v) for v in bone.location]
    displacement = (Vector(samples["30"]) - Vector(samples["0"])).length
    assert displacement > .1, f"VMD motion did not deform bone at frame 30: {samples}"
    result = bpy.ops.mmd_tools.import_vpd(
      directory=str(args.pose.resolve().parent) + os.sep,
      files=[{"name": args.pose.name}],
      scale=1.0, bone_mapper="PMX", use_pose_mode=False)
    assert "FINISHED" in result, "MMD Tools VPD operator failed"
    pose_after_import = [float(v) for v in bone.location]
    bpy.ops.wm.save_as_mainfile(filepath=str((args.out / "mmd_native_motion_pose.blend").resolve()))
    assert (args.out / "mmd_native_motion_pose.blend").stat().st_size > 1000
    report = {
      "schema": "scp.mmd.motion.v1",
      "status": "PASS_NATIVE_VMD_AND_VPD_OPERATORS",
      "upstream": "MMD Tools v4.5.14",
      "blender": bpy.app.version_string,
      "rig": rig.name,
      "bone": bone.name,
      "sample_frame_positions": samples,
      "displacement_blender_units": displacement,
      "vpd_position_after_import": pose_after_import,
      "scope": "MMD VMD armature translation playback and VPD operator; does not qualify source-retarget IK, physical stability or non-synthetic dance"
    }
    (args.out / "motion_receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True), flush=True)

if __name__ == "__main__":
    main()
    # Embedded Blender's Python shutdown hung after success on G2 run 40423130061.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
