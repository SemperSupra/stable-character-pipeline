import copy
import hashlib
import json
import unittest

import verify

def fake_manifest():
    same = hashlib.sha256(b"synthetic constant scene").hexdigest()
    records = {}
    for name, c in verify.EXPECTED.items():
        records[name] = {
            "config":dict(c),
            "lighting_sha256":verify.config_hash(c),
            "geometry_sha256":same,
            "camera_sha256":same,
            "baseline_receipt_sha256":same,
            "material_receipt_sha256":same,
        }
    return {
        "schema":"r044.original.lighting.v1",
        "rights":"ORIGINAL_SYNTHETIC",
        "status":"RENDERED_FOR_INDEPENDENT_EVALUATION",
        "qualification":"NOT_PHOTOREALISM_OR_REAL_CHARACTER_EVIDENCE",
        "source_script_sha256":same,
        "scenarios":records
    }

class TestStrictLightingManifest(unittest.TestCase):
    def test_positive_exact_synthetic(self):
        verify.validate_manifest(fake_manifest())

    def test_reject_relabelled(self):
        v=fake_manifest()
        v["scenarios"]["diffuse_soft"],v["scenarios"]["directional_hard"]=(
            v["scenarios"]["directional_hard"],v["scenarios"]["diffuse_soft"])
        with self.assertRaises(ValueError):verify.validate_manifest(v)

    def test_reject_privacy_or_false_quality(self):
        for key,bad in (
            ("rights","UNKNOWN"),
            ("rights","PRIVATE_PERSON"),
            ("status","PASS_PHOTOREALISM"),
            ("qualification","ACCEPTED_HUMAN_PREFERENCE")):
            v=fake_manifest();v[key]=bad
            with self.subTest(key=key,bad=bad):
                with self.assertRaises(ValueError):verify.validate_manifest(v)

    def test_reject_light_edits(self):
        for key,bad in (("key_power",-1.),("key_size",float('nan')),("fill_power",1e300)):
            v=fake_manifest();v["scenarios"]["diffuse_soft"]["config"][key]=bad
            with self.subTest(key=key):
                with self.assertRaises(ValueError):verify.validate_manifest(v)

    def test_reject_scene_drift(self):
        for key in ("geometry_sha256","camera_sha256"):
            v=fake_manifest()
            v["scenarios"]["directional_hard"][key]=hashlib.sha256(key.encode()).hexdigest()
            with self.assertRaises(ValueError):verify.validate_manifest(v)

    def test_reject_missing_condition_or_hash(self):
        v=fake_manifest();del v["scenarios"]["directional_hard"]
        with self.assertRaises(ValueError):verify.validate_manifest(v)
        v=fake_manifest();v["scenarios"]["diffuse_soft"]["baseline_receipt_sha256"]="0"
        with self.assertRaises(ValueError):verify.validate_manifest(v)

if __name__=="__main__":
    unittest.main()
