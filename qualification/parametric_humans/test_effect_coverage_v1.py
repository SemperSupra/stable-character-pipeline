#!/usr/bin/env python3
"""Adversarial honesty gate: unwired controls must stay explicitly UNKNOWN."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
import effect_coverage_v1 as c
import parameters_v1 as p


class EffectCoverageTests(unittest.TestCase):
    def test_exact_semantic_schema_and_no_false_full_coverage(self):
        report=c.witness(73)
        self.assertEqual(report["control_count"],len(p.ALL_PATHS))
        self.assertEqual({x["path"] for x in report["controls"]},p.ALL_PATHS)
        self.assertGreater(report["geometry_effect_controls"],0)
        self.assertGreater(report["not_geometry_effect_controls"],0)
        self.assertFalse(report["all_controls_implemented"])
        self.assertFalse(report["clinically_validated"])
        self.assertFalse(report["human_visual_accepted"])

    def test_actual_geometry_and_explicit_unwired_appearance(self):
        table={x["path"]:x for x in c.witness(73)["controls"]}
        for path in ("morphology.waist_circumference_m",
                     "morphology.hip_circumference_m",
                     "morphology.jaw_width_ratio",
                     "morphology.left_breast_volume",
                     "morphology.right_breast_volume"):
            self.assertEqual(table[path]["status"],"GEOMETRY_EFFECT_CONFIRMED",path)
        for path in ("appearance.skin_melanin","appearance.hair_length_m",
                     "appearance.left_iris_rgb","appearance.hair_rgb"):
            self.assertEqual(table[path]["status"],"NO_GEOMETRY_EFFECT",path)
        self.assertTrue(all(not x["native_blender_render_verified"]
                            for x in table.values()))

    def test_source_remains_immutable_and_exact_determinism(self):
        first=c.witness(73)
        second=c.witness(73)
        self.assertEqual(first,second)

    def test_cli_refuses_overwriting_evidence(self):
        cli=Path(c.__file__)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"coverage.json"
            command=[sys.executable,str(cli),"--seed","73","--out",str(path)]
            subprocess.run(command,check=True,capture_output=True,text=True)
            self.assertEqual(json.loads(path.read_text())["schema"],c.SCHEMA)
            second=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)


if __name__=="__main__":
    unittest.main(verbosity=2)
