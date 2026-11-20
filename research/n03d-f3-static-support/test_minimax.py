import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from minimax import enclosing_disk
class Minimax(unittest.TestCase):
 def test_static(self):
  d=enclosing_disk([[.01,.02],[.01,.02],[.01,.02]])
  self.assertAlmostEqual(d["minimax_radius_m"],0.)
 def test_two_points(self):
  self.assertAlmostEqual(enclosing_disk([[0,0],[.1,0]])["minimax_radius_m"],.05)
 def test_triangle(self):
  x=enclosing_disk([[0,0],[2,0],[1,math.sqrt(3)]])
  self.assertAlmostEqual(x["minimax_radius_m"],2/math.sqrt(3),places=6)
 def test_collinear(self):
  self.assertAlmostEqual(enclosing_disk([[0,0],[1,0],[.4,0]])["minimax_radius_m"],.5)
 def test_outlier_not_hidden(self):
  self.assertGreater(enclosing_disk([[0,0]]*10+[[2,0]])["minimax_radius_m"],.9)
 def test_infinite_rejected(self):
  with self.assertRaisesRegex(ValueError,"XY_NOT_FINITE"):enclosing_disk([[0,0],[float("nan"),0]])
 def test_bounded_input(self):
  with self.assertRaisesRegex(ValueError,"WINDOW_BOUNDS"):enclosing_disk([[0,0]]*33)
 def test_no_false_contact(self):
  self.assertFalse(enclosing_disk([[0,0],[0,0]])["stationary_support_proven"])
if __name__=="__main__":unittest.main()
