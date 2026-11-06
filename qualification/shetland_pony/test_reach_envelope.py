import unittest
from reach_envelope import screen,reach_margin,MIN_MARGIN_M
class Reach(unittest.TestCase):
 def test_planted_3_link_reach(self):
    r=screen()
    self.assertEqual(r["engineering_verdict"],"REACH_MARGIN_PASS",r)
    for foot,p in r["feet"].items():
        self.assertGreaterEqual(p["minimum_margin_m"],MIN_MARGIN_M)
 def test_four_legs_and_cycle(self):
    for foot in ("front_L","front_R","hind_L","hind_R"):
      self.assertGreater(reach_margin(foot,1)["limb_length_m"],.5)
      self.assertGreater(reach_margin(foot,48)["margin_m"],0)
 def test_provisional_not_physical(self):
    self.assertEqual(screen()["physical_contact"],"NOT_MEASURED")
if __name__=="__main__":unittest.main()
