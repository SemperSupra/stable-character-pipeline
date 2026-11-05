import unittest,math
from winter_fur import sample_bary,fiber,count_for
class Fur(unittest.TestCase):
 def test_weights(self):
    p,w=sample_bary((0,0,0),(1,0,0),(0,1,0),.49,.5)
    self.assertAlmostEqual(sum(w),1)
    self.assertTrue(all(0<=x<=1 for x in w))
 def test_real_taper(self):
    p,f=fiber((0,0,0),(0,0,1),.035,.001,22)
    self.assertEqual(len(p),6);self.assertEqual(len(f),4)
    self.assertGreater(math.dist(p[0],p[1]),10*math.dist(p[4],p[5]))
 def test_determinism(self):
    self.assertEqual(fiber((0,0,0),(0,0,1),.025,.001,100),
                     fiber((0,0,0),(0,0,1),.025,.001,100))
 def test_source_limits(self):
    self.assertEqual(count_for("continuous_shetland_barrel_rump_shoulder"),6500)
    self.assertEqual(count_for("front_L_upper"),210)
    self.assertEqual(count_for("continuous_front_L_limb"),680)
    self.assertEqual(count_for("nonsense"),0)
 def test_bad_data(self):
    with self.assertRaises(ValueError):fiber((0,0,0),(0,0,0),.03,.001,9)
    with self.assertRaises(ValueError):fiber((0,0,0),(0,0,1),.3,.001,9)
    with self.assertRaises(ValueError):sample_bary((0,0,0),(1,0,0),(0,1,0),-2,.1)
if __name__=="__main__":unittest.main()
