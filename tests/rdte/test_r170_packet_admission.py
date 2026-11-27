"""Original public synthetic typed packet receiver tests; no protected source."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

path = Path(__file__).with_name("r170_packet_admission.py")
spec = importlib.util.spec_from_file_location("r170_packet_admission", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(variant="A"):
    req = {
        "schema": m.REQUEST_SCHEMA,
        "source": {"document_id": "OriginalSynthetic", "revision": "syntheticRevision1", "graph_sha256": m.PLACEHOLDER_SOURCE},
        "frame": m.FRAME,
        "objects": [
            {"id": "cube", "feature_path": "root/cube", "material_id": "blue", "translation": [-0.8, 0, 0.7], "uniform_scale": 1},
            {"id": "sphere", "feature_path": "root/sphere", "material_id": "red", "translation": [0.9, 0, 0.85], "uniform_scale": 1}],
        "materials": [
            {"id": "blue", "base_color": [0.08, 0.25, 0.7], "metallic": 0, "roughness": 0.34},
            {"id": "red", "base_color": [0.75, 0.18, 0.12], "metallic": 0, "roughness": 0.22}],
        "cameras": [{"id": "camera", "position": [5, -7, 4], "target": [0, 0, 0.8], "up": [0, 0, 1], "fov_degrees": 45}],
        "lights": [{"id": "area", "type": "AREA", "position": [1, -3, 6], "power_watts": 1000, "size_meters": 5}],
        "options": {"engine": m.ENGINE, "width": 320, "height": 240, "samples": 32, "seed": 139},
    }
    if variant == "B":
        req["materials"][0]["base_color"] = [0.07, 0.68, 0.24]
        req["materials"][1]["base_color"] = [0.18, 0.25, 0.79]
        req["cameras"][0]["position"] = [4, -6, 4.5]
        req["lights"][0]["power_watts"] = 700
    return {
        "schema": m.SCHEMA,
        "variant": variant,
        "request": req,
        "synthetic_request_fingerprint": m.FROZEN_FINGERPRINTS[variant],
        "source_fidelity": m.FIDELITY,
    }


def encode(value):
    return json.dumps(value, separators=(",", ":"), allow_nan=True).encode("utf-8")


class ReceiverAdmissionTests(unittest.TestCase):
    def reject(self, value):
        with self.assertRaises(ValueError):
            m.validate_bytes(encode(value))

    def test_admit_go_canonical_variants_A_B(self):
        for variant in ("A", "B"):
            with self.subTest(variant=variant):
                p = fixture(variant)
                self.assertEqual(m.validate_bytes(encode(p))["variant"], variant)
                actual = m._sha(json.dumps(p["request"], separators=(",", ":"), allow_nan=False).encode())
                self.assertEqual(actual, m.FROZEN_FINGERPRINTS[variant])

    def test_reject_duplicate_json_keys_top_and_nested(self):
        p = fixture()
        raw = encode(p)
        self.assertIn(b'"schema":', raw)
        for corrupted in (raw.replace(b'"schema":', b'"schema":"forged","schema":', 1),
                          raw.replace(b'"width":320', b'"width":999,"width":320', 1)):
            with self.subTest(corrupted=corrupted[:60]):
                with self.assertRaises(ValueError):
                    m.validate_bytes(corrupted)

    def test_reject_nonfinite_and_overlong(self):
        p = fixture()
        p["request"]["lights"][0]["power_watts"] = float("nan")
        self.reject(p)
        with self.assertRaises(ValueError):
            m.validate_bytes(b" " * (m.MAX_BYTES + 1))

    def test_reject_wrong_fingerprint_and_variant_swaps(self):
        p = fixture()
        p["synthetic_request_fingerprint"] = "sha256:" + "0" * 64
        self.reject(p)
        p = fixture()
        p["variant"] = "B"
        self.reject(p)

    def test_reject_recomputed_fingerprint_for_unauthorized_change(self):
        p = fixture()
        p["request"]["lights"][0]["power_watts"] = 900
        p["synthetic_request_fingerprint"] = m._sha(json.dumps(p["request"], separators=(",", ":")).encode())
        self.reject(p)

    def test_reject_source_fidelity_and_identity(self):
        p = fixture()
        p["source_fidelity"] = "SOURCE_VERIFIED"
        self.reject(p)
        p = fixture()
        p["request"]["source"]["graph_sha256"] = "sha256:" + "f" * 64
        self.reject(p)

    def test_reject_extra_key_and_missing_required(self):
        p = fixture()
        p["request"]["objects"][0]["evil"] = 12
        self.reject(p)
        p = fixture()
        del p["request"]["source"]["revision"]
        self.reject(p)

    def test_reject_duplicate_object_or_material(self):
        p = fixture()
        p["request"]["objects"][1]["id"] = "cube"
        self.reject(p)
        p = fixture()
        p["request"]["materials"][1]["id"] = "blue"
        self.reject(p)

    def test_reject_unsafe_paths_and_changed_geometry(self):
        p = fixture()
        p["request"]["objects"][0]["feature_path"] = "root/../secret"
        self.reject(p)
        p = fixture()
        p["request"]["objects"][0]["translation"][0] = -0.3
        self.reject(p)

    def test_reject_degenerate_camera(self):
        p = fixture()
        p["request"]["cameras"][0]["target"] = [5, -7, 4]
        self.reject(p)
        p = fixture()
        p["request"]["cameras"][0]["up"] = [0, 0, 0]
        self.reject(p)

    def test_reject_bad_pbr_and_emitter(self):
        p = fixture()
        p["request"]["materials"][0]["roughness"] = 1.2
        self.reject(p)
        p = fixture()
        p["request"]["lights"][0]["power_watts"] = -1
        self.reject(p)

    def test_reject_bool_as_numeric(self):
        p = fixture()
        p["request"]["options"]["samples"] = True
        self.reject(p)
        p = fixture()
        p["request"]["materials"][0]["metallic"] = True
        self.reject(p)

    def test_reject_unsupported_engine_and_resource_increase(self):
        p = fixture()
        p["request"]["options"]["engine"] = "OTHER"
        self.reject(p)
        p = fixture()
        p["request"]["options"]["width"] = 2048
        self.reject(p)


if __name__ == "__main__":
    unittest.main()
