import math
import unittest
from profiles import point,KINDS,HALVES
from verify import expected
class Profiles(unittest.TestCase):
    def test_independent_polynomial(self):
        for kind in KINDS:
            for half in HALVES:
                for tick in range(40*32,80*32+1):
                    self.assertAlmostEqual(point(kind,half,tick/32)[0],expected(kind,half,tick),places=12)
    def test_fixed_peak_and_support(self):
        for kind in KINDS:
            for half in HALVES:
                self.assertEqual(point(kind,half,60)[0],.03)
                self.assertEqual(point(kind,half,60-half),(0.,0.))
                self.assertEqual(point(kind,half,60+half),(0.,0.))
    def test_smooth_derivative(self):
        for kind in ("cubic","quintic"):
            for half in HALVES:
                for frame in (60-half+.1,60-half/2,60-.1,60+.1,60+half/2):
                    x,d=point(kind,half,frame)
                    finite=(point(kind,half,frame+.0001)[0]-point(kind,half,frame-.0001)[0])/.0002
                    self.assertAlmostEqual(d,finite,places=8)
    def test_invalid(self):
        for args in (("unknown",10,60),("linear",0,60),("linear",True,60)):
            with self.assertRaises(ValueError):point(*args)
if __name__=="__main__":unittest.main()
