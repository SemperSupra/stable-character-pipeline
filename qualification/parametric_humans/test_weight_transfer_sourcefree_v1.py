"""R009 source-free fail-closed checks for bounded MakeHuman35 weight transfer.

No SciPy dependency, CC0 assets, private scans or large binaries in public CI.
Heavy actual-source 9-case suite and 72-frame receipts are separately archived.
"""
import hashlib
import unittest
from weight_transfer_regularize_v1 import (
    check_sha, SkinGateError, ACTORS, SCHEMA, SOURCE_SHA, ALPHA, ITERATIONS,
)

class SourceOnlyControls(unittest.TestCase):
    def test_source_pin_rejects_unrelated_bytes(self):
        with self.assertRaisesRegex(SkinGateError, "SOURCE_SHA_MISMATCH"):
            check_sha(b"not the admitted MakeHuman35 candidate")

    def test_digest_validation_fails_closed(self):
        with self.assertRaisesRegex(SkinGateError, "SOURCE_DIGEST_INVALID"):
            check_sha(b"x", "g" * 64)
        with self.assertRaisesRegex(SkinGateError, "SOURCE_FORMAT_INVALID"):
            check_sha(b"x", "short")
        with self.assertRaisesRegex(SkinGateError, "SOURCE_FORMAT_INVALID"):
            check_sha("not bytes")

    def test_known_reference_is_unchanged(self):
        self.assertEqual(SOURCE_SHA, "57a4cfd1d9df7e6e2f7c2e44e68765a8ca4357895d5b075f9229b78a5bbcd36a")
        self.assertEqual(ACTORS, ("AsterOriginal", "JuniperOriginal"))
        self.assertEqual(SCHEMA, "scp.r009.makehuman35.skin_weight_regularization.v1")

    def test_bounded_research_parameters(self):
        self.assertEqual(ITERATIONS, 4)
        self.assertEqual(ALPHA, 0.5)
        self.assertEqual(hashlib.sha256(b"not the admitted MakeHuman35 candidate").hexdigest() != SOURCE_SHA, True)

if __name__ == "__main__":
    unittest.main()
