"""Adversarial temporal finite-difference regression, stdlib only."""
import math
import unittest
from temporal_profile import difference_peak

class TemporalProfileTests(unittest.TestCase):
    def test_linear_world_motion_has_zero_acceleration_and_jerk(self):
        points=[[i*0.01,0.,0.] for i in range(40)]
        m=difference_peak(points)
        self.assertAlmostEqual(m["speed_m_s"]["peak"],0.2,places=7)
        self.assertEqual(m["accel_m_s2"]["peak"],0.)
        self.assertEqual(m["jerk_m_s3"]["peak"],0.)
    def test_quadratic_motion_has_constant_acceleration_not_jerk(self):
        points=[[(i/20)**2,0.,0.] for i in range(40)]
        m=difference_peak(points)
        self.assertAlmostEqual(m["accel_m_s2"]["peak"],2.,places=7)
        self.assertAlmostEqual(m["jerk_m_s3"]["peak"],0.,places=7)
    def test_discontinuous_position_emits_positive_jerk(self):
        points=[[float(i>=20),0.,0.] for i in range(40)]
        m=difference_peak(points)
        self.assertGreater(m["jerk_m_s3"]["peak"],1000)
        self.assertIn(m["jerk_m_s3"]["at_frame"],(20,21,22))
    def test_nonfinite_rejected(self):
        points=[[0.,0.,0.] for i in range(40)]
        points[8]=[math.inf,0.,0.]
        with self.assertRaisesRegex(ValueError,"NONFINITE"):difference_peak(points)
    def test_bool_coordinate_rejected(self):
        points=[[0.,0.,0.] for i in range(40)]
        points[8]=[True,0.,0.]
        with self.assertRaisesRegex(ValueError,"NONFINITE"):difference_peak(points)
    def test_missing_frames_rejected(self):
        with self.assertRaisesRegex(ValueError,"MISSING"):difference_peak([[0.,0.,0.]])
    def test_no_thresholds_can_declared_realism_pass(self):
        d=difference_peak([[0.,0.,0.] for i in range(40)])
        self.assertEqual(set(d),{"speed_m_s","accel_m_s2","jerk_m_s3"})
        self.assertNotIn("realism_pass",d)

if __name__=="__main__":
    unittest.main()
