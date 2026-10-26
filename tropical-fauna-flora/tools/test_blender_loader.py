#!/usr/bin/env python3
"""Isolated Python regression for Blender's --python script import path.

Run with python3 -I from the tropical-fauna-flora workcell root.
Fake Blender modules only to test import resolution; no rendering claims.
"""
import runpy
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / "render_blender.py"
if str(script.parent) in sys.path:
    raise AssertionError("loader smoke must use isolated Python (-I)")

mathutils = ModuleType("mathutils")
mathutils.Vector = object
mathutils.Matrix = object
with patch.dict(sys.modules, {"bpy": ModuleType("bpy"), "mathutils": mathutils}):
    runpy.run_path(str(script), run_name="__blender_import_probe__")
    from tools.ecology_blender import apply
    if not callable(apply):
        raise AssertionError("ecology Blender adapter did not resolve")

print("PASS: isolated --python entrypoint resolves the public ecology adapter")
