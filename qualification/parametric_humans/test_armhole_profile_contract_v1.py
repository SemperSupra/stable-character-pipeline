"""Pure-stdlib hostile validation for bounded original-fictional armhole morph."""
import math,unittest
from armhole_profile_contract_v1 import (
    delta_x,validate_amounts,valid_amount,smoothstep,
    ArmholeContractError,ACTORS,CENTER_X,CENTER_Y,RADIUS_X,RADIUS_Y)

class ArmholeProfileContract(unittest.TestCase):
    def test_center_peak(self):
        self.assertAlmostEqual(delta_x(CENTER_X,CENTER_Y,0.,.01),.01)
    def test_signed_mirror(self):
        self.assertAlmostEqual(delta_x(-CENTER_X,CENTER_Y,0.,.01),-.01)
    def test_boundary_zero(self):
        for x,y in ((CENTER_X,CENTER_Y+RADIUS_Y),
                    (CENTER_X+RADIUS_X,CENTER_Y),
                    (CENTER_X,CENTER_Y-RADIUS_Y)):
            self.assertAlmostEqual(delta_x(x,y,0.,.01),0.)
    def test_noop(self):
        self.assertEqual(delta_x(CENTER_X,CENTER_Y,0.,0.),0.)
    def test_smoothstep_bounds(self):
        for x in (-100.,-.001,0.,.5,1.,1.001,100.):
            self.assertTrue(0<=smoothstep(x)<=1.)
        self.assertAlmostEqual(smoothstep(.5),.5)
    def test_invalid_amplitude(self):
        for v in (-.01,.061,float('nan'),float('inf'),True,None,'0.01'):
            with self.assertRaises(ArmholeContractError):valid_amount(v)
    def test_invalid_geometry(self):
        for bad in (float('nan'),float('inf'),None,'1'):
            with self.assertRaises(ArmholeContractError):delta_x(bad,1.34,0.,.01)
    def test_actor_set_exact(self):
        self.assertTrue(validate_amounts(dict(zip(ACTORS,(0.,.01)))))
        for v in ({ACTORS[0]:.01},{ACTORS[1]:.01},{ACTORS[0]:.01,ACTORS[1]:.01,'Extra':.01},[],{ACTORS[0]:.01,ACTORS[1]:float('inf')}):
            with self.assertRaises(ArmholeContractError):validate_amounts(v)
    def test_bounded_field(self):
        for x in (.01,.1,.18,.22,.35):
            for y in (1.25,1.31,1.35,1.39,1.44):
                self.assertLessEqual(abs(delta_x(x,y,0.,.01)),.010000001)
if __name__=='__main__':unittest.main()
