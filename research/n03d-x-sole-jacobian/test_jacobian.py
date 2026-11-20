import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from jacobian import jacobian,update
class Calibration(unittest.TestCase):
 def test_identity_central_difference(self):
  step=.002
  plus=[[step if i==j else 0 for i in range(3)] for j in range(3)]
  minus=[[-x for x in q] for q in plus]
  j=jacobian(plus,minus,step)
  self.assertEqual(j,[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
 def test_damped_bounded(self):
  r=update([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]], [.1,0,0])
  self.assertLessEqual(math.dist(r["target_delta_m"],(0,0,0)),.010001)
  self.assertFalse(r["motion_physically_valid"])
 def test_crosscoupling(self):
  r=update([[1,1,0],[0,1,0],[0,0,1]], [.01,.01,0])
  self.assertLess(r["predicted_residual_m"][1],.01)
 def test_degenerate_source_warning(self):
  r=update([[0,0,0],[0,0,0],[0,0,0]],[0,0,-.1])
  self.assertTrue(r["jacobian_near_zero_rank_warning"])
 def test_nonfinite_refused(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):update([[math.nan,0,0],[0,1,0],[0,0,1]],[1,0,0])
 def test_bad_diff(self):
  with self.assertRaisesRegex(ValueError,"FD_STEP"):jacobian([[0,0,0]]*3,[[0,0,0]]*3,.1)
 def test_wrong_shape(self):
  with self.assertRaisesRegex(ValueError,"JACOBIAN_SHAPE"):update([[1,2],[3,4]],[0,0,0])
 def test_bad_trust(self):
  with self.assertRaisesRegex(ValueError,"REGULARIZATION"):update([[1,0,0],[0,1,0],[0,0,1]],[0,0,0],trust=1)
if __name__=="__main__":unittest.main()
