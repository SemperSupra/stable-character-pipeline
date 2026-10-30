import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from linear_sweep import swept_aabb,separation,segment_bounds,THRESHOLD
class Adversarial(unittest.TestCase):
 def test_disjoint_swept_triangle_certified(self):
  a=[(-3.,0.,0.),(-2.9,0.,0.),(-3.,.1,0.)]
  b=[(3.,0.,0.),(3.1,0.,0.),(3.,.1,0.)]
  o={"a":a,"b":b};n={"a":a,"b":b}
  margin,count=segment_bounds(o,n,[(0,1,2)],[(0,1,2)],"a","b")
  self.assertEqual(count,1);self.assertGreater(margin,THRESHOLD)
 def test_endpoint_clear_midway_crossing_fail_closed(self):
  a=[(-1.,0.,0.),(-1.,.2,0.),(-1.,0.,.2)]
  b=[(1.,0.,0.),(1.,.2,0.),(1.,0.,.2)]
  old={"a":a,"b":b}
  new={"a":b,"b":a}
  with self.assertRaisesRegex(ValueError,"UNCERTIFIED_CONTINUOUS"):
   segment_bounds(old,new,[(0,1,2)],[(0,1,2)],"a","b")
 def test_triangle_sliding_along_edge_rejected(self):
  a=[(0.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
  b=[(.001,0.,0.),(.001,1.,0.),(.001,0.,1.)]
  x={"a":a,"b":b}
  with self.assertRaisesRegex(ValueError,"UNCERTIFIED_CONTINUOUS"):
   segment_bounds(x,x,[(0,1,2)],[(0,1,2)],"a","b")
 def test_very_near_touch_threshold(self):
  a=[(0.,0.,0.),(0.,1.,0.),(0.,0.,1.)]
  b=[(THRESHOLD,0.,0.),(THRESHOLD,1.,0.),(THRESHOLD,0.,1.)]
  o={"a":a,"b":b}
  with self.assertRaisesRegex(ValueError,"UNCERTIFIED_CONTINUOUS"):
   segment_bounds(o,o,[(0,1,2)],[(0,1,2)],"a","b")
 def test_nonfinite_guard(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE_SWEEP"):
   swept_aabb([(float("nan"),0.,0.),(0.,0.,0.),(0.,1.,0.)],[(0.,0.,0.)]*3,(0,1,2))
 def test_missing_triangles(self):
  x={"a":[(0.,0.,0.)],"b":[(1.,0.,0.)]}
  with self.assertRaisesRegex(ValueError,"NO_ACTUAL_TRIANGLE"):
   segment_bounds(x,x,[],[],"a","b")
if __name__=="__main__":unittest.main()
