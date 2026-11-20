import sys,math,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from lengths import segment,compare_lengths
class Calibrate(unittest.TestCase):
 def test_distance(self):self.assertAlmostEqual(segment((0,0,0),(0,.5,0)),.5)
 def test_uniform_case_still_not_proven(self):
  x=compare_lengths({"thigh":.4,"shin":.45,"foot":.2},{"thigh":.6,"shin":.675,"foot":.3})
  self.assertAlmostEqual(x["median_length_ratio"],1.5)
  self.assertFalse(x["uniform_isotropic_scale_proven"])
 def test_disproportion(self):
  x=compare_lengths({"thigh":.4,"shin":.4,"foot":.2},{"thigh":.4,"shin":.2,"foot":.1})
  self.assertGreater(x["max_min_ratio_spread"],1.9)
 def test_zero_length(self):
  with self.assertRaisesRegex(ValueError,"BOUNDS"):segment((0,0,0),(0,0,0))
 def test_spoofed_segments(self):
  with self.assertRaisesRegex(ValueError,"SEGMENT_LABEL"):compare_lengths({"thigh":.4},{"thigh":.4})
 def test_nan(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):segment((0,math.nan,0),(1,0,0))
if __name__=="__main__":unittest.main()
