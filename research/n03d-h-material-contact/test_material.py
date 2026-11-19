import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from material import compare_material_ids as metric
class Truth(unittest.TestCase):
 def test_still_foot(self):self.assertEqual(metric({1:(0,0)},{1:(0,0)},1/24)["max_mps"],0.)
 def test_true_slide(self):self.assertEqual(metric({1:(0,0)},{1:(.1,0)},1/24)["max_mps"],2.4)
 def test_centroid_vertex_switch_not_false_speed(self):
  x=metric({1:(0,0),2:(10,0)},{1:(0,0),3:(-10,0)},1/24)
  self.assertEqual(x["max_mps"],0.);self.assertEqual(x["persistent_vertices"],1)
 def test_disjoint_vertex_set_is_unknown(self):self.assertIsNone(metric({1:(0,0)},{2:(1,0)},1/24)["median_mps"])
 def test_zero_dt(self):
  with self.assertRaisesRegex(ValueError,"TIME_DELTA"):metric({}, {},0)
 def test_nonfinite(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):metric({1:(0,0)},{1:(math.nan,0)},1/24)
 def test_tail_speed_not_hidden_by_mean(self):
  a={i:(0.,0.) for i in range(20)}
  b={i:(.001 if i<19 else 1.,0.) for i in range(20)}
  x=metric(a,b,1/24);self.assertGreater(x["max_mps"],x["median_mps"])
if __name__=="__main__":unittest.main()
