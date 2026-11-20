import math,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from planar import fit,transform,error
class SourceAlign(unittest.TestCase):
 def setUp(self):self.a=[(.05*i,math.sin(i*.2)) for i in range(20)]
 def test_exact(self):
  m={"scale":1.2,"cos":0.6,"sin":0.8,"dx":3.,"dy":-4.}
  b=transform(m,self.a);self.assertLess(error(transform(fit(self.a,b),self.a),b),1e-5)
 def test_rotation(self):
  m={"scale":.8,"cos":0.,"sin":1.,"dx":0.,"dy":2.}
  self.assertAlmostEqual(fit(self.a,transform(m,self.a))["sin"],1.)
 def test_reflection_not_reconstructed(self):
  b=[(x,-y) for x,y in self.a];self.assertGreater(error(transform(fit(self.a,b),self.a),b),.01)
 def test_flat_rejected(self):
  with self.assertRaisesRegex(ValueError,"DEGENERATE"):fit([[0,0]]*6,[[1,1]]*6)
 def test_bad_nan(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):fit(self.a,[[math.nan,1]]*20)
 def test_clock_rejected(self):
  with self.assertRaisesRegex(ValueError,"CLOCK_DRIFT"):fit(self.a,self.a[:-1])
 def test_scale_outlier(self):
  with self.assertRaisesRegex(ValueError,"SCALE_OUT"):fit(self.a,[(x*200,y*200) for x,y in self.a])
 def test_small_input(self):
  with self.assertRaisesRegex(ValueError,"SAMPLE_BOUNDS"):fit(self.a[:2],self.a[:2])
if __name__=="__main__":unittest.main()
