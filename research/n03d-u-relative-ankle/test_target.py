import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from target import target,bounded_delta,reachability
class NativeTarget(unittest.TestCase):
 def test_axis(self):
  p=target((0,1,0),(1,0,0),(5,6,7),1,0)
  self.assertEqual(p,(6,6,6))
 def test_yaw(self):
  p=target((0,0,0),(1,0,0),(0,0,0),1,math.pi/2)
  self.assertAlmostEqual(p[1],1.)
 def test_cap(self):
  v=bounded_delta((0,0,0),(1,0,0))
  self.assertAlmostEqual(v[0],.04)
 def test_small(self):
  self.assertAlmostEqual(bounded_delta((0,0,0),(.01,0,0))[0],.01)
 def test_unreachable(self):
  self.assertFalse(reachability((0,0,0),(0,0,2),.5,.5)["two_segment_reachable"])
 def test_reachable_not_accepted(self):
  s=reachability((0,0,0),(0,0,.7),.5,.5)
  self.assertTrue(s["two_segment_reachable"]);self.assertFalse(s["foot_plant_accepted"])
 def test_nan(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):target((0,0,0),(math.nan,1,0),(0,0,0),1,0)
 def test_zero_scale(self):
  with self.assertRaisesRegex(ValueError,"SOURCE_MORPHOLOGY_SCALE"):target((0,0,0),(1,0,0),(0,0,0),0,0)
 def test_bad_budget(self):
  with self.assertRaisesRegex(ValueError,"BAD_CORRECTION_BOUND"):bounded_delta((0,0,0),(1,0,0),1)
if __name__=="__main__":unittest.main()
