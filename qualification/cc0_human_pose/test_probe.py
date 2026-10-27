import json
import unittest
from pathlib import Path

from probe import SOURCE_SHA1, SOURCE_SIZE, SOURCE_URL, check_original, fetch

class AdmissionTests(unittest.TestCase):
    def test_manifest(self):
        manifest = json.loads((Path(__file__).parent / "source.v1.json").read_text())
        self.assertEqual(manifest["sha1"], SOURCE_SHA1)
        self.assertEqual(manifest["license"], "CC0-1.0")
    def test_bad_digest(self):
        with self.assertRaises(ValueError):
            check_original({"bytes": SOURCE_SIZE, "sha1": "000000", "sha256": ""})
    def test_bad_length(self):
        with self.assertRaises(ValueError):
            check_original({"bytes": 1, "sha1": SOURCE_SHA1, "sha256": ""})
    def test_unlisted_origin(self):
        with self.assertRaises(ValueError):
            fetch("https://invalid.example/path", Path("/dev/null"), 20)

if __name__ == "__main__":
    unittest.main()
