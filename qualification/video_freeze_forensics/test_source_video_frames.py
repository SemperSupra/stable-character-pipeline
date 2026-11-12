import unittest
from source_video_frames import classify,source_motion
class MotionVideoAuditTests(unittest.TestCase):
    def test_motion_without_visible_pixel_change_is_not_passed(self):
        self.assertEqual(classify(.02,0.,0.),"SOURCE_MOTION_NOT_OBSERVED_IN_VIDEO")
    def test_static_hold_is_not_inferred_freeze(self):
        self.assertEqual(classify(0.,0.,0.),"STATIONARY_SOURCE_AND_VIDEO")
    def test_both_move(self):
        self.assertEqual(classify(.03,2.3,.1),"BOTH_MOVING")
    def test_image_moves_but_source_still(self):
        self.assertEqual(classify(0.,.25,.2),"VIDEO_CHANGED_WITHOUT_SOURCE_JOINT_MOTION")
    def test_negative_or_nan_rejected(self):
        for vals in ((-.1,0,0),(0,float("nan"),0),(0,0,1.1)):
            with self.assertRaisesRegex(ValueError,"INVALID"):
                classify(*vals)
    def test_valid_source_joint_delta(self):
        a={"joints":{"a":[0.,0.,0.],"b":[1.,0.,0.]}}
        b={"joints":{"a":[0.,0.,0.],"b":[1.1,0.,0.]}}
        v,m=source_motion(a,b)
        self.assertAlmostEqual(v,.1)
        self.assertAlmostEqual(m,.05)
    def test_bad_joint_schema_rejected(self):
        with self.assertRaisesRegex(ValueError,"JOINT_SCHEMA"):
            source_motion({"joints":{"a":[0,0,0]}},{"joints":{"b":[0,0,0]}})
if __name__=="__main__":
    unittest.main()
