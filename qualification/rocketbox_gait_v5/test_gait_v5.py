"""Hostile pure-source guard for actual native overlay. Never certifies foot contact."""
import math
import unittest
from gait_v5 import BONES, CYCLES, FRAMES, FPS, SCHEMA, LEG_AXIS, LEG_BONES, AXIS_PROBE_ZIP_SHA256, pose_at


class NativeMeasuredAxisGaitSourceTests(unittest.TestCase):
    def test_exact_timeline_and_two_real_source_roles(self):
        self.assertEqual((FRAMES, FPS), (72, 12))
        self.assertEqual(CYCLES, 3.2)
        self.assertEqual(len(BONES), 10)
        self.assertTrue(SCHEMA.endswith(".v1"))
        self.assertEqual(LEG_AXIS, "Z")
        self.assertEqual(len(LEG_BONES), 6)
        self.assertEqual(AXIS_PROBE_ZIP_SHA256, "585f50e4d9acacaf63557098287c9caec110dbc000fae5934941eb090369b5ce")

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
                self.assertGreaterEqual(p["Bip01 L Calf"], .08-1.e-9)
                self.assertGreaterEqual(p["Bip01 R Calf"], .08-1.e-9)
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


class BoundedNativeStanceJacobianSourceTests(unittest.TestCase):
    def test_identity_jacobian_moves_both_coordinates(self):
        from gait_v5 import damped_joint_update
        a,b=damped_joint_update(((1.,0.),(0.,1.)),(.04,-.03))
        self.assertGreater(a,.03)
        self.assertLess(b,-.02)

    def test_rank_deficient_stays_bounded_and_finite(self):
        from gait_v5 import damped_joint_update
        self.assertEqual(damped_joint_update(((0.,0.),(0.,0.)),(.2,.1)),(0.,0.))
        for val in (10.,-10.):
            out=damped_joint_update(((1.,2.),(2.,4.)),(val,val))
            self.assertTrue(all(math.isfinite(x) and abs(x)<=.09 for x in out))

    def test_reject_nonfinite_and_bad_limits(self):
        from gait_v5 import damped_joint_update
        for err in ((float("nan"),0.),(float("inf"),0.)):
            with self.assertRaisesRegex(ValueError,"INVALID_STANCE_JACOBIAN"):
                damped_joint_update(((1.,0.),(0.,1.)),err)
        for bad in (-.01,0.,.26,float("nan"),True):
            with self.assertRaisesRegex(ValueError,"(BAD_STANCE|INVALID_STANCE)"):
                damped_joint_update(((1.,0.),(0.,1.)),(.1,.2),limit=bad)

    def test_require_two_dimensional_jacobian(self):
        from gait_v5 import damped_joint_update
        for J in (((1.,),),((1.,2.),),((1.,2.),(3.,4.),(5.,6.))):
            with self.assertRaisesRegex(ValueError,"BAD_STANCE_JACOBIAN"):
                damped_joint_update(J,(.1,.1))


class SourceStanceReleaseAndAbstainTests(unittest.TestCase):
    def test_low_moving_stance_is_bounded_by_time(self):
        from gait_v5 import next_tentative_stance,STANCE_MAX_AGE
        s={"side":None,"anchor_x":None,"entered":None,"cooldown":{"L":-1,"R":-1}}
        base={"L":(-2.0,.01),"R":(-2.2,.04)}
        out=[]
        for frame in range(15):
            chosen,s,_=next_tentative_stance(frame,base,s,0.)
            out.append(chosen)
        self.assertEqual(out[:STANCE_MAX_AGE+1],["L"]*(STANCE_MAX_AGE+1))
        self.assertEqual(out[STANCE_MAX_AGE+1:2*(STANCE_MAX_AGE+1)],
                         ["R"]*(STANCE_MAX_AGE+1))
        self.assertEqual(out[2*(STANCE_MAX_AGE+1)],"L")

    def test_reject_large_x_drift_and_force_swing_abstention(self):
        from gait_v5 import next_tentative_stance
        state={"side":"L","anchor_x":-2.0,"entered":0,
               "cooldown":{"L":-1,"R":-1}}
        chosen,next_state,reason=next_tentative_stance(
            3,{"L":(-1.7,.01),"R":(-1.6,.10)},state,0.)
        self.assertIsNone(chosen)
        self.assertEqual(reason,"SWING_ABSTAIN_DRIFT")
        self.assertGreater(next_state["cooldown"]["L"],3)

    def test_ineligible_raised_feet_do_not_get_stance(self):
        from gait_v5 import next_tentative_stance
        state={"side":None,"anchor_x":None,"entered":None,
               "cooldown":{"L":-1,"R":-1}}
        c,_,reason=next_tentative_stance(
            9,{"L":(0.,.1),"R":(0.,.09)},state,0.)
        self.assertIsNone(c)
        self.assertIn("SWING_ABSTAIN",reason)

    def test_nan_and_wrong_state_fails_closed(self):
        from gait_v5 import next_tentative_stance
        state={"side":None,"anchor_x":None,"entered":None,
               "cooldown":{"L":-1,"R":-1}}
        for bad in (float("nan"),float("inf")):
            with self.assertRaisesRegex(ValueError,"V5B_NONFINITE"):
                next_tentative_stance(
                    9,{"L":(bad,0.),"R":(0.,0.)},state,0.)
        with self.assertRaisesRegex(ValueError,"V5B_INVALID_CLOCK"):
            next_tentative_stance(True,{"L":(0.,0.),"R":(0.,0.)},state,0.)
