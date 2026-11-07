"""Hostile source-free tests for pinned CC0 body-only OBJ extraction."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from basemesh_body_only_v1 import extract, BodyExtractionError, main
from basemesh_admission_v1 import git_blob_sha1


def fixture(extra=""):
    return ("# This asset was explicitly released as CC0\n"
            "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\n"
            "v 5 5 5\nv 6 6 6\nv 7 7 7\nv 8 8 8\n"
            "vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n"
            "g body\nf 1/1 2/2 3/3 4/4\n"
            "g helper-eye\nf 5/1 6/2 7/3 8/4\n" + extra).encode()


def shape():
    return {"vertices": 8, "quads": 2, "body_quads": 1, "body_vertex_indices": 4, "groups": 2}


class BodyOnlyTest(unittest.TestCase):
    def run_fixture(self, data):
        return extract(data, expected_blob=git_blob_sha1(data), expected_shape=shape())

    def test_body_face_selected_and_uv_preserved(self):
        obj, receipt = self.run_fixture(fixture())
        self.assertEqual(receipt["body_quads"], 1)
        self.assertEqual(receipt["body_vertices"], 4)
        self.assertEqual(receipt["body_uvs"], 4)
        self.assertEqual(receipt["excluded_helper_quads"], 1)
        self.assertEqual(obj.count(b"\nf "), 1)
        self.assertNotIn(b"helper-eye", obj)
        self.assertIn(b"f 1/1 2/2 3/3 4/4", obj)
        self.assertFalse(receipt["rig_transfer_qualified"])

    def test_byte_replay(self):
        data = fixture()
        a, ar = self.run_fixture(data)
        b, br = self.run_fixture(data)
        self.assertEqual(a, b)
        self.assertEqual(ar, br)

    def test_wrong_pin_rejected(self):
        with self.assertRaisesRegex(BodyExtractionError, "SOURCE_NOT_ADMITTED"):
            extract(fixture(), expected_blob="0" * 40, expected_shape=shape())

    def test_wrong_expected_shape_rejected(self):
        with self.assertRaisesRegex(BodyExtractionError, "SOURCE_NOT_ADMITTED"):
            extract(fixture(), expected_blob=git_blob_sha1(fixture()), expected_shape={"body_quads": 2})

    def test_bad_uv_rejected(self):
        data = fixture().replace(b"vt 1 0", b"vt nan 0")
        with self.assertRaises(BodyExtractionError):
            self.run_fixture(data)

    def test_out_of_bounds_uv_rejected(self):
        data = fixture().replace(b"f 1/1 2/2 3/3 4/4", b"f 1/1 2/2 3/3 4/15")
        with self.assertRaises(BodyExtractionError):
            self.run_fixture(data)

    def test_body_group_omission_rejected(self):
        data = fixture().replace(b"g body", b"g helper-body")
        with self.assertRaises(BodyExtractionError):
            self.run_fixture(data)

    def test_nonquad_rejected(self):
        data = fixture().replace(b"f 1/1 2/2 3/3 4/4", b"f 1/1 2/2 3/3")
        with self.assertRaises(BodyExtractionError):
            self.run_fixture(data)

    def test_replay_output_digest(self):
        obj, receipt = self.run_fixture(fixture())
        self.assertEqual(hashlib.sha256(obj).hexdigest(), receipt["output_sha256"])


if __name__ == "__main__":
    unittest.main()
