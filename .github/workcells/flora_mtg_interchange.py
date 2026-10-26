#!/usr/bin/env python3
"""F1c: real L-Py, MTG lineage, PlantGL tessellation; synthetic geometry only."""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from openalea.lpy import Lsystem
from openalea.mtg import MTG
from openalea.plantgl.all import Color3, Material, PglTurtle, Shape, Tesselator, TriangleSet

GRAMMAR = """Axiom: A
derivation length: 3
production:
A --> F[+A][-A]
"""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def graph_and_organs(word):
    graph = MTG()
    plant = graph.add_component(graph.root, label="synthetic_plant")
    current, stack, organs = None, [], []
    for token in word:
        if token == "F":
            name = f"stem_{sum(o['kind']=='stem' for o in organs):03d}"
            vid = graph.add_component(plant, label=name) if current is None else graph.add_child(current, label=name)
            organs.append({"organ_id": name, "kind": "stem", "mtg_vid": vid, "parent_vid": current, "scale": graph.scale(vid)})
            current = vid
        elif token == "A":
            if current is None:
                raise ValueError("unattached terminal apex")
            name = f"leaf_{sum(o['kind']=='leaf' for o in organs):03d}"
            vid = graph.add_child(current, label=name)
            organs.append({"organ_id": name, "kind": "leaf", "mtg_vid": vid, "parent_vid": current, "scale": graph.scale(vid)})
        elif token == "[":
            stack.append(current)
        elif token == "]":
            if not stack:
                raise ValueError("unbalanced branch")
            current = stack.pop()
        elif token not in "+-":
            raise ValueError("unexpected L-Py grammar token: " + repr(token))
    if stack or sum(o["kind"] == "stem" for o in organs) != 7 or sum(o["kind"] == "leaf" for o in organs) != 8:
        raise ValueError("unexpected grammar topology")
    if graph.nb_vertices() != 17 or graph.nb_scales() != 3:
        raise ValueError("unexpected MTG scales or vertices")
    for organ in organs:
        if organ["parent_vid"] is not None and graph.parent(organ["mtg_vid"]) != organ["parent_vid"]:
            raise ValueError("MTG parent provenance mismatch")
    return graph, organs


def tessellate(shape):
    tess = Tesselator()
    tess.process(shape.geometry)
    mesh = tess.triangulation
    if mesh is None:
        raise ValueError("real PlantGL tessellation unavailable")
    vertices = [tuple(float(c) for c in p) for p in mesh.pointList]
    faces = [tuple(int(n) for n in tri) for tri in mesh.indexList]
    if len(vertices) < 3 or not faces or any(len(tri) != 3 for tri in faces):
        raise ValueError("invalid upstream triangles")
    if any(n < 0 or n >= len(vertices) for tri in faces for n in tri):
        raise ValueError("out-of-bounds upstream face")
    if any(not math.isfinite(c) or abs(c) > 100 for p in vertices for c in p):
        raise ValueError("non-finite or unbounded upstream vertex")
    return vertices, faces


def bounding(points):
    return [[round(min(p[i] for p in points), 6) for i in range(3)],
            [round(max(p[i] for p in points), 6) for i in range(3)]]


def leaf_plate(anchor, index, width=0.14, length=0.35):
    # Approximate parent-stem tip and original synthetic leaf plate, NOT botany.
    angle = index * 2.399963229728653
    dx, dy = math.cos(angle), math.sin(angle)
    sx, sy = -dy * width, dx * width
    x, y, z = anchor
    vertices = [(x-sx*.45, y-sy*.45, z),
                (x+sx*.45, y+sy*.45, z),
                (x+dx*length, y+dy*length, z+.06),
                (x+dx*length*.55, y+dy*length*.55, z+.10)]
    return Shape(TriangleSet(vertices, [(0, 1, 3), (1, 2, 3), (2, 0, 3)]),
                 Material(Color3(45, 140, 50)))


