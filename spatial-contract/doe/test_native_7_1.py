"""W3c W2 7.1 strict numeric gains and speaker-order negative controls."""
import unittest
from inspect_native_7_1 import normalized_differences,TOLERANCE

class GainOracle(unittest.TestCase):
    def setUp(self):
        self.g=[.6,0,.8,0,0,0,0,0]
        self.r=[.06,0,.08,0,0,0,0,0]
    def test_exact_source_normalization(self):
        self.assertEqual(max(x for x in normalized_differences(self.r,self.g) if x is not None),0)
    def test_wrong_channel_order_detected(self):
        swapped=self.r.copy();swapped[0],swapped[1]=swapped[1],swapped[0]
        self.assertGreater(max(x for x in normalized_differences(swapped,self.g) if x is not None),TOLERANCE)
    def test_wrong_source_azimuth_detected(self):
        wrong=[0,.06,.08,0,0,0,0,0]
        self.assertGreater(max(x for x in normalized_differences(wrong,self.g) if x is not None),TOLERANCE)
    def test_nonfinite_rejected(self):
        for bad in [float('nan'),float('inf'),-1]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                r=self.r.copy();r[4]=bad;normalized_differences(r,self.g)
    def test_wrong_lfe(self):
        r=self.r.copy();r[3]=.1
        with self.assertRaises(ValueError):normalized_differences(r,self.g)
    def test_wrong_number_of_channels(self):
        with self.assertRaises(ValueError):normalized_differences(self.r[:-1],self.g)
    def test_incomplete_gain(self):
        with self.assertRaises(ValueError):normalized_differences([0]*8,self.g)
    def test_tolerance_frozen(self):
        self.assertEqual(TOLERANCE,.005)

if __name__=='__main__':unittest.main()
