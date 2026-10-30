"""Original source-clean PTS precision controls, independent of ffmpeg execution."""
from fractions import Fraction
import unittest

class NativeContainerTickContract(unittest.TestCase):
    def test_matroska_millisecond_quantization_is_not_exact(self):
        expected=Fraction(1,24)
        decoded=Fraction(42,1000)
        self.assertGreater(abs(decoded-expected), Fraction(1,2000000))

    def test_nut_frame_native_tick_is_exact(self):
        tick_base=Fraction(1,49152)
        for i in range(48):
            self.assertEqual((i*2048)*tick_base,Fraction(i,24))

    def test_forged_tick_would_fail(self):
        self.assertNotEqual(Fraction(2047,49152), Fraction(1,24))

    def test_fractional_2997_not_rounded(self):
        frame=Fraction(1001,30000)
        self.assertNotEqual(frame,Fraction(1,30))

if __name__=="__main__":
    unittest.main()
