import math,unittest
from floor_math import lift_for_min_z
class FloorCorrection(unittest.TestCase):
 def test_no_lift_above_ground(self):self.assertEqual(lift_for_min_z(.04),0.)
 def test_no_lift_at_zero(self):self.assertEqual(lift_for_min_z(0),0.)
 def test_penetration_margin(self):self.assertAlmostEqual(lift_for_min_z(-.05),.053)
 def test_max_envelope(self):
  with self.assertRaisesRegex(ValueError,"ROOT_LIFT_OVER_ENVELOPE"):lift_for_min_z(-.14)
 def test_nonfinite_nan(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE_SOLE_HEIGHT"):lift_for_min_z(math.nan)
 def test_nonfinite_inf(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE_SOLE_HEIGHT"):lift_for_min_z(math.inf)
 def test_bool_rejected(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE_SOLE_HEIGHT"):lift_for_min_z(True)
 def test_repeatable(self):self.assertEqual([lift_for_min_z(-.02944)]*2,[.03244]*2)
if __name__=="__main__":unittest.main()
