"""Blender-only display adapter for verified ecology event traces.

Source GLB geometry and animation remain intact. Navigation offsets are
synthetic guidance, forage cones are data-visualization proxies, not botany.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def apply(imported, binding_path, source_glb, count, fps):
    raw = Path(binding_path).read_text()
    binding = json.loads(raw)
    if binding.get("schema") != "scp.ecology.scene-binding.v1":
        raise RuntimeError("unknown ecology scene binding")
    sent_digest = binding.get("binding_sha256")
    canonical = {k: v for k, v in binding.items() if k != "binding_sha256"}
    proof = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if sent_digest != proof:
        raise RuntimeError("tampered binding")
    if binding.get("model_sha256") != hashlib.sha256(Path(source_glb).read_bytes()).hexdigest():
        raise RuntimeError("scene binding model SHA mismatch")
    frames = binding.get("frames", [])
    if binding.get("frame_count") != count or binding.get("fps") != fps or len(frames) != count:
        raise RuntimeError("simulation and render frame mismatch")
    if count > 120:
        raise RuntimeError("unbounded video")
    actors = {a["id"]: a["node"] for a in frames[0]["actors"]}
    patches = {p["id"] for p in frames[0]["patches"]}
    if len(actors) != 6 or len(patches) != 3:
        raise RuntimeError("unexpected fauna/flora contract")
    if any(f["frame"] != i or set(a["id"] for a in f["actors"]) != set(actors)
           or set(p["id"] for p in f["patches"]) != patches
           for i, f in enumerate(frames, 1)):
        raise RuntimeError("inconsistent binding frames")
    scene = bpy.context.scene
    scene.frame_set(1)
    drivers = {}
    for name, node in sorted(actors.items()):
        match = [o for o in imported if o.name == node]
        if not match:
            tokens = [s.lower() for s in node.split("/")]
            match = [o for o in imported if all(t in o.name.lower() for t in tokens)]
        if len(match) != 1:
            raise RuntimeError("missing or ambiguous imported GLB animal root " + node)
        root = match[0]
        parent = root.parent
        before = root.matrix_world.copy()
        empty = bpy.data.objects.new("ecology/navigation/" + name, None)
        scene.collection.objects.link(empty)
        if parent:
            empty.parent = parent
            empty.matrix_parent_inverse = Matrix.Identity(4)
        root.parent = empty
        root.matrix_parent_inverse = Matrix.Identity(4)
        root.matrix_world = before
        drivers[name] = empty
    surface = bpy.data.materials.new("ecology/forage-data-proxy")
    surface.diffuse_color = (0.3, 0.7, 0.09, 1)
    surface.use_nodes = True
    shader = surface.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (0.3, 0.7, 0.09, 1)
    proxies = {}
    for p in frames[0]["patches"]:
        x,y,z = p["position"]
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=.55,
            radius2=.05, depth=1., location=(x,y,z+.45))
        item=bpy.context.object
        item.name="ecology/forage-proxy/" + p["id"]
        item.data.materials.append(surface)
        proxies[p["id"]]=item
    first_ratios = {p["id"]: p["ratio"] for p in frames[0]["patches"]}
    changed = False
    for f in frames:
        for a in f["actors"]:
            vector = Vector(a["offset"])
            driver = drivers[a["id"]]
            driver.location = (driver.parent.matrix_world.to_3x3().inverted() @ vector
                if driver.parent else vector)
            driver.keyframe_insert(data_path="location", frame=f["frame"])
        for p in f["patches"]:
            ratio=p["ratio"]
            if not isinstance(ratio, (int,float)) or not math.isfinite(ratio) or not 0 <= ratio <= 1:
                raise RuntimeError("invalid visual biomass ratio")
            changed = changed or abs(ratio-first_ratios[p["id"]]) > 1e-6
            item=proxies[p["id"]]
            item.scale=(.45+.3*ratio, .45+.3*ratio, .15+.85*ratio)
            item.keyframe_insert(data_path="scale",frame=f["frame"])
    if not changed:
        raise RuntimeError("no resource change to visualize")
    for ob in list(proxies.values())+list(drivers.values()):
        if ob.animation_data and ob.animation_data.action:
            for curve in ob.animation_data.action.fcurves:
                for key in curve.keyframe_points:
                    key.interpolation = "LINEAR"
    scene.frame_set(1)
    return {
        "ecology_binding_sha256": sent_digest,
        "ecology_report_sha256": binding["source_report_sha256"],
        "ecology_fidelity": binding["fidelity"],
        "ecology_actor_drivers": len(drivers),
        "ecology_resource_proxies": len(proxies),
        "ecology_visualization": "SYNTHETIC_NAVIGATION_AND_BIOMASS_CONES_NOT_REAL_BIOLOGY"
    }
