"""Independent morphology contract, character-differentiation and hostile tests."""
import copy
import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from modular_wardrobe_v1 import build, ACTORS
from parametric_morphology_v1 import (
    DEFAULT, BOUNDS, SCHEMA, apply, deform, validate)
from verify_original_glb import decode, accessory
from wardrobe_export_preset import export


class MorphologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.original = cls.root / "source.glb"
        cls.source_manifest = cls.root / "source.json"
        build(cls.original, cls.source_manifest)
        cls.morphed = cls.root / "morphed.glb"
        cls.manifest = cls.root / "morphed.json"
        cls.receipt = cls.root / "receipt.json"
        cls.proof = apply(cls.original, cls.source_manifest, cls.morphed,
                          cls.manifest, cls.receipt)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_owner_asserted_actor_sex_and_independent_parameters(self):
        self.assertEqual(DEFAULT["AsterOriginal"]["sex"], "male")
        self.assertEqual(DEFAULT["JuniperOriginal"]["sex"], "female")
        self.assertEqual(set(DEFAULT), set(ACTORS))
        custom = copy.deepcopy(DEFAULT)
        custom["JuniperOriginal"]["shoulder_width"] = 1.13
        custom["AsterOriginal"]["bust_projection_m"] = .012
        self.assertEqual(validate(custom), custom)  # No sex-locked controls.

    def test_differentiated_silhouette_and_facial_measures(self):
        a = DEFAULT["AsterOriginal"]; j = DEFAULT["JuniperOriginal"]
        # Samples in source-local metres; never conflate sex labels with inference.
        shoulder = (.19, 1.315, .02)
        waist = (.14, 1.05, -.06)
        hip = (.17, .875, -.06)
        jaw = (.088, 1.605, -.06)
        bust = (.085, 1.258, -.13)
        self.assertGreater(deform(shoulder, "body", a)[0],
                           deform(shoulder, "body", j)[0])
        self.assertLess(deform(waist, "body", j)[0],
                        deform(waist, "body", a)[0])
        self.assertGreater(deform(hip, "body", j)[0],
                           deform(hip, "body", a)[0])
        self.assertGreater(deform(jaw, "body", a)[0],
                           deform(jaw, "body", j)[0])
        self.assertLess(deform(bust, "body", j)[2],
                        deform(bust, "body", a)[2])

    def test_source_preserved_and_35_joint_animation_retained(self):
        before_bytes = self.original.read_bytes()
        doc_a, _ = decode(before_bytes)
        doc_b, bb = decode(self.morphed.read_bytes())
        manifest = json.loads(self.manifest.read_text())
        self.assertEqual(hashlib.sha256(before_bytes).hexdigest(),
                         self.proof["source_sha256"])
        self.assertEqual(self.proof["derived_sha256"],
                         hashlib.sha256(self.morphed.read_bytes()).hexdigest())
        self.assertEqual(manifest["derived_sha256"], self.proof["derived_sha256"])
        self.assertEqual(doc_b["skins"], doc_a["skins"])
        self.assertEqual(doc_b["animations"], doc_a["animations"])
        self.assertEqual(doc_b["extras"]["parametric_morphology"]["schema"], SCHEMA)
        self.assertEqual([len(s["joints"]) for s in doc_b["skins"]], [35, 35])
        self.assertEqual(self.proof["actor_vertex_changes"].keys(),
                         dict.fromkeys(ACTORS, 0).keys())
        self.assertTrue(all(self.proof["actor_vertex_changes"].values()))
        for actor in ACTORS:
            for slot in ("body", "hair", "top", "bottom"):
                mesh = doc_b["meshes"][manifest["actor_slots"][actor][slot]["mesh"]]
                for prim in mesh["primitives"]:
                    attrs = prim["attributes"]
                    xyz = accessory(doc_b, bb, attrs["POSITION"])
                    norms = accessory(doc_b, bb, attrs["NORMAL"])
                    self.assertEqual(len(xyz), len(norms))
                    self.assertTrue(all(all(math.isfinite(v) for v in p) for p in xyz))
                    self.assertTrue(all(abs(math.sqrt(sum(v*v for v in n))-1.) < .006
                                        for n in norms))

    def test_portable_worn_presets_interoperate_without_body_deletion(self):
        output = self.root / "viewer.glb"
        receipt = self.root / "viewer.json"
        p = {"AsterOriginal": "signature", "JuniperOriginal": "alternate"}
        result = export(self.morphed, self.manifest, output, receipt, p)
        self.assertEqual(result["presets"], p)
        self.assertIn("body", result["active_layers"]["AsterOriginal"])
        self.assertIn("body", result["active_layers"]["JuniperOriginal"])
        self.assertNotIn("alt_top", result["active_layers"]["AsterOriginal"])

    def test_invalid_profile_rejected(self):
        cases = [
            {**DEFAULT, "unknownActor": dict(DEFAULT["AsterOriginal"])},
            {**DEFAULT, "AsterOriginal": {**DEFAULT["AsterOriginal"],
                                        "jaw_width": float("nan")}},
            {**DEFAULT, "JuniperOriginal": {**DEFAULT["JuniperOriginal"],
                                          "hip_width": 40.}},
            {**DEFAULT, "JuniperOriginal": {**DEFAULT["JuniperOriginal"],
                                          "sex": "guessed"}},
            {**DEFAULT, "JuniperOriginal": {**DEFAULT["JuniperOriginal"],
                                          "not_a_control": 1}},
        ]
        for p in cases:
            with self.subTest(profile=p):
                with self.assertRaisesRegex(ValueError, "MORPH_PROFILE"):
                    validate(p)

    def test_mutated_manifest_rejected_before_geometry(self):
        tamper = json.loads(self.source_manifest.read_text())
        tamper["derived_sha256"] = "0"*64
        path = self.root / "tampered-source.json"
        path.write_text(json.dumps(tamper))
        with self.assertRaisesRegex(ValueError, "MORPH_SOURCE_MANIFEST_SHA"):
            apply(self.original, path, self.root / "bad.glb",
                  self.root / "bad-manifest.json", self.root / "bad-receipt.json")

    def test_output_source_overwrite_is_refused(self):
        with self.assertRaisesRegex(ValueError, "MORPH_SOURCE_OVERWRITE"):
            apply(self.original, self.source_manifest, self.original,
                  self.root / "refuse.json", self.root / "refuse-receipt.json")

    def test_determinism_and_no_fake_visual_acceptance(self):
        second = self.root / "repeat.glb"
        receipt = apply(self.original, self.source_manifest, second,
                        self.root / "repeat.json", self.root / "repeat-receipt.json")
        self.assertEqual(self.morphed.read_bytes(), second.read_bytes())
        self.assertEqual(receipt["human_appearance_accepted"], False)
        self.assertEqual(receipt["garment_fit_accepted"], False)
        self.assertEqual(receipt["animation_contact_accepted"], False)


if __name__ == "__main__":
    unittest.main()
