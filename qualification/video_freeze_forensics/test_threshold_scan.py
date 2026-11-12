import unittest
from threshold_scan import spans, source_motion
class ThresholdForensicTests(unittest.TestCase):
    def test_ended_interval(self):
        x=spans("freeze_start: 0.4\nfreeze_end: 0.9")
        self.assertEqual(len(x),1)
        self.assertAlmostEqual(x[0]["duration_s"],.5)
    def test_open_interval_retained(self):
        x=spans("freeze_start: 1.0",2.)
        self.assertEqual(x[0]["end_s"],2.)
    def test_end_without_start_reject(self):
        with self.assertRaisesRegex(ValueError,"END_WITHOUT_START"):
            spans("freeze_end: 0.5")
    def test_bad_clock_reject(self):
        with self.assertRaisesRegex(ValueError,"INVALID_FREEZE_SPAN_CLOCK"):
            spans("freeze_start: 1.5\nfreeze_end: 1.0")
    def test_source_moves(self):
        frames=[{"joints":{"ankle":[0.,0.,float(i)/100]}} for i in range(40)]
        result=source_motion(frames,0.,.35)
        self.assertGreater(result["max_joint_displacement_m"],0)
        self.assertEqual(result["pairs"],7)
    def test_bad_nonfinite_reject(self):
        frames=[{"joints":{"x":[0,0,0]}} for i in range(40)]
        frames[1]={"joints":{"x":[float("nan"),0,0]}}
        with self.assertRaisesRegex(ValueError,"NONFINITE_SOURCE"):
            source_motion(frames,0.,.3)
if __name__=="__main__":
    unittest.main()
