"""Adversarial controls for independent full-edge and original 60Hz tail observability."""
import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from peer_edges import observe, assess
from test_trace import fixtures, document


class NativeFullEdgeCritic(unittest.TestCase):
    def test_valid_360_reference_narrow_hold(self):
        rows=fixtures(False)
        r=observe(rows)
        self.assertEqual(r["edge_count"],359)
        self.assertEqual(r["max_target_planar_speed_mps"],0.0)
        self.assertFalse(r["physical_contact_accepted"])
        self.assertEqual(r["status"],"HOLD")

    def test_toeoff_jump_not_masked_by_phase(self):
        rows=fixtures(False)
        # Coherently teleport the entire post-switch native foot trajectory by 1 m.
        for row in rows[120:]:
            row["target_foot"][0]+=1.0
        r=observe(rows)
        self.assertGreater(r["max_target_planar_speed_mps"],50.0)
        self.assertEqual(r["first_large_edge_destination_frame"],120)
        self.assertEqual(r["max_speed_edge_destination_frame"],120)
        self.assertGreater(r["max_target_planar_accel_mps2"],1000.0)

    def test_missing_source_tail_is_visible_not_synthesized(self):
        rows=fixtures(False)
        # Original source moves at 60Hz while legacy target freezes after 355.
        for i in range(356,360):
            rows[i]["source_ankle"][0] = (i-355)*0.01
        r=observe(rows)
        self.assertTrue(r["tail_motion_disagreement_observed"])
        self.assertAlmostEqual(r["source_last_four_planar_path_m"],0.04)
        self.assertEqual(r["target_last_four_planar_path_m"],0.0)
        self.assertFalse(r["native_motion_repaired"])

    def test_tail_dropped_rejected(self):
        with self.assertRaisesRegex(ValueError,"EXACT_360_ROWS"):
            observe(fixtures(False)[:-4])

    def test_time_origin_corruption_rejected(self):
        rows=fixtures(False)
        rows[0]["time_s"]=1/60.0
        with self.assertRaisesRegex(ValueError,"TIMEBASE"):
            observe(rows)

    def test_nonfinite_native_or_original_rejected(self):
        for key in ("source_ankle","target_foot"):
            rows=fixtures(False)
            rows[200][key][0]=math.nan
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"POINT_FINITE"):
                observe(rows)

    def test_duplicate_side_and_forged_acceptance_rejected(self):
        doc=document(fixtures(False))
        self.assertEqual(len(assess(doc)["results"]),4)
        doc["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"PROVENANCE"):
            assess(doc)
        doc["mvp_accepted"]=False
        doc["actors"][1]["name"]=doc["actors"][0]["name"]
        with self.assertRaisesRegex(ValueError,"SIDE"):
            assess(doc)


if __name__=="__main__":
    unittest.main()
