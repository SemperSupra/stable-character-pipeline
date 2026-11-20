import math,unittest
from planar_support import fk,positions,jacobian,finite_angles,LINKS
class SupportOracle(unittest.TestCase):
 def test_zero_angle_endpoint(self):
  x,z,angle,phi=fk((0,0,0,0,0),(0,sum(LINKS)+.06))
  self.assertAlmostEqual(x,0.)
  self.assertAlmostEqual(z,.06)
  self.assertAlmostEqual(angle,0.)
 def test_sole_ground_at_zero(self):
  q=positions((0,0,0,0,0),(0,sum(LINKS)+.06))
  self.assertAlmostEqual(q[1],0.)
  self.assertAlmostEqual(q[3],0.)
  self.assertAlmostEqual(q[2]-q[0],.24)
 def test_jacobian_against_finite_difference(self):
  theta=(.21,-.24,.15,-.13,.01);p=(.03,.96);h=1e-6
  j=jacobian(theta,p)
  for k in range(5):
   a=list(theta);b=list(theta);a[k]+=h;b[k]-=h
   pa,pb=positions(a,p),positions(b,p)
   for i in range(4):
    self.assertAlmostEqual((pa[i]-pb[i])/(2*h),j[i][k],delta=1e-8)
 def test_duplicate_support_points_not_accepted(self):
  q=positions((0,0,0,0,0),(0,sum(LINKS)+.06))
  self.assertNotEqual((q[0],q[1]),(q[2],q[3]))
 def test_nonfinite(self):
  with self.assertRaisesRegex(ValueError,"UNSUPPORTED"):finite_angles((0,0,float("nan"),0,0))
 def test_overrotation(self):
  with self.assertRaisesRegex(ValueError,"UNSUPPORTED"):finite_angles((0,0,1.5,0,0))
 def test_boolean(self):
  with self.assertRaisesRegex(ValueError,"UNSUPPORTED"):finite_angles((0,True,0,0,0))
 def test_joint_number(self):
  with self.assertRaisesRegex(ValueError,"FIVE_ANGLE_LAYOUT"):finite_angles((0,0,0))
 def test_bad_pelvis(self):
  with self.assertRaisesRegex(ValueError,"PELVIS_LAYOUT"):positions((0,0,0,0,0),(0,float("nan")))
if __name__=="__main__":unittest.main()
