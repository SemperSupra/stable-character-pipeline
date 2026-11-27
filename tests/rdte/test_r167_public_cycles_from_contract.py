"""Source-free negative tests for the R167 typed Cycles scene overlay."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

script = Path(__file__).with_name("r167_public_cycles_from_contract.py")
spec = importlib.util.spec_from_file_location("r167_public_cycles_from_contract", script)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


# Reuse the exact original frozen A fixture; no second independent identity.
from test_r170_packet_admission import fixture as packet

class SyntheticPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name).resolve()
        self.source = root / "input.json"
        self.output = root / "output"
        self.output.mkdir(mode=0o700)
        self.write(packet())

    def write(self, value):
        self.source.write_text(json.dumps(value), encoding="utf-8")

    def read(self):
        return m.load_packet(self.source)

    def test_valid_synthetic_packet_and_paths(self):
        self.assertEqual(m.safe_paths(["blender", "--", str(self.source), str(self.output)]),
                         (self.source, self.output))
        v, raw = self.read()
        self.assertEqual(v["variant"], "A")
        self.assertGreater(len(raw), 100)

    def test_reject_wrong_packet_schema_and_rights_claim(self):
        x = packet()
        x["schema"] = "bad"
        self.write(x)
        with self.assertRaises(ValueError):
            self.read()
        x = packet()
        x["source_fidelity"] = "SOURCE_VERIFIED"
        self.write(x)
        with self.assertRaises(ValueError):
            self.read()

    def test_reject_unsupported_engine_and_overbudget(self):
        x = packet()
        x["request"]["options"]["engine"] = "OTHER"
        self.write(x)
        with self.assertRaises(ValueError):
            self.read()
        x = packet()
        x["request"]["options"]["width"] = 2048
        x["request"]["options"]["height"] = 2048
        x["request"]["options"]["samples"] = 256
        self.write(x)
        with self.assertRaises(ValueError):
            self.read()

    def test_reject_missing_and_nonfinite_transform(self):
        x = packet()
        x["request"]["objects"].pop()
        self.write(x)
        with self.assertRaises(ValueError):
            self.read()
        x = packet()
        x["request"]["objects"][0]["translation"][0] = float("nan")
        self.write(x)
        with self.assertRaises(ValueError):
            self.read()

    def test_reject_output_filename_symlink(self):
        (self.output / m.OUTPUT_FILES[0]).symlink_to(self.output / "missing")
        with self.assertRaises(ValueError):
            m.safe_paths(["blender", "--", str(self.source), str(self.output)])

    def test_reject_symlink_ancestor(self):
        target = self.output.parent / "actual"
        target.mkdir()
        alias = self.output.parent / "alias"
        alias.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            m.safe_paths(["blender", "--", str(self.source), str(alias)])

    def test_reject_public_output_permissions(self):
        import os
        if os.name == "nt":
            self.skipTest("POSIX 0700 check only")
        self.output.chmod(0o755)
        with self.assertRaises(ValueError):
            m.safe_paths(["blender", "--", str(self.source), str(self.output)])

    def test_reject_bad_argument_count(self):
        with self.assertRaises(ValueError):
            m.safe_paths(["blender", "--", str(self.source)])

    def test_reject_oversized_json_file(self):
        self.source.write_bytes(b" " * 65537)
        with self.assertRaises(ValueError):
            m.safe_paths(["blender", "--", str(self.source), str(self.output)])


if __name__ == "__main__":
    unittest.main()
