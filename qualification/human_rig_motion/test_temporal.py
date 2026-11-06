import math
import unittest
from temporal import FRAMES, InvalidModel, rotation_steps


class ExactFrameQuaternionTests(unittest.TestCase):
    def test_static_and_sign_equivalent_orientation(self):
        samples = [(0., 0., 0., 1.) for _ in range(FRAMES)]
        samples[36] = (0., 0., 0., -1.)
        self.assertEqual(rotation_steps(samples), [0.] * (FRAMES - 1))

    def test_real_nonzero_angular_step(self):
        samples = [(math.sin(.01 * t / 2), 0., 0., math.cos(.01 * t / 2))
                   for t in range(FRAMES)]
        steps = rotation_steps(samples)
        self.assertEqual(len(steps), 71)
        self.assertTrue(all(abs(v - math.degrees(.01)) < 1e-6 for v in steps))

    def test_technical_large_step_still_observed(self):
        samples = [(0., 0., 0., 1.) for _ in range(FRAMES)]
        samples[35] = (math.sin(.9), 0., 0., math.cos(.9))
        self.assertGreater(max(rotation_steps(samples)), 100.)

    def test_zero_norm_is_rejected(self):
        samples = [(0., 0., 0., 1.) for _ in range(FRAMES)]
        samples[1] = (0., 0., 0., 0.)
        with self.assertRaisesRegex(InvalidModel, "unnormalized"):
            rotation_steps(samples)

    def test_nonfinite_or_excess_norm_rejected(self):
        for bad in ((math.nan, 0., 0., 1.), (math.inf, 0., 0., 1.),
                    (0., 0., 0., 2.)):
            samples = [(0., 0., 0., 1.) for _ in range(FRAMES)]
            samples[5] = bad
            with self.assertRaises(InvalidModel):
                rotation_steps(samples)

    def test_missing_frame_is_rejected(self):
        with self.assertRaisesRegex(InvalidModel, "frame count"):
            rotation_steps([(0., 0., 0., 1.) for _ in range(FRAMES - 1)])


if __name__ == "__main__":
    unittest.main()
