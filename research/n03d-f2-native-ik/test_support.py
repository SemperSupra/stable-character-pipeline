import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from support import bounded_sole_z,outcome
class SupportBounds(unittest.TestCase):
 def test_correct_small_penetration(self):self.assertAlmostEqual(bounded_sole_z(-.02),.022)
 def test_hard_limit(self):self.assertEqual(bounded_sole_z(-.10),.04)
 def test_hover_does_not_push_down(self):self.assertEqual(bounded_sole_z(.03),0)
 def test_nan_source(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):bounded_sole_z(math.nan)
 def test_root_budget(self):
  with self.assertRaisesRegex(ValueError,"BUDGET"):outcome([0]*7,[0]*7,.01,.03)
 def test_improve_not_green(self):
  v=outcome([-.09]*7,[-.05]*7,0,.04)
  self.assertAlmostEqual(v["penetration_improvement_m"],.04)
  self.assertFalse(v["after_sole_support_height_meets_10mm"])
  self.assertFalse(v["post_ik_natural_gait_accepted"])
 def test_worse_propagates(self):
  v=outcome([-.02]*7,[-.04]*7,0,.02)
  self.assertLess(v["penetration_improvement_m"],0)
 def test_missing_samples(self):
  with self.assertRaisesRegex(ValueError,"INSUFFICIENT"):outcome([-.02],[0],0,.02)
 def test_target_clamp_too_large(self):
  with self.assertRaisesRegex(ValueError,"BAD_TARGET"):bounded_sole_z(-.01,limit_m=.5)
if __name__=="__main__":unittest.main()