def serialize_obj(points, faces, organ):
    # Standard OBJ serializer of actual PlantGL tessellated mesh, not a new engine.
    lines = ["# synthetic PlantGL tessellation; illustrative source unit = meter", "o " + organ]
    lines.extend("v {:.9f} {:.9f} {:.9f}".format(*p) for p in points)
    lines.extend("f {} {} {}".format(*(v+1 for v in f)) for f in faces)
    return ("\n".join(lines) + "\n").encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    out = Path(parser.parse_args().out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory() as tmp:
        p = Path(tmp) / "synthetic.lpy"
        p.write_text(GRAMMAR)
        lsys = Lsystem(str(p))
        word = str(lsys.derive())
        if word != str(Lsystem(str(p)).derive()):
            raise ValueError("L-Py derivation nondeterministic")
        graph, organs = graph_and_organs(word)
        turtle = PglTurtle()
        lsys.turtle_interpretation(lsys.derive(), turtle)
        source_scene = list(turtle.getScene())
        if len(source_scene) != 7:
            raise ValueError("expected 7 actual PglTurtle source shapes, found " + str(len(source_scene)))
        stems = [o for o in organs if o["kind"] == "stem"]
        leaves = [o for o in organs if o["kind"] == "leaf"]
        shape_by_vid = {}
        for i, organ in enumerate(stems):
            shape_by_vid[organ["mtg_vid"]] = source_scene[i]
            organ["source"] = "real L-Py PglTurtle shape at F-module ordinal " + str(i)
        leaf_shapes = {}
        for i, organ in enumerate(leaves):
            parent_points, _ = tessellate(shape_by_vid[organ["parent_vid"]])
            anchor = max(parent_points, key=lambda p: (p[2], p[0], p[1]))
            leaf_shapes[organ["mtg_vid"]] = leaf_plate(anchor, i)
            organ["source"] = "original parametric PlantGL TriangleSet at approximate parent-stem tip"
        for organ in organs:
            shape = (shape_by_vid if organ["kind"] == "stem" else leaf_shapes)[organ["mtg_vid"]]
            points, faces = tessellate(shape)
            if max(max(p[i] for p in points)-min(p[i] for p in points) for i in range(3)) < 1e-5:
                raise ValueError("degenerate shape " + organ["organ_id"])
            payload = serialize_obj(points, faces, organ["organ_id"])
            name = organ["organ_id"] + ".obj"
            (out/name).write_bytes(payload)
            organ.update({"obj": name, "obj_sha256": digest(payload),
                          "source_bounds_m": bounding(points),
                          "vertices": len(points), "triangles": len(faces)})
        report = {
            "schema": "scp.flora.mtg_interchange.v1",
            "fidelity": "SYNTHETIC_LPY_STEMS_AND_APPROXIMATE_PLANTGL_LEAF_PLATES",
            "unit_policy": "1 synthetic source unit assumed equal to 1 meter for interchange ONLY",
            "coordinate_system": "Z_UP_RIGHT_HANDED",
            "mesh_provider": "openalea.plantgl.Tesselator",
            "source_grammar_sha256": digest(GRAMMAR.encode()),
            "grammar_iterations": 3, "mtg_vertices": graph.nb_vertices(),
            "mtg_scales": graph.nb_scales(), "source_lpy_shapes": len(source_scene),
            "organ_count": len(organs), "organ_records": organs,
            "dependencies": {name: importlib.metadata.version(name) for name in
                             ("openalea.lpy", "openalea.plantgl", "openalea.mtg")},
            "rights": "original synthetic geometry; upstream runtime binaries not redistributed",
            "limitations": "ordinal mapping only; no real tropical botany, physiology, contact or time-calibrated growth"
        }
        report["digest_sha256"] = digest(canonical(report))
        (out/"source_receipt.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("F1C_PLANTGL_SOURCE_PASS " + json.dumps({
            "count": len(organs), "digest_sha256": report["digest_sha256"],
            "versions": report["dependencies"]}, sort_keys=True))


if __name__ == "__main__":
    main()
