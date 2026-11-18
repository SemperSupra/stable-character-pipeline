import math,unittest
from morphology_contract import LATENTS,MEASURES,predict,jacobian,validate_measurements,check_params
class MorphologyOracle(unittest.TestCase):
 def test_dimensions(self):
  self.assertEqual(len(LATENTS),4);self.assertEqual(len(MEASURES),8)
 def test_analytic_gradient_central_difference(self):
  x=(.4,-.3,.25,.5);h=1e-5
  j=jacobian(x)
  for k in range(4):
   a=list(x);b=list(x);a[k]+=h;b[k]-=h
   p=predict(a);q=predict(b)
   for i,label in enumerate(MEASURES):
    self.assertAlmostEqual((p[label]-q[label])/(2*h),j[i][k],delta=1e-8)
 def test_repeatability(self):
  self.assertEqual(predict((0,0,0,0)),predict((0,0,0,0)))
 def test_expected_units(self):
  self.assertAlmostEqual(predict((0,0,0,0))["stature_m"],1.67)
  self.assertEqual(len(validate_measurements(predict((0,0,0,0)))),8)
 def test_nonfinite(self):
  with self.assertRaises(ValueError):predict((0,0,float('nan'),0))
 def test_unsupported_styling_dim(self):
  with self.assertRaisesRegex(ValueError,"LATENT_LAYOUT"):predict((0,0,0,0,1))
 def test_out_of_bounds(self):
  with self.assertRaisesRegex(ValueError,"LATENT_OUT_OF_BOUNDS"):predict((2,0,0,0))
 def test_wrong_measure_order(self):
  r=predict((0,0,0,0));del r["waist_span_m"]
  with self.assertRaisesRegex(ValueError,"LAYOUT_OR_LABEL"):validate_measurements(r)
 def test_nonpositive_measure(self):
  r=predict((0,0,0,0));r["stature_m"]=-1
  with self.assertRaises(ValueError):validate_measurements(r)
 def test_units_cm_fail(self):
  r={k:v*100 for k,v in predict((0,0,0,0)).items()}
  with self.assertRaises(ValueError):validate_measurements(r)
 def test_bool_as_number_rejected(self):
  with self.assertRaises(ValueError):check_params((0,False,0,0))
if __name__=="__main__":unittest.main()
