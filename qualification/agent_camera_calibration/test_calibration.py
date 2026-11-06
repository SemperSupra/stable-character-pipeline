import copy
import json
import math
import unittest
from calibration import AdmissionError, assess


def fixture():
    rows = []
    for view, fx, fy, cx, cy, source, extrinsics, train_image, held_image in (
        ("front", 800., 780., 320., 240., "e"*64, "1"*64, "a"*64, "c"*64),
        ("oblique", 760., 820., 300., 220., "f"*64, "2"*64, "b"*64, "d"*64),
    ):
        for i in range(9):
            x = (i - 4) * .025
            y = ((i * 2) % 9 - 4) * .025
            z = 1.0 + i * .02
            role = "train" if i < 6 else "heldout"
            rows.append({"view": view, "role": role,
                         "family": view + ("_training" if role == "train" else "_heldout"),
                         "image_sha256": train_image if role == "train" else held_image,
                         "source_sha256": source, "extrinsics_sha256": extrinsics,
                         "point_id": view + ":" + str(i),
                         "xyz": [x, y, z],
                         "uv": [fx*x/z+cx, fy*y/z+cy],
                         "size": [640, 480]})
    return rows


class CameraCalibrationHostileTests(unittest.TestCase):
    def test_actual_heldout_reprojection(self):
        result = assess(fixture())
        self.assertEqual(result["geometry"], "PASS_DECLARED_SYNTHETIC_ONLY")
        self.assertEqual(len(result["views"]), 2)
        self.assertAlmostEqual(result["views"][0]["fx_px"], 800., places=4)
        self.assertAlmostEqual(result["views"][1]["fy_px"], 820., places=4)
        self.assertTrue(all(v["heldout_rmse_px"] < 1e-4 for v in result["views"]))
        self.assertEqual(result["external_photo_fit"], "NOT_RUN")
        self.assertFalse(result["release_or_CPE_admission"])
        print("CAMERA_SYNTHETIC_ONLY_RECEIPT", json.dumps(result, sort_keys=True))

    def test_heldout_pixel_drift_dominates_pass(self):
        rows = fixture()
        for r in rows:
            if r["view"] == "front" and r["role"] == "heldout":
                r["uv"][0] += 5
        self.assertEqual(assess(rows)["geometry"], "FAIL_HELDOUT_REPROJECTION")

    def test_capture_family_leakage_denied(self):
        rows = fixture()
        rows[6]["family"] = rows[0]["family"]
        with self.assertRaisesRegex(AdmissionError, "family"):
            assess(rows)

    def test_image_byte_leakage_denied(self):
        rows = fixture()
        rows[6]["image_sha256"] = rows[0]["image_sha256"]
        with self.assertRaisesRegex(AdmissionError, "image"):
            assess(rows)

    def test_cross_view_global_family_leakage_denied(self):
        rows = fixture()
        rows[15]["family"] = rows[0]["family"]
        with self.assertRaisesRegex(AdmissionError, "global family"):
            assess(rows)

    def test_insufficient_and_single_view_denied(self):
        rows = fixture()
        with self.assertRaisesRegex(AdmissionError, "two or more"):
            assess([r for r in rows if r["view"] == "front"])
        with self.assertRaisesRegex(AdmissionError, "insufficient"):
            assess([r for r in rows if r["point_id"] != "front:6"])

    def test_degenerate_camera_axis_denied(self):
        rows = fixture()
        for r in rows:
            if r["view"] == "front" and r["role"] == "train":
                r["xyz"][0] = 0.
                r["uv"][0] = 320.
        with self.assertRaisesRegex(AdmissionError, "degenerate"):
            assess(rows)

    def test_extrinsics_declaration_not_authenticated(self):
        rows = fixture()
        rows[0]["extrinsics_sha256"] = "3"*64
        with self.assertRaisesRegex(AdmissionError, "extrinsics"):
            assess(rows)
        rows = fixture()
        for r in rows:
            if r["view"] == "oblique":
                r["extrinsics_sha256"] = "1"*64
        with self.assertRaisesRegex(AdmissionError, "identical extrinsics"):
            assess(rows)

    def test_nonfinite_and_negative_depth_denied(self):
        for bad in (math.nan, math.inf, -1.):
            rows = fixture()
            rows[0]["xyz"][2] = bad
            with self.assertRaises(AdmissionError):
                assess(rows)

    def test_duplicate_id_or_untrusted_digest_denied(self):
        rows = fixture()
        rows[1]["point_id"] = rows[0]["point_id"]
        with self.assertRaisesRegex(AdmissionError, "repeated"):
            assess(rows)
        rows = fixture()
        rows[0]["source_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(AdmissionError, "SHA-256"):
            assess(rows)

    def test_no_unbounded_tolerance_or_forged_claim(self):
        with self.assertRaisesRegex(AdmissionError, "error budget"):
            assess(fixture(), 999)
        r = assess(fixture())
        self.assertEqual(r["independent_extrinsics"], "NOT_PROVEN")
        self.assertEqual(r["image_byte_capture"], "NOT_VERIFIED_BY_THIS_WORKCELL")
        self.assertFalse(r["model_mutation"])


if __name__ == "__main__":
    unittest.main()
