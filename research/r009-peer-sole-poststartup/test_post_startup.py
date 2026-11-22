"""Adversarial 360-frame original shoe startup/poststartup independent oracle."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from post_startup import summarize,build

def rows():
    return [{"frame":i,"t":round(i/60,9),
             "heel_xy":[0.,0.],"ball_xy":[.2,0.],
             "heel_min_z":.003,"ball_min_z":.003,
             "world_shoe_side_min_z":.003} for i in range(360)]

def report():
    x=rows()
    return {"schema":"scp.r009.peer-original-native360-shoe-fullclip-v1",
            "source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
            "source_60hz_frame_count":360,
            "physical_contact_accepted":False,
            "protected_likeness_used":False,
            "exact_native_blend_sha256":"e"*64,
            "actors":[{"name":name,"sides":{
                s:{"rows":x,"metrics":summarize(x)["fullclip_replayed_same_original_metrics"]}
                for s in ("L","R")}}
                for name in ("AsterOriginal","JuniperOriginal")]}

class TestPoststartup(unittest.TestCase):
    def test_first_edge_is_retained_but_ignored_for_later_peak(self):
        x=rows()
        for i in range(1,360):x[i]["heel_xy"][0]=1.
        for i in range(200,360):x[i]["heel_xy"][0]=1.02
        r=summarize(x)["speed_by_region"]["heel"]
        self.assertEqual(r["all_359_edges_including_first_peak_destination_frame"],1)
        self.assertEqual(r["post_startup_peak_destination_frame"],200)
        self.assertAlmostEqual(r["first_edge_0_to_1_speed_mps"],60.)
        self.assertAlmostEqual(r["post_startup_1_to_359_speed_max_mps"],1.2)

    def test_negative_ground_is_actual_mesh_penetration_not_contact_proof(self):
        x=rows()
        for i in range(100,125):x[i]["world_shoe_side_min_z"]=-.03
        r=summarize(x)
        self.assertEqual(r["all_360_frames_below_floor"],25)
        self.assertEqual(r["all_360_frames_penetration_gt_25mm"],25)
        self.assertAlmostEqual(r["whole_clip_penetration_mm"],30.)
        self.assertFalse(r["true_planted_contact_proven"])

    def test_poststartup_near_ground_gate_does_not_claim_stance(self):
        x=rows()
        for i in range(3,360):x[i]["heel_xy"][1]=i*.2
        r=summarize(x)
        self.assertEqual(r["speed_by_region"]["heel"]["post_startup_near_plane_candidate_pairs"],358)
        self.assertGreater(r["speed_by_region"]["heel"]["post_startup_near_plane_candidate_max_mps"],10.)
        self.assertFalse(r["ground_reaction_force_measured"])

    def test_zero_eligible_near_ground_is_not_zero_slip(self):
        x=rows()
        for row in x:row["world_shoe_side_min_z"]=.1
        r=summarize(x)
        self.assertEqual(r["speed_by_region"]["ball"]["post_startup_near_plane_candidate_pairs"],0)
        self.assertIsNone(r["speed_by_region"]["ball"]["post_startup_near_plane_candidate_max_mps"])

    def test_false_frame_count_and_nonfinite_rejected(self):
        with self.assertRaises(ValueError):summarize(rows()[:-1])
        for invalid in (math.nan,math.inf,True):
            x=rows()
            x[101]["world_shoe_side_min_z"]=invalid
            with self.subTest(value=invalid),self.assertRaises(ValueError):summarize(x)

    def test_build_fails_wrong_protected_source_and_malformed_metrics(self):
        x=report()
        self.assertEqual(build(x)["status"],"HOLD")
        x["protected_likeness_used"]=True
        with self.assertRaises(ValueError):build(x)
        x=report()
        x["actors"][0]["sides"]["L"]["metrics"]["max_actual_geometry_penetration_m"]=100.
        with self.assertRaisesRegex(ValueError,"ORIGINAL_FULLCLIP_METRIC_DRIFT"):build(x)

    def test_near_ground_negative_5mm_is_only_candidate(self):
        x=rows()
        x[10]["world_shoe_side_min_z"]=-.004
        x[11]["world_shoe_side_min_z"]=-.004
        r=summarize(x)
        self.assertGreaterEqual(r["speed_by_region"]["ball"]["post_startup_near_plane_candidate_pairs"],1)
        self.assertFalse(r["true_planted_contact_proven"])

if __name__=="__main__":unittest.main()
