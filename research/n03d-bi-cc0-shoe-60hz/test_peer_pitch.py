"""Adversarial dimensional checks for original CC0 outsole pitch witness."""
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from peer_pitch_geometry import measure

class OriginalOutsolePitchGeometry(unittest.TestCase):
    def test_horizontal_span_gives_atan2_not_false_asin(self):
        r=measure((0,0,.085),(0,.220,0))
        self.assertAlmostEqual(r["observed_world_pitch_deg"],math.degrees(math.atan2(.085,.220)),places=5)
        self.assertLess(r["observed_world_pitch_deg"],22.7)
        self.assertLess(r["atan2_asin_agreement_deg"],1e-8)

    def test_sloped_chord_22cm_gives_asin(self):
        horizontal=math.sqrt(.220**2-.085**2)
        r=measure((0,0,.085),(0,horizontal,0))
        self.assertAlmostEqual(r["observed_world_pitch_deg"],math.degrees(math.asin(.085/.220)),places=5)
        self.assertAlmostEqual(r["sloped_heel_ball_chord_m"],.220,places=7)

    def test_reversed_heel_ball_sign(self):
        r=measure((0,0,0),(0,.22,.085))
        self.assertLess(r["observed_world_pitch_deg"],0.0)
        self.assertFalse(r["physical_contact_accepted"])

    def test_flat_sole(self):
        r=measure((0,0,.01),(0,.21,.01))
        self.assertEqual(r["observed_world_pitch_deg"],0.0)

    def test_reject_degenerate_and_nonfinite(self):
        for heel,ball,reason in (
            ((0,0,0),(0,0,0),"SHOE_LONGITUDINAL"),
            ((0,0,0),(0,0.005,0),"SHOE_LONGITUDINAL"),
            ((0,0,0),(0,math.nan,0),"POINT_FINITE"),
            ((0,0,0),(0,math.inf,0),"POINT_FINITE"),
            ((0,0,0),(0,1),"POINT_SHAPE")):
            with self.subTest(reason=reason),self.assertRaisesRegex(ValueError,reason):
                measure(heel,ball)

    def test_rights_not_implied_from_trigonometry(self):
        r=measure((0,0,.085),(0,.22,0))
        self.assertFalse(r["anatomical_heel_ball_verified"])
        self.assertFalse(r["physical_contact_accepted"])

if __name__=="__main__":
    unittest.main()
