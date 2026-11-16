"""R042 disposable mask-resolved clone export challenger.
Preserves original source body, rig, masks, morphs and .blend intact.
"""
import argparse
import hashlib
import json
import math
import os
import sys

import bpy
from mathutils.kdtree import KDTree

FRAMES = (1, 12, 24)


def fail(message):
    raise RuntimeError("R042_MASK_CLONE_HOLD " + message)


def points(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    o = obj.evaluated_get(dg)
    mesh = o.to_mesh()
    try:
        return [o.matrix_world @ v.co for v in mesh.vertices]
    finally:
        o.to_mesh_clear()


def nearest(a, b):
    if not a or not b:
        fail("empty mesh")
    t = KDTree(len(b))
    for j, q in enumerate(b):
        t.insert(q, j)
    t.balance()
    vals = []
    for p in a:
        _, _, d = t.find(p)
        if not math.isfinite(d):
            fail("nonfinite point distance")
        vals.append(d)
    vals.sort()
    return {
        "samples": len(vals),
        "max_m": float(vals[-1]),
        "p95_m": float(vals[max(0, math.ceil(.95 * len(vals)) - 1)]),
        "mean_m": float(sum(vals) / len(vals)),
    }


def measure(a, b):
    return {"native_to_import": nearest(a, b), "import_to_native": nearest(b, a)}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def clone_and_apply_mask(body, rig):
    clone = body.copy()
    clone.data = body.data.copy()
    clone.name = "R042_MaskResolved_MPFB_Body"
    bpy.context.collection.objects.link(clone)
    source_shape_count = len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0
    active_source_keys = [
        k.name for k in body.data.shape_keys.key_blocks
        if k.name != "Basis" and abs(k.value) > 1e-8
    ] if body.data.shape_keys else []
    if active_source_keys:
        fail("source shape keys are active; scratch clone cannot isolate mask impact: " + str(len(active_source_keys)))
    # Science-only negative/control: never mutate original source or silently
    # claim morph-preserving delivery from a topology-changing mask.
    # Drop *cloned* inactive source keys to isolate mask/export topology.
    # This explicitly DISQUALIFIES the derivative as a CharacterPack.
    bpy.ops.object.select_all(action="DESELECT")
    clone.select_set(True)
    bpy.context.view_layer.objects.active = clone
    if source_shape_count:
        bpy.ops.object.shape_key_remove(all=True)
    if clone.data.shape_keys is not None:
        fail("diagnostic clone shape keys still present")
    masks = [m for m in clone.modifiers if m.type == "MASK"]
    if len(masks) != 1 or masks[0].name != "Hide helpers":
        fail("unexpected native modifier stack; do not guess which mask to apply")
    mask = masks[0]
    if not mask.show_viewport or not mask.show_render:
        fail("mask is not enabled in both source viewport and render")
    original_mask = next(m for m in body.modifiers if m.name == mask.name)
    bpy.ops.object.select_all(action="DESELECT")
    clone.select_set(True)
    bpy.context.view_layer.objects.active = clone
    bpy.context.scene.frame_set(1)
    try:
        bpy.ops.object.modifier_apply(modifier=mask.name)
    except Exception as error:
        fail("Blender rejected mask-only clone: " + str(error))
    if any(m.type == "MASK" for m in clone.modifiers):
        fail("mask still present after apply")
    arms = [m for m in clone.modifiers if m.type == "ARMATURE" and m.object == rig]
    if len(arms) != 1:
        fail("clone lost source rig binding")
    if any(m.type not in ("ARMATURE",) for m in clone.modifiers):
        fail("unexpected remaining modifier(s) after mask-only apply")
    if original_mask.name not in [m.name for m in body.modifiers]:
        fail("immutable source body mask was unexpectedly altered")
    return clone, {"original_source_shape_keys_preserved": source_shape_count,
                   "diagnostic_clone_shape_keys_deliberately_omitted": source_shape_count,
                   "diagnostic_derivative_morph_fidelity": "FAIL_NOT_PRODUCTION_ADMISSIBLE",
                   "clone_vertices_after_mask": len(clone.data.vertices)}


def export_and_reimport(clone, rig, root, all_weights):
    bpy.ops.object.select_all(action="DESELECT")
    clone.select_set(True)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    label = "all" if all_weights else "four"
    output = os.path.join(root, "r042-mask-resolved-" + label + ".glb")
    bpy.ops.export_scene.gltf(
        filepath=output, export_format="GLB", use_selection=True,
        export_all_influences=all_weights
    )
    if not os.path.isfile(output) or os.stat(output).st_size < 2000:
        fail("exported clone GLB missing")
    old = {obj.as_pointer() for obj in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=output)
    added = [obj for obj in bpy.data.objects if obj.as_pointer() not in old]
    bodies = [obj for obj in added if obj.type == "MESH" and "R042_MaskResolved_MPFB_Body" in obj.name]
    arms = [obj for obj in added if obj.type == "ARMATURE"]
    if len(bodies) != 1 or not arms:
        fail("clone GLB failed independent body/armature import")
    imported = bodies[0]
    if not any(m.type == "ARMATURE" and m.object in arms for m in imported.modifiers):
        fail("imported clone has no skin-binding armature")
    samples = {}
    for f in FRAMES:
        bpy.context.scene.frame_set(f)
        samples[f] = points(imported)
    if len(samples[1]) != len(samples[24]):
        fail("imported clone topology changed with pose")
    active = any((a - b).length > 1e-7 for a, b in zip(samples[1], samples[24]))
    if not active:
        fail("imported clone did not animate")
    info = {
        "sha256": sha(output), "bytes": os.stat(output).st_size,
        "import_vertices": len(samples[1]), "import_rig_bones": sum(len(a.data.bones) for a in arms),
        "animated_after_import": active,
        "frame_points": samples,
    }
    for obj in added:
        bpy.data.objects.remove(obj, do_unlink=True)
    return info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    root = os.path.abspath(args.out)
    source_blend = os.path.join(root, "mpfb-official-anatomy.blend")
    if not os.path.isfile(source_blend):
        fail("source master native blend absent")
    body = bpy.data.objects.get("R036_Official_MPFB_Human")
    rig = bpy.data.objects.get("R036_Official_MPFB_Rig")
    if body is None or rig is None:
        fail("original native body/rig missing")
    source = {}
    for f in FRAMES:
        bpy.context.scene.frame_set(f)
        source[f] = points(body)
    before = sha(source_blend)
    clone, clone_meta = clone_and_apply_mask(body, rig)
    after = sha(source_blend)
    if before != after:
        fail("immutable source blend bytes mutated")
    clone_native = {}
    for f in FRAMES:
        bpy.context.scene.frame_set(f)
        clone_native[f] = points(clone)
    comparisons = {
        str(f): measure(source[f], clone_native[f]) for f in FRAMES
    }
    exports = {}
    for label, all_weights in (("four", False), ("all", True)):
        result = export_and_reimport(clone, rig, root, all_weights)
        measurements = {
            str(f): measure(source[f], result["frame_points"][f]) for f in FRAMES
        }
        exports[label] = {
            key: val for key, val in result.items() if key != "frame_points"
        }
        exports[label]["versus_native"] = measurements
    report = {
        "schema": "r042.mpfb.mask-clone-export.v1",
        "status": "DIAGNOSTIC_CLONE_ONLY_NO_CANONICAL_EXPORT_ACCEPTANCE",
        "source_blend_sha256_unchanged": before == after,
        "source_evaluated_vertices": len(source[1]),
        "clone": clone_meta,
        "native_vs_mask_clone": comparisons,
        "reimported": exports,
        "source_rig_bones": len(rig.data.bones),
        "limits": "source topology, morph controls, final shaders, game engine and physical fidelity NOT qualified",
        "scope": "public pinned MPFB + synthetic proxy organs only; original source preserved",
        "decision": "HOLD_ORIGINAL_MASTER_AND_RELEASE",
    }
    with open(os.path.join(root, "r042-mask-clone-diagnostic.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, sort_keys=True, indent=2)
    print("R042_MASK_CLONE_DIAGNOSTIC", json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
