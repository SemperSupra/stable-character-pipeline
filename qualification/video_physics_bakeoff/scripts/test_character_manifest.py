#!/usr/bin/env python3
"""Fail-closed adapter controls with no external dependencies."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from character_manifest import BATCHES, load_manifest

class CharacterManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.files = []
        for idx, batch in enumerate(BATCHES):
            name = "case_" + str(idx)
            folder = self.root / batch
            folder.mkdir()
            raw = ("original-video-" + name).encode()
            path = folder / (name + "_side.mp4")
            path.write_bytes(raw)
            data = {"schema": "scp.expanded-original-3d-motion-corpus.v1",
                    "batch": batch,
                    "rights": "CC0-1.0 for original generated files",
                    "cases": [{"case": name, "spec": {"motion": "stand" if idx == 0 else "walk"},
                               "videos": [{"file": path.name, "sha256": hashlib.sha256(raw).hexdigest()}]}]}
            (folder / "manifest.json").write_text(json.dumps(data))
            self.files.append(path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_four_batches_no_oracle(self):
        cases = load_manifest(self.root)["cases"]
        self.assertEqual(len(cases), 4)
        self.assertTrue(all("expect" not in c for c in cases))
        self.assertFalse(cases[0]["expected_motion"])
        self.assertTrue(cases[1]["expected_motion"])

    def test_tampering_rejected(self):
        self.files[1].write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "VIDEO_SHA_MISMATCH"):
            load_manifest(self.root)

    def test_unexpected_rights_rejected(self):
        p = self.root / BATCHES[0] / "manifest.json"
        doc = json.loads(p.read_text())
        doc["rights"] = "unknown"
        p.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_BATCH_OR_RIGHTS"):
            load_manifest(self.root)

if __name__ == "__main__":
    unittest.main()
