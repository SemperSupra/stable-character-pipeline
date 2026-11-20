import unittest,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from material import select_ids,snapshot,stats,overlap
def mesh():
 return [[i/100,0,i/10000] for i in range(200)]
class Material(unittest.TestCase):
 def test_ids_deterministic(self):
  self.assertEqual(select_ids(mesh(),list(range(100))),list(range(8)))
 def test_index_permutation_invariant(self):
  a=select_ids(mesh(),list(range(100)))
  b=select_ids(mesh(),list(reversed(range(100))))
  self.assertEqual(a,b)
 def test_snapshot_static_motion(self):
  q=snapshot(mesh(),list(range(8)))
  self.assertEqual(stats([q,q,q,q],1/24)["max_speed_mps"],0)
  self.assertFalse(stats([q,q,q,q],1/24)["physical_stance_proven"])
 def test_moving_material_detected(self):
  q=snapshot(mesh(),list(range(8)));r={"centroid_xyz_m":[q["centroid_xyz_m"][0]+.1,0,0],"min_z_m":0}
  self.assertGreater(stats([q,r,q,r],1/24)["max_speed_mps"],2)
 def test_overlap_change(self):
  self.assertAlmostEqual(overlap(list(range(8)),list(range(4,12))),1/3)
 def test_duplicate_ids_rejected(self):
  with self.assertRaisesRegex(ValueError,"UNQUALIFIED"):select_ids(mesh(),[0]*100)
 def test_mesh_index_drift_rejected(self):
  with self.assertRaisesRegex(ValueError,"MESH_INDEX"):select_ids(mesh(),list(range(99))+[201])
 def test_nan_geometry_rejected(self):
  a=mesh();a[0][1]=math.nan
  with self.assertRaisesRegex(ValueError,"NONFINITE"):select_ids(a,list(range(100)))
 def test_source_clock_negative(self):
  q=snapshot(mesh(),list(range(8)))
  with self.assertRaisesRegex(ValueError,"SOURCE_CLOCK"):stats([q]*4,0)
 def test_support_selection_policy(self):
  with self.assertRaisesRegex(ValueError,"POLICY"):select_ids(mesh(),list(range(100)),ratio=.5)
if __name__=="__main__":unittest.main()
