"""Adversarial original-only first-edge repeat and attribution controls."""
import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from first_edge_oracle import evaluate, SEQ


def base_side(frame):
    return {"heel_xy":[0.,0.01*frame],
            "ball_xy":[0.2,0.01*frame],
            "heel_min_z":0.005,"ball_min_z":0.006,
            "world_shoe_side_min_z":0.002}

def fixture():
    baseline={s:[base_side(i) for i in range(360)] for s in ("L","R")}
    records=[]
    for i in SEQ:
        records.append({"frame":i,
                        "shoe":{s:base_side(i) for s in ("L","R")},
                        "bones":{s:{"foot":[0.,i*.01,0.1],
                                     "toe":[0.,i*.01+.2,0.1]} for s in ("L","R")},
                        "pose_sha256":(str(i%10)*64),
                        "body_sha256":(str((i+4)%10)*64)})
    return records,baseline


class TestFirstEdge(unittest.TestCase):
    def test_source_only_first_edge_stays_hold(self):
        rec,src=fixture()
        o=evaluate(rec,src)
        self.assertEqual(o["repeated_evaluation"],"PASS_NARROW")
        self.assertFalse(o["source_fk_comparison_accepted"])
        self.assertFalse(o["physical_contact_accepted"])
        self.assertEqual(o["status"],"HOLD")
        self.assertAlmostEqual(o["material"]["L"]["heel_first_edge_speed_mps"],0.6)

    def test_real_two_frame_replay_drift_red(self):
        rec,src=fixture()
        rec[2]["shoe"]["L"]["heel_xy"][0]=0.05
        o=evaluate(rec,src)
        self.assertEqual(o["repeated_evaluation"],"RED")
        self.assertAlmostEqual(o["max_repeat_shoe_coordinate_drift_m"],0.05)

    def test_state_history_bone_drift_red(self):
        rec,src=fixture()
        rec[5]["bones"]["R"]["toe"][0]=0.08
        o=evaluate(rec,src)
        self.assertEqual(o["repeated_evaluation"],"RED")
        self.assertAlmostEqual(o["max_repeat_bone_coordinate_drift_m"],0.08)

    def test_same_shoe_different_skin_hash_red(self):
        rec,src=fixture()
        rec[3]["body_sha256"]="b"*64
        o=evaluate(rec,src)
        self.assertFalse(o["body_sha_consistent"])
        self.assertEqual(o["repeated_evaluation"],"RED")

    def test_disagreement_with_prior_fullclip_red(self):
        rec,src=fixture()
        src["R"][1]["ball_xy"][0]+=0.15
        o=evaluate(rec,src)
        self.assertEqual(o["repeated_evaluation"],"RED")
        self.assertAlmostEqual(o["max_vs_fullclip_first_edge_drift_m"],0.15)

    def test_nonfinite_bool_and_forged_frame_rejected(self):
        for key,value in (("nan",math.nan),("inf",math.inf),("bool",True)):
            rec,src=fixture()
            rec[1]["shoe"]["L"]["heel_xy"][0]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                evaluate(rec,src)
        rec,src=fixture()
        rec[3]["frame"]=2
        with self.assertRaisesRegex(ValueError,"FIRST_EDGE_FRAME_ORDER"):
            evaluate(rec,src)

    def test_truncated_and_invalid_root_baseline_rejected(self):
        rec,src=fixture()
        src["L"].pop()
        with self.assertRaisesRegex(ValueError,"SOURCE_BASELINE_360"):
            evaluate(rec,src)
        rec,src=fixture()
        rec.pop()
        with self.assertRaisesRegex(ValueError,"FIRST_EDGE_TRACE_MISSING"):
            evaluate(rec,src)

    def test_body_pose_digest_drift_red(self):
        rec,src=fixture()
        rec[6]["pose_sha256"]="f"*64
        o=evaluate(rec,src)
        self.assertFalse(o["pose_sha_consistent"])
        self.assertEqual(o["repeated_evaluation"],"RED")


if __name__=="__main__":
    unittest.main()
