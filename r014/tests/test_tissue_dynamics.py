import math,unittest
from r014.tissue_dynamics import RegionParameters,RegionController,simulate,to_morph_amplitude

SPEC=RegionParameters(mass=1.,stiffness=200.,damping=24.,max_displacement=.04)

class TissueControls(unittest.TestCase):
    def test_rest_invariance(self):
        c=RegionController(SPEC)
        for i in range(240):c.sample(0)
        self.assertEqual(c.snapshot(),(0.,0.))
    def test_nonfinite_parameters_fail(self):
        for val in (float("nan"),0.,-1.):
            with self.assertRaises(ValueError):
                RegionParameters(val,200,20,.1)
    def test_nonfinite_input_fails(self):
        with self.assertRaises(ValueError):RegionController(SPEC).sample(float('inf'))
    def test_damping_settles_after_single_inertial_impulse(self):
        c=RegionController(SPEC)
        c.sample(80.)
        initial=c.energy()
        for _ in range(240*3):c.sample(0)
        self.assertLess(c.energy(),initial*0.001)
        self.assertLess(abs(c.state.displacement),.0001)
    def test_displacement_limited(self):
        c=RegionController(SPEC)
        for _ in range(1000):
            v=c.sample(1e5)
            self.assertLessEqual(abs(v),SPEC.max_displacement+1e-12)
            self.assertTrue(math.isfinite(c.energy()))
    def test_identical_240hz_trajectories_regardless_frame_rate(self):
        driver=lambda t: 7. if t<.2 else -3. if t<.5 else 0.
        a=simulate(SPEC,24,24,driver)
        b=simulate(SPEC,60,60,driver)
        self.assertEqual(a[-1],b[-1])
    def test_morph_split_bounds(self):
        self.assertEqual(to_morph_amplitude(-.08,.04),{"positive":0.,"negative":1.})
        self.assertEqual(to_morph_amplitude(.02,.04),{"positive":.5,"negative":0.})
    def test_nondividing_rate_rejected(self):
        with self.assertRaises(ValueError):simulate(SPEC,10,29,lambda _:0.)
if __name__=="__main__":unittest.main()
