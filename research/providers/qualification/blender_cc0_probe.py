"""Actual Blender 4.5 glTF import/animation/export qualification of one CC0 Khronos fixture.

No model prediction, human character identity test, retarget or GPL MMD equivalence claim.
"""
import argparse
import hashlib
import json
import math
import pathlib
import struct

import bpy

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sample_times(source, gltf):
    buffers = [source / b["uri"] for b in gltf["buffers"]]
    all_times = []
    for animation in gltf["animations"]:
        for sampler in animation["samplers"]:
            acc = gltf["accessors"][sampler["input"]]
            view = gltf["bufferViews"][acc["bufferView"]]
            assert acc["componentType"] == 5126, "original floating-point time accessor expected"
            assert acc["type"] == "SCALAR"
            raw = buffers[view["buffer"]].read_bytes()
            offset = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
            times = struct.unpack_from("<" + str(acc["count"]) + "f", raw, offset)
            assert len(times) >= 2 and all(math.isfinite(t) for t in times)
            assert list(times) == sorted(times) and times[-1] > times[0]
            all_times.extend(times)
    return min(all_times), max(all_times)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    source = pathlib.Path(args.source).resolve()
    out = pathlib.Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    assert bpy.app.version >= (4, 5, 0), "requires genuine Blender >= 4.5"
    rights = (source / "README.md").read_text()
    assert "Creative Commons Zero v1.0 Universal" in rights
    gltf_path = source / "AnimatedTriangle.gltf"
    gltf = json.loads(gltf_path.read_text())
    assert gltf["asset"]["version"] == "2.0" and gltf["animations"]
    t0, t1 = sample_times(source, gltf)
    assert (source / "AnimatedTriangle_geometry.bin").stat().st_size == 44
    assert (source / "AnimatedTriangle_animation.bin").stat().st_size == 100

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 24
    result = bpy.ops.import_scene.gltf(filepath=str(gltf_path))
    assert "FINISHED" in result
    meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    assert meshes and len(bpy.data.actions) >= 1, "not a real Blender animation import"
    frames = sorted(set([int(round(t0 * 24)), int(round((t0 + t1) * 12)), int(round(t1 * 24))]))
    assert len(frames) >= 2, "invalid animation duration"
    observations = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        transformations = []
        for obj in sorted(bpy.data.objects, key=lambda x: x.name):
            q = obj.matrix_world.to_quaternion()
            transformations.append([obj.name] + [round(float(x), 8) for x in q])
        observations.append({"frame": frame, "transforms": transformations})
    assert len({json.dumps(v["transforms"]) for v in observations}) > 1, "no changing evaluated Blender transform"

    blend_path = out / "AnimatedTriangle_roundtrip.blend"
    glb_path = out / "AnimatedTriangle_roundtrip.glb"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    result = bpy.ops.export_scene.gltf(filepath=str(glb_path), export_format="GLB", export_animations=True)
    assert "FINISHED" in result
    raw = glb_path.read_bytes()
    assert raw[:4] == b"glTF"
    total_size = struct.unpack_from("<I", raw, 8)[0]
    assert total_size == len(raw), "invalid GLB length"
    json_len = struct.unpack_from("<I", raw, 12)[0]
    assert raw[16:20] == b"JSON"
    exported = json.loads(raw[20:20 + json_len])
    assert exported.get("animations"), "export lost the animation"
    assert exported.get("meshes"), "export lost mesh"

    report = {
        "schema": "scp.blender_real_cc0_qualification.v1",
        "source_model": "Khronos glTF-Sample-Assets AnimatedTriangle",
        "upstream_commit": "8f492390ddc7a2ae221a1369ef560589cf8c70fb",
        "source_license": "CC0-1.0 per exact upstream model README",
        "blender_version": bpy.app.version_string,
        "source_gltf_sha256": sha(gltf_path),
        "source_animation_bin_sha256": sha(source / "AnimatedTriangle_animation.bin"),
        "imported_mesh_count": len(meshes),
        "imported_actions": len(bpy.data.actions),
        "sampled_poses": observations,
        "export_animations": len(exported["animations"]),
        "export_meshes": len(exported["meshes"]),
        "export_glb_sha256": sha(glb_path),
        "blend_sha256": sha(blend_path),
        "limitations": "This is one CC0 rotating triangle, not a person, rigged model, measured human walking or MMD parity."
    }
    (out / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
if __name__ == "__main__":
    main()
