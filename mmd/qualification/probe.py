#!/usr/bin/env python3
"""Original synthetic PMX/VMD/VPD fixtures tested with upstream MMD Tools 4.5.14."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

def module(root, name):
    file = root / "mmd_tools" / "core" / name / "__init__.py"
    if not file.is_file():
        raise FileNotFoundError(file)
    spec = importlib.util.spec_from_file_location("scp_mmd_" + name, file)
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def assert_rejected(action, error, label):
    try:
        action()
    except error:
        return label + ":REJECTED"
    raise AssertionError(label + " unexpectedly accepted malformed input")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    pmx = module(args.source, "pmx")
    vmd = module(args.source, "vmd")
    vpd = module(args.source, "vpd")

    # Public fixtures are authored here: no borrowed MMD models, dances, or poses.
    model = pmx.Model()
    model.name, model.name_e = "公開テスト", "SCP synthetic triangle"
    model.comment = "Original test triangle, not an observed or licensed person"
    bone = pmx.Bone()
    bone.name, bone.name_e = "センター", "Center"
    bone.location, bone.displayConnection = (0., 0., 0.), (0., 1., 0.)
    model.bones = [bone]
    for xyz, uv in [((-1., 0., 0.), (0., 0.)), ((1., 0., 0.), (1., 0.)), ((0., 1., 0.), (.5, 1.))]:
        vertex = pmx.Vertex()
        vertex.co, vertex.normal, vertex.uv = xyz, (0., 0., 1.), uv
        vertex.weight = pmx.BoneWeight()
        vertex.weight.bones = [0]
        model.vertices.append(vertex)
    model.faces = [(0, 1, 2)]
    material = pmx.Material()
    material.name, material.name_e = "SCPテスト", "SCP original"
    material.diffuse = (.3, .6, .9, 1.)
    material.specular, material.ambient = (0., 0., 0.), (.2, .2, .2)
    material.edge_color, material.vertex_count = (0., 0., 0., 1.), 3
    model.materials = [material]

    pmx_file = args.out / "synthetic_triangle.pmx"
    pmx.save(str(pmx_file), model)
    parsed = pmx.load(str(pmx_file))
    assert parsed.name == model.name and len(parsed.vertices) == 3
    assert len(parsed.faces) == 1 and len(parsed.bones) == 1
    assert parsed.bones[0].name == bone.name and len(parsed.materials) == 1
    assert all(v.weight.bones == [0] for v in parsed.vertices)

    anim = vmd.File()
    anim.header = vmd.Header()
    anim.header.model_name = model.name
    anim.boneAnimation = vmd.BoneAnimation()
    for frame, y in [(0, 0.), (30, .5)]:
        key = vmd.BoneFrameKey()
        key.frame_number, key.location = frame, (0., y, 0.)
        key.rotation, key.interp = (0., 0., 0., 1.), (20, 20, 107, 107) * 16
        anim.boneAnimation[bone.name].append(key)
    vmd_file = args.out / "synthetic_center_motion.vmd"
    anim.save(filepath=str(vmd_file))
    parsed_anim = vmd.File()
    parsed_anim.load(filepath=str(vmd_file))
    frames = parsed_anim.boneAnimation[bone.name]
    assert parsed_anim.header.model_name == model.name
    assert [k.frame_number for k in frames] == [0, 30]
    assert math.isclose(frames[1].location[1], .5, abs_tol=1e-6)

    pose = vpd.File()
    pose.osm_name = model.name
    pose.bones = [vpd.VpdBone(bone.name, [0., .25, 0.], [0., 0., 0., 1.])]
    vpd_file = args.out / "synthetic_center_pose.vpd"
    pose.save(filepath=str(vpd_file))
    parsed_pose = vpd.File()
    parsed_pose.load(filepath=str(vpd_file))
    assert len(parsed_pose.bones) == 1
    assert parsed_pose.bones[0].bone_name == bone.name
    assert parsed_pose.bones[0].location == [0., .25, 0.]

    # Repeat exact serializer calls and enforce byte-identical output.
    other_pmx = args.out / "repeat.pmx"
    pmx.save(str(other_pmx), model)
    assert other_pmx.read_bytes() == pmx_file.read_bytes()
    other_pmx.unlink()
    other_vmd = args.out / "repeat.vmd"
    anim.save(filepath=str(other_vmd))
    assert other_vmd.read_bytes() == vmd_file.read_bytes()
    other_vmd.unlink()

    invalid_pmx = args.out / "invalid.pmx"
    invalid_pmx.write_bytes(b"NOPE" + pmx_file.read_bytes()[4:])
    negative = [assert_rejected(lambda: pmx.load(str(invalid_pmx)), pmx.InvalidFileError, "PMX_BAD_MAGIC")]
    invalid_pmx.unlink()
    invalid_vmd = args.out / "invalid.vmd"
    invalid_vmd.write_bytes(b"NOPE".ljust(50, b"\0"))
    def load_vmd():
        obj = vmd.File()
        obj.load(filepath=str(invalid_vmd))
    negative.append(assert_rejected(load_vmd, vmd.InvalidFileError, "VMD_BAD_MAGIC"))
    invalid_vmd.unlink()
    invalid_vpd = args.out / "invalid.vpd"
    invalid_vpd.write_text("NOT POSE", encoding="utf-8")
    def load_vpd():
        obj = vpd.File()
        obj.load(filepath=str(invalid_vpd))
    negative.append(assert_rejected(load_vpd, vpd.InvalidFileError, "VPD_BAD_MAGIC"))
    invalid_vpd.unlink()

    report = {
      "schema": "scp.mmd.qualification.v1",
      "result": "PASS_PARSER_ROUNDTRIPS_AND_NEGATIVE_CONTROLS",
      "source": "MMD Tools v4.5.14 pinned commit, upstream parsers",
      "rights": "original self-generated test triangle and motion; GPL upstream not vendored",
      "bone_count": 1, "mesh_vertices": 3, "keyframes": [0, 30],
      "negative_controls": negative,
      "files": {p.name: {"sha256": digest(p), "bytes": p.stat().st_size} for p in (pmx_file, vmd_file, vpd_file)},
      "unverified": ["Blender import", "VMD-to-armature animation", "IK", "physics", "soft tissue", "third-party model rights"]
    }
    (args.out / "qualification.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    main()
