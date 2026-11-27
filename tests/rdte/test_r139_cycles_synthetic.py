"""Source-safe standard-Python tests: NOT native Blender/Cycles execution."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("r139_cycles_synthetic.py")
spec = importlib.util.spec_from_file_location("r139_cycles_synthetic", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestCyclesSyntheticContract(unittest.TestCase):
    def test_stable_fixture_hash(self):
        self.assertEqual(module.stable_json(module.FIXTURE), module.stable_json(module.FIXTURE))
        self.assertTrue(module.digest(module.stable_json(module.FIXTURE)).startswith("sha256:"))

    def test_existing_clean_dir_required(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            self.assertEqual(module.validate_output_dir(["blender", "--", str(root)]), root)
            with self.assertRaises(ValueError):
                module.validate_output_dir(["blender", "--", str(root), "extra"])
            with self.assertRaises(ValueError):
                module.validate_output_dir(["blender", "--", str(root / "missing")])
            (root / module.OUTPUT_NAMES[0]).write_bytes(b"previous")
            with self.assertRaises(ValueError):
                module.validate_output_dir(["blender", "--", str(root)])

    def test_r144_dangling_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            (root / module.OUTPUT_NAMES[0]).symlink_to(root / "missing.png")
            with self.assertRaises(ValueError):
                module.validate_output_dir(["blender", "--", str(root)])

    def test_r144_symlink_ancestor_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            actual = root / "private"
            actual.mkdir()
            (actual / "scene").mkdir()
            alias = root / "alias"
            alias.symlink_to(actual, target_is_directory=True)
            with self.assertRaises(ValueError):
                module.validate_output_dir(["blender", "--", str(alias / "scene")])

    def test_r144_world_traversable_output_dir_rejected(self):
        import os
        if os.name == "nt":
            self.skipTest("POSIX mode boundary not qualified on Windows")
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve() / "public"
            root.mkdir(mode=0o755)
            root.chmod(0o755)
            with self.assertRaises(ValueError):
                module.validate_output_dir(["blender", "--", str(root)])

    def test_missing_args_fail_closed(self):
        with self.assertRaises(ValueError):
            module.validate_output_dir(["blender"])

    def test_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()
            target = root / "target"
            target.mkdir()
            alias = root / "alias"
            alias.symlink_to(target, target_is_directory=True)
            # The current version resolves before checking symlink; explicitly
            # record this negative to prevent caller-controlled alias bypass.
            with self.assertRaises(ValueError):
                module.validate_output_dir(["blender", "--", str(alias)])


if __name__ == "__main__":
    unittest.main()
