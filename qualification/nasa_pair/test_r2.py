import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from r2_probe import SOURCES, MODEL_SHA256, verify, fetch

class IndependentPairAdmission(unittest.TestCase):
    def test_immutable_source_provenance(self):
        self.assertEqual(SOURCES["video"]["sha1"], "dfc000088cfff728b57fe0c8ae38a7266410caeb")
        self.assertEqual(SOURCES["photo"]["sha1"], "e9e88122157dd60bc314d57754c02844954eaa00")
        self.assertNotEqual(SOURCES["photo"]["url"], SOURCES["video"]["url"])
        self.assertEqual(len(MODEL_SHA256), 64)
    def test_media_sha1_mismatch_fails(self):
        for meta in SOURCES.values():
            with self.assertRaises(ValueError):
                verify(meta, {"sha1": "0" * 40, "bytes": meta["bytes"]})
    def test_media_byte_length_mismatch_fails(self):
        for meta in SOURCES.values():
            with self.assertRaises(ValueError):
                verify(meta, {"sha1": meta["sha1"], "bytes": meta["bytes"] - 1})
    def test_source_allowlist_fails_before_network(self):
        with self.assertRaises(ValueError):
            fetch("https://example.invalid/file.webm", Path("/dev/null"), 1)

if __name__ == "__main__":
    unittest.main()
