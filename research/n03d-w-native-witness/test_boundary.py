import sys,math,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from boundary import validate
sys.path.insert(0,str(Path(__file__).parent.parent/"n03d-v-joint-feasibility"))
from solver import solve,SIDES
def source():return {SIDES[0]:[[0.,0.,-.02]]*4,SIDES[1]:[[1.,0.,.02]]*4}
class NativeBoundary(unittest.TestCase):
 def test_three_independent_mode_contracts(self):
  for m in ("root_only","foot_only","joint"):self.assertTrue(validate(solve(source(),m)))
 def test_native_spoof(self):
  r=solve(source(),"joint");r["actual_native_after_correction_measured"]=True
  with self.assertRaisesRegex(ValueError,"UNAUTHORIZED"):validate(r)
 def test_physics_spoof(self):
  r=solve(source(),"joint");r["physical_contact_accepted"]=True
  with self.assertRaisesRegex(ValueError,"UNAUTHORIZED"):validate(r)
 def test_nan(self):
  r=solve(source(),"joint");r["root_corrections_m"][0][0]=math.nan
  with self.assertRaisesRegex(ValueError,"NONFINITE"):validate(r)
 def test_budget(self):
  r=solve(source(),"joint");r["foot_corrections_m"][SIDES[0]][0]=[1,0,0]
  with self.assertRaisesRegex(ValueError,"MOVEMENT_BUDGET"):validate(r)
 def test_clock(self):
  r=solve(source(),"joint");r["root_corrections_m"].pop()
  with self.assertRaisesRegex(ValueError,"MISSING_ROOT"):validate(r)
if __name__=="__main__":unittest.main()
