"""Hostile tests: numerical improvements must never imply verified shoe contact."""
import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from policy import assess, kinematics


def fixture():
    windows = []
    for actor in ("AsterOriginal", "JuniperOriginal"):
        for side in ("L", "R"):
            for start in (24, 48):
                w = {"actor": actor, "side": side, "start_sample_24hz": start,
                     "persistent_vertex_count": 32}
                for fps in (24, 60):
                    dt = 1/fps
                    times = [start/24 + j*dt for j in range(4 if fps == 24 else 8)]
                    if fps == 60:
                        times.append((start+3)/24)
                    for mode in ("source", "candidate"):
                        w[mode + "_" + str(fps)] = [
                            {"time_s": t, "xy_m": [(t-start/24)*(.2 if mode == "source" else .001), 0.],
                             "min_z_m": -.09 if mode == "source" else -.07,
                             "ik_delta_m": 0. if mode == "source" else .008,
                             "max_joint_pose_rotation_rad": .1,
                             "nonlinear_gap_m": .0003}
                            for t in times]
                windows.append(w)
    return {"schema": "scp.n03d-ab.native-material-temporal-ik.v1",
            "source_class": "ORIGINAL_FICTIONAL_CC0",
            "source_scene_sha256": "a"*64, "source_trace_sha256": "b"*64,
            "source_100style_sha256": "c"*64, "windows": windows,
            "source_motion_changed": False, "corrected_blend_saved": False,
            "physical_contact_accepted": False, "mvp_accepted": False}


class TemporalMaterialPolicy(unittest.TestCase):
    def test_provenance_complete_but_contact_held(self):
        r = assess(fixture())
        self.assertEqual(r["status"], "HOLD")
        self.assertEqual(len(r["windows"]), 8)
        self.assertFalse(r["physical_contact_accepted"])

    def test_even_perfect_numerical_contact_never_admits(self):
        x = fixture()
        for w in x["windows"]:
            for fps in (24, 60):
                for point in w["candidate_"+str(fps)]:
                    point["min_z_m"] = 0.
                    point["xy_m"] = [0., 0.]
        r = assess(x)
        self.assertEqual(r["status"], "HOLD")
        self.assertIn("SOURCE_STANCE_UNKNOWN", r["windows"][0]["reasons"])

    def test_nan_rejected(self):
        x = fixture()
        x["windows"][0]["candidate_60"][0]["xy_m"][0] = math.nan
        with self.assertRaisesRegex(ValueError, "NONFINITE"):
            assess(x)

    def test_time_skip_rejected(self):
        x = fixture()
        x["windows"][0]["candidate_60"][2]["time_s"] += .1
        with self.assertRaisesRegex(ValueError, "IRREGULAR_TIMEBASE"):
            assess(x)

    def test_heldout_endpoint_rejected(self):
        x = fixture()
        x["windows"][0]["candidate_60"][8]["time_s"] += .01
        with self.assertRaisesRegex(ValueError, "MISALIGNED_HELDOUT_ENDPOINT"):
            assess(x)

    def test_duplicate_window_rejected(self):
        x = fixture()
        x["windows"][1] = copy.deepcopy(x["windows"][0])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_WINDOW"):
            assess(x)

    def test_private_rights_rejected(self):
        x = fixture()
        x["source_class"] = "PROTECTED_NAOMI"
        with self.assertRaisesRegex(ValueError, "RIGHTS"):
            assess(x)

    def test_source_mutation_rejected(self):
        x = fixture()
        x["source_motion_changed"] = True
        with self.assertRaisesRegex(ValueError, "SOURCE_MUTATION"):
            assess(x)

    def test_false_contact_claim_rejected(self):
        x = fixture()
        x["physical_contact_accepted"] = True
        with self.assertRaisesRegex(ValueError, "FORGED_ACCEPTANCE"):
            assess(x)

    def test_ik_budget_rejected(self):
        x = fixture()
        x["windows"][0]["candidate_24"][1]["ik_delta_m"] = .015
        with self.assertRaisesRegex(ValueError, "IK_TRUST_BUDGET"):
            assess(x)

    def test_pose_bound(self):
        x = fixture()
        x["windows"][0]["candidate_24"][1]["max_joint_pose_rotation_rad"] = 5.
        with self.assertRaisesRegex(ValueError, "NEGATIVE_POSE_OR_GAP"):
            assess(x)

    def test_clock_count_rejected(self):
        x = fixture()
        x["windows"][0]["candidate_60"].pop()
        with self.assertRaisesRegex(ValueError, "SAMPLE_RATE_LENGTH"):
            assess(x)

    def test_fake_removed_contact_rejected(self):
        x = fixture()
        for w in x["windows"]:
            for p in w["candidate_60"]:
                p["min_z_m"] = .5
        r = assess(x)
        self.assertIn("UNKNOWN_CONSECUTIVE_CONTACT", r["windows"][0]["reasons"])

    def test_third_party_identity_rejected(self):
        x = fixture()
        x["windows"][0]["actor"] = "Naomi"
        with self.assertRaisesRegex(ValueError, "ACTOR_SIDE_FRAME"):
            assess(x)


if __name__ == "__main__":
    unittest.main()
