"""Independent source-observation adapter for the W16-C2 original synthetic .blend.

Uses native Blender evaluated bones, not the source's IK target claims. Static
synthetic poles below are *authored test references*, NOT human anatomical truth.
"""
import argparse
import hashlib
import json
from pathlib import Path
import bpy

NAMES = ("CobaltOriginal", "MarigoldOriginal")
FRAMES = (0, 12, 24, 36, 48, 60, 71)
LEGS = (("Left", -1), ("Right", 1))


def extract(blend, output):
    blend = Path(blend)
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    specs = []
    for name in NAMES:
        arm = bpy.data.objects.get(name + "_Skeleton")
        if arm is None or arm.type != "ARMATURE":
            raise ValueError("SOURCE_ARMATURE_NOT_PRESENT")
        for leg, sign in LEGS:
            upper = arm.data.bones.get(leg + "Upper")
            lower = arm.data.bones.get(leg + "Lower")
            if upper is None or lower is None or lower.parent is None or lower.parent.name != upper.name:
                raise ValueError("SOURCE_BONE_HIERARCHY_MISMATCH")
            specs.append({"actor": name, "leg": leg,
                          "pole": [sign * 0.36, 0.48, -0.42],
                          "upper": (upper.tail_local-upper.head_local).length,
                          "lower": (lower.tail_local-lower.head_local).length})
    frames = []
    for frame in FRAMES:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        poses = []
        for name in NAMES:
            arm = bpy.data.objects[name + "_Skeleton"]
            for leg, _ in LEGS:
                up = arm.pose.bones[leg + "Upper"]
                down = arm.pose.bones[leg + "Lower"]
                def xyz(vector):
                    return [float(v) for v in vector]
                poses.append({"actor": name, "leg": leg,
                              "hip": xyz(arm.matrix_world @ up.head),
                              "knee": xyz(arm.matrix_world @ up.tail),
                              "ankle": xyz(arm.matrix_world @ down.tail)})
        frames.append({"tick": frame, "poses": poses})
    document = {"schema": "scp.visualqa.l2_knee_input.v1",
                "rights": "ORIGINAL_SELF_AUTHORED_SYNTHETIC",
                "source_sha256": hashlib.sha256(blend.read_bytes()).hexdigest(),
                "legs": specs, "frames": frames}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
    print("VISUALQA_OBSERVED_NATIVE_BONE_COORDINATES", len(frames), len(specs))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    extract(args.blend, args.out)
