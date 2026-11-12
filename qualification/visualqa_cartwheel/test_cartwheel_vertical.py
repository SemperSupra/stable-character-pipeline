"""Exact analytic shared-pelvis reachability hostile controls."""
import math
import unittest
from cartwheel_vertical import shared_vertical_interval,least_absolute_shift,SUM

def make(hip_left, ankle_left, hip_right=None,ankle_right=None):
    return {"joints":{"left_hip":hip_left,"left_ankle":ankle_left,
                      "right_hip":hip_right or hip_left,
                      "right_ankle":ankle_right or ankle_left}}

class CartwheelFeasibilityTests(unittest.TestCase):
    def test_two_feasible_same_height_legs_have_zero_shift(self):
        f=make([0.,-.15,1.],[.1,-.15,.1],[0.,.15,1.],[.1,.15,.1])
        iv,_=shared_vertical_interval(f)
        self.assertIsNotNone(iv)
        self.assertEqual(least_absolute_shift(iv),0.)
    def test_two_legs_need_same_downward_correction(self):
        f=make([0.,-.15,1.2],[0.,-.15,.1],[0.,.15,1.2],[0.,.15,.1])
        iv,_=shared_vertical_interval(f)
        delta=least_absolute_shift(iv)
        self.assertLess(delta,-.05)
        for side in ("left","right"):
            h=list(f["joints"][side+"_hip"]);h[2]+=delta
            self.assertLess(math.dist(h,f["joints"][side+"_ankle"]),SUM)
    def test_impossible_horizontal_separation_has_no_vertical_solution(self):
        f=make([0.,-.15,1.],[2.0,-.15,.1])
        iv,_=shared_vertical_interval(f)
        self.assertIsNone(iv)
        self.assertIsNone(least_absolute_shift(iv))
    def test_contradictory_leg_height_intervals(self):
        f=make([0.,-.15,2.],[0.,-.15,0.],
               [0.,.15,-2.],[0.,.15,0.])
        iv,_=shared_vertical_interval(f)
        self.assertIsNone(iv)
    def test_never_claims_realism(self):
        iv,_=shared_vertical_interval(make([0.,0.,1.],[0.,0.,.2]))
        self.assertIsInstance(iv,list)
        self.assertEqual(len(iv),2)

if __name__=="__main__":
    unittest.main()
