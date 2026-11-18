import math,unittest
import fine_motion as m
class HighRate(unittest.TestCase):
 def test_timebase(self):self.assertEqual((m.FPS,m.FRAMES,m.SAMPLE_RATE),(24,144,240))
 def test_exact_duration(self):self.assertEqual(m.FRAMES/m.FPS,6)
 def test_approach(self):
  self.assertAlmostEqual(m.roots(0)[1]-m.roots(0)[0],6.7)
  self.assertAlmostEqual(m.roots(143)[1]-m.roots(143)[0],1.58)
 def test_out_of_range(self):
  for k in (-1,144):
   with self.assertRaisesRegex(ValueError,"FRAME_OUT_OF_RANGE"):m.time(k)
 def test_input_bool_rejected(self):
  with self.assertRaisesRegex(ValueError,"FRAME_OUT_OF_RANGE"):m.time(True)
 def test_all_finite(self):self.assertTrue(m.validate())
 def test_phase_independence(self):
  self.assertNotEqual(m.tissue_series(m.PHASES[0]),m.tissue_series(m.PHASES[1]))
 def test_deterministic(self):self.assertEqual(m.tissue_series(.0),m.tissue_series(.0))
 def test_bounded(self):
  self.assertTrue(all(abs(v)<=.9 for z in m.tissue_series(.0) for v in z))
 def test_nonzero_tissue(self):
  self.assertGreater(max(abs(v) for z in m.tissue_series(.4) for v in z),0.001)
 def test_bilateral_gait(self):
  a=m.pose(12,0)
  self.assertNotEqual(a["upperleg_L"],a["upperleg_R"])
 def test_nonfinite_clip_rejected(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE_CONTROL"):m.clip(math.nan,-1,1)
if __name__=="__main__":unittest.main()
