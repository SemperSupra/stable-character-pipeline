import unittest
import math
from facial_controls import CHANNEL_LIMITS,FRAMES,pulse,sample,timeline,validate

class FacialTests(unittest.TestCase):
    def test_48_all_bounded_and_finite(self):
        t=timeline();self.assertEqual(len(t["frames"]),FRAMES)
        for f,a in enumerate(t["frames"],1):
            self.assertEqual(a,sample(f))
            self.assertTrue(validate(a))
            self.assertEqual(set(a),set(CHANNEL_LIMITS))
    def test_independent_eyes_and_ears(self):
        self.assertNotEqual(sample(10)["blink_L"],sample(10)["blink_R"])
        self.assertNotEqual(sample(6)["ear_L_yaw_deg"],sample(6)["ear_R_yaw_deg"])
        self.assertEqual(sample(1)["blink_L"],0)
        self.assertGreater(sample(10)["blink_L"],.99)
        self.assertGreater(sample(30)["blink_R"],.99)
    def test_distinct_nostril_and_jaw_pulses(self):
        self.assertGreater(sample(22)["nostril_L"],.7)
        self.assertEqual(sample(22)["jaw_open_deg"],0)
        self.assertGreater(sample(40)["jaw_open_deg"],6.)
        self.assertEqual(sample(40)["nostril_R"],0)
    def test_bad_inputs_fail_closed(self):
        for f in (0,49,1.1,"1",None):
            with self.assertRaises(ValueError):sample(f)
        with self.assertRaises(ValueError):pulse(1,0,2)
        with self.assertRaises(ValueError):validate({})
        a=sample(10);a["blink_L"]=math.nan
        with self.assertRaises(ValueError):validate(a)
        a=sample(10);a["jaw_open_deg"]=90
        with self.assertRaises(ValueError):validate(a)

if __name__=="__main__":unittest.main()
