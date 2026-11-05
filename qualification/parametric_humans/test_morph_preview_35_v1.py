#!/usr/bin/env python3
"""Source-only geometry adversarial tests; real 35-joint GLB smoke is separate."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import morph_preview_35_v1 as adapter
import parameters_v1 as p


class MorphPreviewTests(unittest.TestCase):
    def test_source_owned_geometry_counts_and_positions(self):
        state=p.sample(73)
        source=adapter.wardrobe.adult_body_geometry(0)
        warped,proof=adapter.apply_original_shape(0,state)
        self.assertTrue(proof["source_geometry_preview"])
        self.assertGreater(proof["vertices_position_modified"],0)
        self.assertFalse(proof["wardrobe_collision_qualified"])
        for material in source.parts:
            old,new=source.parts[material],warped.parts[material]
            self.assertEqual(old["i"],new["i"],material)
            self.assertEqual(old["j"],new["j"],material)
            self.assertEqual(old["w"],new["w"],material)
            self.assertEqual(len(old["p"]),len(new["p"]),material)
        self.assertNotEqual(source.parts["skinWarm"]["p"],warped.parts["skinWarm"]["p"])

    def test_rig_parent_unchanged_after_multiple_actors(self):
        before=adapter.wardrobe.h.v1.figure_geometry
        hashes={path:hashlib.sha256((adapter.ORIGINAL/path).read_bytes()).hexdigest()
                for path in ("humanization_v2.py","modular_wardrobe_v1.py",
                             "generate_original_glb.py")}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"morph.glb"
            manifest=Path(td)/"manifest.json"
            receipt=Path(td)/"receipt.json"
            result=adapter.build(p.sample(73),p.sample(74),out,manifest,receipt)
            self.assertEqual(result["derived_glb_sha256"],
                hashlib.sha256(out.read_bytes()).hexdigest())
            self.assertEqual(result["rig_joint_count"],35)
            self.assertEqual(result["frames"],72)
            self.assertEqual(set(result["witnesses"]),{"AsterOriginal","JuniperOriginal"})
            self.assertTrue(result["mesh_topology_preserved"])
            self.assertFalse(result["release_approved"])
            self.assertEqual(json.loads(receipt.read_text())["scientific_status"],
                "UNKNOWN_NOT_ANATOMICALLY_OR_CLOTHING_QUALIFIED")
            with self.assertRaises(FileExistsError):
                adapter.build(p.sample(73),p.sample(74),out,manifest,receipt)
        self.assertIs(adapter.wardrobe.h.v1.figure_geometry,before)
        self.assertEqual({path:hashlib.sha256((adapter.ORIGINAL/path).read_bytes()).hexdigest()
                          for path in hashes},hashes)

    def test_reject_non_original_source(self):
        state=copy.deepcopy(p.sample(73))
        state["source_class"]="externally_acquired"
        with self.assertRaisesRegex(p.ContractError,"SOURCE_CLASS_MISMATCH"):
            adapter.apply_original_shape(1,state)


if __name__=="__main__":
    unittest.main(verbosity=2)
