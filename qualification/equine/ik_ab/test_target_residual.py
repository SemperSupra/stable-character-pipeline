import unittest
from target_residual import FEET,screen
class TestActualIKTargetResidual(unittest.TestCase):
 def fixture(self):
  return {f:[{'frame':i,'planned_world_ankle_xyz':(0,0,.2),
              'actual_world_lower_tail_xyz':(0,0,.2)} for i in range(1,49)] for f in FEET}
 def test_perfect_experiment_still_not_physics(self):
  r=screen(self.fixture())
  self.assertEqual(r['total_front_frames_over_20mm'],0)
  self.assertEqual(r['contact_physics'],'UNKNOWN')
  self.assertFalse(r['model_release_accepted'])
 def test_40mm_abnormal_rejected_as_residual(self):
  x=self.fixture();x['front_L'][4]['actual_world_lower_tail_xyz']=(.04,0,.2)
  r=screen(x)
  self.assertEqual(r['total_front_frames_over_20mm'],1)
 def test_exact_clocks(self):
  x=self.fixture();x['hind_L'][8]['frame']=7
  with self.assertRaises(ValueError):screen(x)
 def test_nonfinite_and_source_rejects(self):
  x=self.fixture();x['front_R'][8]['actual_world_lower_tail_xyz']=(float('nan'),0,.1)
  with self.assertRaises(ValueError):screen(x)
  x=self.fixture();del x['hind_R']
  with self.assertRaises(ValueError):screen(x)
 def test_unqualified_coordinate_plane_rejected(self):
  x=self.fixture();x['front_L'][8]['actual_world_lower_tail_xyz']=(10,0,0)
  with self.assertRaises(ValueError):screen(x)
if __name__=='__main__':unittest.main()
