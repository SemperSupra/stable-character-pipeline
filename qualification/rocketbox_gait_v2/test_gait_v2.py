"""Hostile pure-source guard for actual native overlay. Never certifies foot contact."""
import math
import unittest
from gait_v2 import BONES, CYCLES, FRAMES, FPS, SCHEMA, pose_at


class DistancePhasedGaitSourceTests(unittest.TestCase):
    def test_exact_timeline_and_two_real_source_roles(self):
        self.assertEqual((FRAMES, FPS), (72, 12))
        self.assertEqual(CYCLES, 3.2)
        self.assertEqual(len(BONES), 10)
        self.assertTrue(SCHEMA.endswith(".v1"))

    def test_endpoint_roots_and_no_straight_line_slide_speed(self):
        self.assertAlmostEqual(pose_at(0, 0)[0], -2.9, places=6)
        self.assertAlmostEqual(pose_at(71, 0)[0], -.85, places=6)
        self.assertAlmostEqual(pose_at(0, 1)[0], 2.9, places=6)
        self.assertAlmostEqual(pose_at(71, 1)[0], .85, places=6)
        self.assertLess(pose_at(1, 0)[0]-pose_at(0, 0)[0],
                        pose_at(36, 0)[0]-pose_at(35, 0)[0])

    def test_strict_convergence_no_backwards_motion(self):
        one = [pose_at(f, 0)[0] for f in range(72)]
        two = [pose_at(f, 1)[0] for f in range(72)]
        self.assertTrue(all(a < b for a, b in zip(one, one[1:])))
        self.assertTrue(all(a > b for a, b in zip(two, two[1:])))
        self.assertTrue(all(a < b for a, b in zip(one, two)))

    def test_10_motion_channels_finite_at_every_native_tick(self):
        for actor in range(2):
            for frame in range(72):
                root, pose = pose_at(frame, actor)
                self.assertEqual(tuple(pose), BONES)
                self.assertTrue(all(math.isfinite(v) for v in (root, *pose.values())))

    def test_alternating_left_right_thigh_signs(self):
        for actor in range(2):
            for frame in range(72):
                p = pose_at(frame, actor)[1]
                self.assertAlmostEqual(p["Bip01 L Thigh"], -p["Bip01 R Thigh"], places=9)

    def test_knee_flexion_does_not_reverse_in_authored_local_axis(self):
        for actor in range(2):
            for frame in range(72):
                p = pose_at(frame, actor)[1]
                self.assertGreaterEqual(p["Bip01 L Calf"], .12-1.e-9)
                self.assertGreaterEqual(p["Bip01 R Calf"], .12-1.e-9)
        # Positive local-axis values are NOT real signed anatomical JCS.
        
    def test_start_stop_leg_amplitudes_fade(self):
        for actor in range(2):
            for frame in (0, 71):
                p = pose_at(frame, actor)[1]
                self.assertAlmostEqual(p["Bip01 L Thigh"], 0.0, places=8)
                self.assertAlmostEqual(p["Bip01 L Foot"], 0.0, places=8)
                self.assertAlmostEqual(p["Bip01 R UpperArm"], 0.0, places=8)

    def test_reject_type_coercion_and_missing_source_ticks(self):
        for invalid in (-1, 72, 999, None, True, False, 0., 36., "36", float("nan"), float("inf")):
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaisesRegex(ValueError, "INVALID_FRAME_ACTOR"):
                    pose_at(invalid, 0)

    def test_reject_extra_role_and_nonint_actor(self):
        for invalid in (-1, 2, True, False, None, 0., "0", float("nan")):
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaisesRegex(ValueError, "INVALID_FRAME_ACTOR"):
                    pose_at(18, invalid)


if __name__ == "__main__":
    unittest.main()
