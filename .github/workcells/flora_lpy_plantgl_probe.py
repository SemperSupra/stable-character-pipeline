#!/usr/bin/env python3
"""Actual upstream OpenAlea L-Py and PlantGL headless API qualification.

Synthetic structural fixture. No claim of accurate species morphology or
simulation-ready geometry, and no actual Qt viewers or GPU required.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from openalea.lpy import Lsystem
from openalea.plantgl.all import BBoxComputer, Color3, Cylinder, Discretizer, Material, PglTurtle, Scene, Shape

SOURCE = """Axiom: A
derivation length: 3
production:
A --> F[+A][-A]
"""

def derive():
    with TemporaryDirectory() as folder:
        model = Path(folder) / "synthetic-branch.lpy"
        model.write_text(SOURCE)
        first = str(Lsystem(str(model)).derive())
        second = str(Lsystem(str(model)).derive())
        if first != second:
            raise AssertionError("nondeterministic L-Py derivation")
        if first.count("A") != 8 or first.count("F") != 7:
            raise AssertionError("unexpected L-Py grammar module counts")
        # Use upstream L-Py's actual turtle interpreter to construct real PlantGL geometry.
        turtle = PglTurtle()
        Lsystem(str(model)).turtle_interpretation(Lsystem(str(model)).derive(), turtle)
        derived_scene = turtle.getScene()
        if len(derived_scene) < 1:
            raise AssertionError("L-Py grammar did not produce PlantGL geometry")
        derived_shapes = len(derived_scene)
    return first, derived_shapes

def geometry():
    scene = Scene()
    material = Material(Color3(30, 180, 60))
    scene.add(Shape(Cylinder(.12, 2.0), material))
    scene.add(Shape(Cylinder(.05, 1.0), material))
    if len(scene) != 2:
        raise AssertionError("missing PlantGL geometry")
    bounding = BBoxComputer(Discretizer())
    scene.apply(bounding)
    if bounding.result is None:
        raise AssertionError("cannot compute PlantGL bounding volume")
    return len(scene)

def main():
    result, derived_shapes = derive()
    primitives = geometry()
    report = {
        "schema": "scp.floraprobe.lpy_plantgl.v1",
        "backend": "openalea.lpy + openalea.plantgl",
        "fidelity": "SYNTHETIC_GRAMMAR_AND_PRIMITIVES_ONLY",
        "production_iterations": 3,
        "terminal_count": result.count("F"),
        "apex_count": result.count("A"),
        "plantgl_primitives": primitives,
        "plantgl_derived_shapes": derived_shapes,
        "lpy_version": importlib.metadata.version("openalea.lpy"),
        "plantgl_version": importlib.metadata.version("openalea.plantgl")
    }
    report["digest_sha256"] = hashlib.sha256(
        json.dumps(report,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    print("QUALIFIED_LPY_DERIVATION_AND_PLANTGL_HEADLESS_GEOMETRY",
          json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    main()
