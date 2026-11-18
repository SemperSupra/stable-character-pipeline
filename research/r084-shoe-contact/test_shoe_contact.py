import math,unittest
from shoe_contact import quantify,point
class Contact(unittest.TestCase):
 def test_flat_stationary_is_diagnostic_not_accepted(self):
  r=quantify([point(0,(0,0)) for _ in range(12)],12)
  self.assertEqual(r["flags"],[])
  self.assertFalse(r["gait_contact_accepted"])
 def test_slide_rejected(self):
  r=quantify([point(0,(i*.02,0)) for i in range(12)],12)
  self.assertIn("PLANTED_FOOT_SLIDING",r["flags"])
 def test_penetration_rejected(self):
  r=quantify([point(-.03,(0,0)),point(0,(0,0))],12)
  self.assertIn("PENETRATION_OVER_10MM",r["flags"])
 def test_constant_hover_rejected(self):
  r=quantify([point(.08,(0,0)),point(.09,(0,0))],12)
  self.assertIn("NO_GROUND_PROXIMITY",r["flags"])
 def test_single_contact_unknown(self):
  r=quantify([point(.07,(0,0)),point(0,(0,0)),point(.07,(0,0))],12)
  self.assertIn("NO_TWO_CONSECUTIVE_CONTACT_SAMPLES",r["flags"])
 def test_nonfinite_rejected(self):
  with self.assertRaisesRegex(ValueError,"SOLE_Z_NONFINITE"):point(math.nan,(0,0))
 def test_nonfinite_xy(self):
  with self.assertRaisesRegex(ValueError,"SOLE_XY_NONFINITE"):point(0,(0,math.inf))
 def test_empty_track_rejected(self):
  with self.assertRaisesRegex(ValueError,"TOO_FEW_SHOE_SAMPLES"):quantify([],12)
 def test_unknown_frame_clock(self):
  with self.assertRaisesRegex(ValueError,"BAD_FRAME_CLOCK"):quantify([point(0,(0,0))]*2,0)
 def test_bad_schema(self):
  with self.assertRaisesRegex(ValueError,"INVALID_SHOE_SAMPLE"):quantify([{"z_m":0},{"z_m":0}],12)
 def test_separated_step_not_called_slip(self):
  r=quantify([point(0,(0,0)),point(.10,(10,0)),point(0,(20,0))],12)
  self.assertNotIn("PLANTED_FOOT_SLIDING",r["flags"])
if __name__=="__main__":unittest.main()
