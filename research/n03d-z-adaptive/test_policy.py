import unittest,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from policy import screen,select
class NativeTrust(unittest.TestCase):
 def test_real_improvement(self):
  q=screen([.05,0,0],[.045,0,0],[.0452,0,0],[-.005,0,0],1,.005)
  self.assertTrue(q["numeric_candidate_admissible"])
  self.assertFalse(q["native_physical_contact_accepted"])
 def test_model_mismatch_rejected(self):
  q=screen([.05,0,0],[.045,0,0],[.03,0,0],[-.005,0,0],1,.005)
  self.assertEqual(q["reason"],"MODEL_MISMATCH")
 def test_jacobian_sensitive_rejected(self):
  q=screen([.05,0,0],[.04,0,0],[.04,0,0],[-.005,0,0],50,.005)
  self.assertEqual(q["reason"],"JACOBIAN_SENSITIVE")
 def test_worsening_rejected(self):
  q=screen([.05,0,0],[.06,0,0],[.06,0,0],[-.005,0,0],1,.005)
  self.assertEqual(q["reason"],"NO_REAL_RESIDUAL_IMPROVEMENT")
 def test_budget_reject(self):
  with self.assertRaisesRegex(ValueError,"TRUST_EXCEEDED"):screen([0,0,0],[0,0,0],[0,0,0],[.05,0,0],1,.005)
 def test_nonfinite(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):screen([math.nan,0,0],[0,0,0],[0,0,0],[0,0,0],1,.005)
 def test_no_pass_without_numeric_candidate(self):
  a=screen([0,0,0],[0,0,0],[0,0,0],[0,0,0],1,.005)
  r=select([{"trust_radius_m":.005,"assessment":a}])
  self.assertTrue(r["no_numerical_candidate"])
  self.assertFalse(r["physical_footplant_accepted"])
 def test_best_is_numerical_not_physical(self):
  a=screen([.05,0,0],[.04,0,0],[.04,0,0],[-.005,0,0],1,.005)
  b=screen([.05,0,0],[.045,0,0],[.045,0,0],[-.002,0,0],1,.002)
  r=select([{"trust_radius_m":.005,"assessment":a},{"trust_radius_m":.002,"assessment":b}])
  self.assertEqual(r["chosen_trust_radius_m"],.005)
  self.assertFalse(r["physical_footplant_accepted"])
if __name__=="__main__":unittest.main()
