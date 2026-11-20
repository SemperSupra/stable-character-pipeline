import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from alignment import original_index,sample_interpolated,near_ground_ratio
class Alignment(unittest.TestCase):
 def test_24hz_to60(self):self.assertAlmostEqual(original_index(1),122.5)
 def test_last_valid(self):self.assertAlmostEqual(original_index(142),475.)
 def test_no_extrapolated(self):
  with self.assertRaisesRegex(ValueError,"BOUNDS"):original_index(143)
 def test_fk_halfstep(self):
  def f(i):return {"joint":(float(i),0.,1.)}
  self.assertEqual(sample_interpolated(f,122.5,"joint"),(122.5,0.,1.))
 def test_missing_speed_unknown(self):
  self.assertIsNone(near_ground_ratio({"near_ground_p50_world_speed_mps":None},{"near_ground_p50_world_speed_mps":2.}))
 def test_real_ratio(self):
  self.assertAlmostEqual(near_ground_ratio({"near_ground_p50_world_speed_mps":.04},{"near_ground_p50_world_speed_mps":1.6}),40)
 def test_invalid_sample(self):
  with self.assertRaisesRegex(ValueError,"SOURCE_FRAME"):sample_interpolated(lambda i:{"a":(0,0,0)},2500,"a")
 def test_motion_source_not_physical_plant(self):
  self.assertIsNone(near_ground_ratio({"near_ground_p50_world_speed_mps":0},{"near_ground_p50_world_speed_mps":3.}))
if __name__=="__main__":unittest.main()
