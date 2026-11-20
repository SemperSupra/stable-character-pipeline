import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from score import relative,diagnostic
class Scores(unittest.TestCase):
 def test_better_but_not_physical(self):
  s=diagnostic(.5,.1)
  self.assertTrue(s["speed_reduction_over_25pct"])
  self.assertFalse(s["physical_planted_contact_accepted"])
 def test_much_worse(self):
  self.assertEqual(relative(.8,.2),4.)
 def test_equal(self):
  self.assertEqual(relative(.5,.5),1.)
 def test_zero_baseline_unknown(self):
  self.assertIsNone(relative(.5,0))
 def test_unknown_source(self):
  self.assertIsNone(relative(None,.5))
 def test_negative_rejected(self):
  with self.assertRaisesRegex(ValueError,"SPEED_NONFINITE"):relative(-1,.5)
 def test_nan_rejected(self):
  with self.assertRaisesRegex(ValueError,"SPEED_NONFINITE"):relative(math.nan,.5)
 def test_candidate_not_promoted(self):
  self.assertFalse(diagnostic(.5,0)["physical_planted_contact_accepted"])
if __name__=="__main__":unittest.main()
