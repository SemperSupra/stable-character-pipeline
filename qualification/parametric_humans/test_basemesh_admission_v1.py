"""Source-free hostile controls for pinned MakeHuman CC0 basemesh admission."""
import unittest
from basemesh_admission_v1 import AdmissionError,git_blob_sha1,inspect,SCHEMA

HEADER="# This asset was explicitly released as CC0 in september 2020.\n"
GOOD=(HEADER+"v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\ng body\nf 1 2 3 4\n").encode()

def admit(data):
    return inspect(data,git_blob_sha1(data))

class TestAdmission(unittest.TestCase):
    def test_cc0_quad(self):
        r=admit(GOOD)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["quantities"]["body_quads"],1)
        self.assertEqual(r["quantities"]["body_vertex_indices"],4)
        self.assertFalse(r["human_realism_accepted"])
        self.assertFalse(r["rig_transfer_qualified"])
    def test_wrong_pin(self):
        with self.assertRaisesRegex(AdmissionError,"SOURCE_BLOB_SHA_MISMATCH"):
            inspect(GOOD,"0"*40)
    def test_no_license(self):
        with self.assertRaisesRegex(AdmissionError,"SOURCE_LICENSE_HEADER_MISSING"):
            admit(GOOD.replace(b"CC0",b"NONE"))
    def test_triangle_rejected(self):
        with self.assertRaisesRegex(AdmissionError,"NON_QUAD_FACE"):
            admit(GOOD.replace(b"f 1 2 3 4",b"f 1 2 3"))
    def test_oob(self):
        with self.assertRaisesRegex(AdmissionError,"INVALID_FACE_INDEX"):
            admit(GOOD.replace(b"f 1 2 3 4",b"f 1 2 3 9"))
    def test_duplicate_index(self):
        with self.assertRaisesRegex(AdmissionError,"INVALID_FACE_INDEX"):
            admit(GOOD.replace(b"f 1 2 3 4",b"f 1 2 2 4"))
    def test_nonfinite(self):
        with self.assertRaisesRegex(AdmissionError,"NONFINITE_VERTEX"):
            admit(GOOD.replace(b"v 0 0 0",b"v nan 0 0"))
    def test_duplicate_group(self):
        with self.assertRaisesRegex(AdmissionError,"DUPLICATE_GROUP"):
            admit(GOOD+b"g body\n")
    def test_topology_mismatch(self):
        with self.assertRaisesRegex(AdmissionError,"PINNED_TOPOLOGY_MISMATCH"):
            inspect(GOOD,git_blob_sha1(GOOD),{"vertices":5})
    def test_unknown_record(self):
        with self.assertRaisesRegex(AdmissionError,"UNSUPPORTED_OBJ_RECORD"):
            admit(GOOD+b"call-this-not-data\n")
    def test_missing_body(self):
        with self.assertRaisesRegex(AdmissionError,"MISSING_BODY"):
            admit(GOOD.replace(b"g body",b"g hair"))

if __name__=="__main__":
    unittest.main()
