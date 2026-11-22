"""Hostile full source-clock shoe material oracle controls, physical HOLD."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from shoe360_metrics import analyze


def fixture():
    return [{
        "frame":i,"t":round(i/60,9),
        "heel_xy":[0.0,0.0],"ball_xy":[0.20,0.0],
        "heel_min_z":0.005,"ball_min_z":0.005,
        "world_shoe_side_min_z":0.005,
    } for i in range(360)]


class TrueNativeShoeMetrics(unittest.TestCase):
    def test_narrow_360_synthetic_hold(self):
        r=analyze(fixture())
        self.assertEqual(r["source_frame_edges"],359)
        self.assertEqual(r["max_heel_material_region_speed_mps"],0)
        self.assertFalse(r["physical_contact_accepted"])
        self.assertFalse(r["ground_reaction_force_measured"])

    def test_360_last_four_not_synthesized(self):
        x=fixture()
        for i in range(356,360):
            x[i]["heel_xy"][0]=(i-355)*0.01
            x[i]["ball_xy"][0]=0.20+(i-355)*0.01
        r=analyze(x)
        self.assertAlmostEqual(r["last_four_heel_material_path_m"],0.04,places=8)
        self.assertAlmostEqual(r["last_four_ball_material_path_m"],0.04,places=8)

    def test_phase_switch_full_edge_spike_visible(self):
        x=fixture()
        for row in x[100:]:
            row["heel_xy"][0]+=1.0
            row["ball_xy"][0]+=1.0
        r=analyze(x)
        self.assertGreater(r["max_heel_material_region_speed_mps"],50.0)
        self.assertGreater(r["max_ball_material_region_speed_mps"],50.0)

    def test_actual_negative_floor_gap_cannot_claim_contact(self):
        x=fixture()
        x[160]["world_shoe_side_min_z"]=-0.025
        r=analyze(x)
        self.assertAlmostEqual(r["max_actual_geometry_penetration_m"],0.025)
        self.assertFalse(r["physical_contact_accepted"])

    def test_actual_peak_frame_is_not_hidden_by_clip_maximum(self):
        x=fixture()
        for row in x[100:]:
            row["heel_xy"][0]+=1.0
            row["ball_xy"][0]+=1.0
        result=analyze(x)
        self.assertEqual(result["max_heel_speed_destination_frame"],100)
        self.assertEqual(result["max_ball_speed_destination_frame"],100)
        self.assertEqual(result["max_heel_near_ground_destination_frame"],100)
        self.assertEqual(result["max_ball_near_ground_destination_frame"],100)
        self.assertEqual(result["max_heel_speed_signed_xy_delta_m"],[1.0,0.0])
        self.assertEqual(result["max_ball_speed_signed_xy_delta_m"],[1.0,0.0])

    def test_minimum_actual_geometry_penetration_frame(self):
        x=fixture()
        x[160]["world_shoe_side_min_z"]=-0.025
        result=analyze(x)
        self.assertEqual(result["min_world_shoe_z_frame"],160)
        self.assertEqual(result["max_actual_geometry_penetration_m"],0.025)

    def test_false_356_frames_rejected(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_60HZ_NOT_360"):
            analyze(fixture()[:-4])

    def test_corrupt_index_rejected(self):
        x=fixture();x[358]["frame"]=357
        with self.assertRaisesRegex(ValueError,"SOURCE_FRAME_INDEX"):
            analyze(x)

    def test_corrupt_time_rejected(self):
        x=fixture();x[359]["t"]=359/12
        with self.assertRaisesRegex(ValueError,"SOURCE_SAMPLE_TIME"):
            analyze(x)

    def test_nan_inf_and_bool_rejected(self):
        for k,v in (("heel_xy",math.nan),("ball_xy",math.inf),("heel_min_z",True)):
            x=fixture()
            if k.endswith("_xy"):
                x[10][k][0]=v
            else:
                x[10][k]=v
            with self.subTest(key=k),self.assertRaises(ValueError):
                analyze(x)


if __name__=="__main__":
    unittest.main()
