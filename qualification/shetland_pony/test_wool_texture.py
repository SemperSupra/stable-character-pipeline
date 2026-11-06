import unittest,statistics
from wool_texture import render_pixels,shade
class Wool(unittest.TestCase):
 def test_real_streaks_not_smooth_texture(self):
    p=render_pixels((.31,.12,.07,1),64,64)
    self.assertEqual(len(p),64*64*4)
    r=p[::4]
    self.assertGreater(statistics.pstdev(r),.008)
    self.assertGreater(len(set(round(x,3) for x in r)),15)
 def test_deterministic(self):
    a=render_pixels((.2,.15,.10,1),32,32)
    self.assertEqual(a,render_pixels((.2,.15,.10,1),32,32))
 def test_bad_input(self):
    with self.assertRaises(ValueError):shade(-1,.4)
    with self.assertRaises(ValueError):render_pixels((.2,.2,.1,1),2048,2048)
    with self.assertRaises(ValueError):render_pixels((.1,.1),32,32)
if __name__=="__main__":unittest.main()
