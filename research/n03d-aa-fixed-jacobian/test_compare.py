import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from compare import error,classify
class MaterialJacobian(unittest.TestCase):
 def test_zero(self):self.assertEqual(error([0,0,0],[0,0,0]),0)
 def test_strict_better(self):self.assertTrue(classify(.001,.01)["fixed_material_prediction_more_accurate"])
 def test_worse(self):self.assertFalse(classify(.02,.001)["fixed_material_prediction_more_accurate"])
 def test_no_contact_pass(self):self.assertFalse(classify(0,0)["source_plant_contact_admitted"])
 def test_large_error(self):self.assertFalse(classify(.005,.006)["fixed_material_local_model_within_tolerance"])
 def test_nan_rejection(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):classify(math.nan,.01)
 def test_point_shape(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE_MATERIAL_POINT"):error([1,2],[0,0,0])
 def test_threshold_limit(self):
  with self.assertRaisesRegex(ValueError,"ACCEPTANCE_THRESHOLD"):classify(.001,.01,1)
if __name__=="__main__":unittest.main()
