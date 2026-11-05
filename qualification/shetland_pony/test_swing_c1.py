import unittest,math
from footpaths import target,CYCLE_FRAMES,STRIDE_M,DUTY_FACTOR,FOOT_CONTACT_PHASE

class ContactC1(unittest.TestCase):
 def test_physical_stance_world_lock(self):
    for foot in FOOT_CONTACT_PHASE:
      for frame in range(2,49):
        a=target(frame-1,foot);b=target(frame,foot)
        if a.state==b.state=="stance_planned" and b.phase>a.phase:
            self.assertAlmostEqual(a.ankle_x,b.ankle_x,places=9)
 def test_endpoints_and_both_sided_velocity_match(self):
    # Direct analytic check of the exact swing Hermite boundary derivatives.
    p0=.08-STRIDE_M*DUTY_FACTOR;p1=.08;m=-STRIDE_M*(1-DUTY_FACTOR)
    def p(u):
      return ((2*u**3-3*u*u+1)*p0 + (u**3-2*u*u+u)*m
        +(-2*u**3+3*u*u)*p1 + (u**3-u*u)*m)
    self.assertAlmostEqual(p(0),p0);self.assertAlmostEqual(p(1),p1)
    h=1e-6
    self.assertAlmostEqual((p(h)-p(0))/h/(1-DUTY_FACTOR),-STRIDE_M,delta=1e-4)
    self.assertAlmostEqual((p(1)-p(1-h))/h/(1-DUTY_FACTOR),-STRIDE_M,delta=1e-4)
 def test_planned_hoof_clearance(self):
    for f in FOOT_CONTACT_PHASE:
      p=[target(i,f) for i in range(1,CYCLE_FRAMES+1)]
      self.assertEqual(len(p),48)
      self.assertTrue(any(x.state=="swing_planned" for x in p))
      self.assertGreater(max(x.ankle_z for x in p)-min(x.ankle_z for x in p),.08)
 def test_no_bad_input(self):
    with self.assertRaises(ValueError):target(49,"front_L")
if __name__=="__main__":unittest.main()
