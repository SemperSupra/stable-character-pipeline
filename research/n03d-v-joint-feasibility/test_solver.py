import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from solver import SIDES,solve
def pair(n=4):
 return {SIDES[0]:[[0.,0.,0.] for _ in range(n)],
         SIDES[1]:[[1.,0.,0.] for _ in range(n)]}
class ContactOracle(unittest.TestCase):
 def test_static_needs_nothing(self):
  v=solve(pair(),"joint")
  self.assertEqual(v["objective_final"],0.)
  self.assertFalse(v["physical_contact_accepted"])
 def test_true_shared_root_displacement(self):
  a=pair()
  for s in SIDES:
   for t in range(1,4):a[s][t][2]=-.02
  v=solve(a,"root_only")
  self.assertLess(v["objective_final"],v["objective_initial"])
  self.assertLessEqual(v["max_root_correction_m"],.04+1e-6)
 def test_opposed_two_shoe_root_cannot_cure(self):
  a=pair()
  for t in range(1,4):
   a[SIDES[0]][t][2]=-.08;a[SIDES[1]][t][2]=.08
  root=solve(a,"root_only")
  joint=solve(a,"joint")
  self.assertLess(joint["objective_final"],root["objective_final"])
 def test_hard_budget(self):
  a=pair()
  for s in SIDES:
   a[s][3][2]=-.5
  v=solve(a,"joint")
  self.assertLessEqual(v["max_foot_correction_m"],.04+1e-6)
  self.assertGreater(v["max_ground_proxy_penetration_m"],.3)
 def test_monotone_and_no_false_stance(self):
  v=solve(pair(),"foot_only")
  self.assertTrue(v["energy_nonincreasing"])
  self.assertFalse(v["actual_native_after_correction_measured"])
 def test_timebase_mismatch(self):
  a=pair();a[SIDES[1]].pop()
  with self.assertRaisesRegex(ValueError,"SIDE_TIMEBASE"):solve(a,"joint")
 def test_nan_fails(self):
  a=pair();a[SIDES[0]][0][0]=math.nan
  with self.assertRaisesRegex(ValueError,"NONFINITE"):solve(a,"joint")
 def test_budget_fails(self):
  with self.assertRaisesRegex(ValueError,"BUDGET"):solve(pair(),"joint",bound=.5)
 def test_modes_independent(self):
  for mode in ("root_only","foot_only","joint"):
   self.assertEqual(solve(pair(),mode)["mode"],mode)
 def test_unknown_mode(self):
  with self.assertRaisesRegex(ValueError,"UNKNOWN"):solve(pair(),"invalid")
if __name__=="__main__":unittest.main()
