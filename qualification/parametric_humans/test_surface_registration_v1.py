import copy
import unittest
from surface_registration_v1 import SCHEMA, FitRejected, fit_once


def fixture(offset=0.04):
    return {
        "schema": SCHEMA,
        "options": {"max_normal_step_m": .05, "max_tangent_step_m": .02,
                    "min_confidence": .7, "max_triangle_area_ratio": 2.0},
        "vertices": [[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 0.]],
        "normals": [[0., 0., 1.]] * 4,
        "triangles": [[0, 1, 2], [0, 2, 3]],
        "correspondences": [{"status": "ADMITTED", "surface": "BODY",
                             "point": [x, y, offset], "confidence": 1.}
                            for x, y in [(0., 0.), (1., 0.), (1., 1.), (0., 1.)]],
    }


class RegistrationTests(unittest.TestCase):
    def test_positive_normal(self):
        r = fit_once(fixture())
        self.assertEqual(r["stats"]["positive_normal"], 4)
        self.assertTrue(all(abs(v[2] - .04) < 1e-9 for v in r["vertices"]))
        self.assertFalse(r["motion_accepted"])

    def test_negative_normal(self):
        r = fit_once(fixture(-.03))
        self.assertEqual(r["stats"]["negative_normal"], 4)
        self.assertAlmostEqual(r["vertices"][0][2], -.03)

    def test_clips_outlier(self):
        r = fit_once(fixture(.40))
        self.assertEqual(r["stats"]["clamped"], 4)
        self.assertAlmostEqual(r["vertices"][0][2], .05)

    def test_holds_clothing_and_unknown(self):
        f = fixture()
        f["correspondences"][0] = {"status": "HOLD"}
        f["correspondences"][1] = {"status": "UNKNOWN"}
        r = fit_once(f)
        self.assertEqual(r["stats"]["held"], 1)
        self.assertEqual(r["stats"]["unknown"], 1)
        self.assertEqual(r["vertices"][0], f["vertices"][0])

    def test_denies_nonbody(self):
        f = fixture()
        f["correspondences"][0]["surface"] = "CLOTHING"
        with self.assertRaisesRegex(FitRejected, "NONANATOMICAL"):
            fit_once(f)

    def test_denies_unknown_admission(self):
        f = fixture()
        f["correspondences"][0]["status"] = "UNVERIFIED"
        with self.assertRaisesRegex(FitRejected, "UNADMITTED"):
            fit_once(f)

    def test_denies_nan(self):
        f = fixture()
        f["vertices"][0][0] = float("nan")
        with self.assertRaisesRegex(FitRejected, "NONFINITE"):
            fit_once(f)

    def test_denies_bad_face(self):
        f = fixture()
        f["triangles"] = [[0, 0, 1]]
        with self.assertRaisesRegex(FitRejected, "INVALID_TRIANGLE"):
            fit_once(f)

    def test_denies_deformation_inversion(self):
        f = fixture(0.)
        f["normals"] = [[1., 0., 0.]] * 4
        f["options"]["max_normal_step_m"] = .25
        # Project corner past opposite side, reversing the first triangle.
        f["correspondences"][2]["point"] = [1., -4., 0.]
        f["options"]["max_tangent_step_m"] = .25
        # Tangential clamp limits it, so deliberately invert by moving 3 vertices.
        for i in (0, 1, 2):
            f["correspondences"][i]["point"] = [f["vertices"][i][0], f["vertices"][i][1], 0.]
        f["correspondences"][0]["point"] = [0., 0.2, 0.]
        f["correspondences"][1]["point"] = [1., -0.2, 0.]
        f["correspondences"][2]["point"] = [1., -0.1, 0.]
        # Not necessarily inverted under bounded movement; test actual checker with distorted cell.
        f["vertices"] = [[0., 0., 0.], [.1, 0., 0.], [.1, .1, 0.], [0., .1, 0.]]
        f["correspondences"][1]["point"] = [.1, .2, 0.]
        f["correspondences"][2]["point"] = [.1, 0., 0.]
        with self.assertRaises(FitRejected):
            fit_once(f)

    def test_accepts_lateral(self):
        f = fixture()
        for obs in f["correspondences"]:
            obs["point"][0] += .01
        r = fit_once(f)
        self.assertEqual(r["stats"]["lateral"], 4)
        self.assertAlmostEqual(r["vertices"][0][0], .01)

    def test_bad_confidence(self):
        f = fixture()
        f["correspondences"][0]["confidence"] = float("inf")
        with self.assertRaisesRegex(FitRejected, "CONFIDENCE"):
            fit_once(f)

    def test_low_confidence_abstains(self):
        f = fixture()
        f["correspondences"][0]["confidence"] = .1
        r = fit_once(f)
        self.assertEqual(r["stats"]["unknown"], 1)


if __name__ == "__main__":
    unittest.main()
