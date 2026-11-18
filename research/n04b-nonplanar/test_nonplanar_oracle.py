import math,unittest
from nonplanar_oracle import closest_triangle,reference_distances,wavy_mesh,queries
class Oracle(unittest.TestCase):
 def test_face_interior(self):
  x=closest_triangle((.2,.3,2.),(0,0,0),(1,0,0),(0,1,0))
  self.assertAlmostEqual(x[0],.2);self.assertAlmostEqual(x[1],.3);self.assertEqual(x[2],0)
 def test_ab_edge(self):
  self.assertEqual(closest_triangle((.4,-1.,.5),(0,0,0),(1,0,0),(0,1,0)),(.4,0.,0.))
 def test_bc_edge(self):
  x=closest_triangle((.8,.8,0.),(0,0,0),(1,0,0),(0,1,0))
  self.assertAlmostEqual(x[0],.5);self.assertAlmostEqual(x[1],.5)
 def test_c_vertex(self):
  self.assertEqual(closest_triangle((-.7,1.5,0),(0,0,0),(1,0,0),(0,1,0)),(0.,1.,0.))
 def test_degenerate_fails(self):
  with self.assertRaisesRegex(ValueError,"DEGENERATE"):closest_triangle((0,0,0),(0,0,0),(1,0,0),(2,0,0))
 def test_nonfinite_fails(self):
  with self.assertRaises(ValueError):closest_triangle((float('nan'),0,0),(0,0,0),(1,0,0),(0,1,0))
 def test_deforming_mesh_not_planar(self):
  v,t=wavy_mesh(.5)
  self.assertEqual(len(v),81);self.assertEqual(len(t),128)
  self.assertGreater(max(x[2] for x in v)-min(x[2] for x in v),.15)
 def test_deforming_same_topology(self):
  a,faces=wavy_mesh(.5);b,faces_b=wavy_mesh(1.1)
  self.assertEqual(faces,faces_b);self.assertEqual([x[:2] for x in a],[x[:2] for x in b])
  self.assertNotEqual([x[2] for x in a],[x[2] for x in b])
 def test_bad_topology(self):
  v,f=wavy_mesh(.5)
  with self.assertRaisesRegex(ValueError,"BAD_TOPOLOGY"):reference_distances(v,[(1,999,3)],queries(.5,4))
 def test_winding_invariance(self):
  v,f=wavy_mesh(.5)
  p=queries(.5,2)
  d1=reference_distances(v,f,p)
  d2=reference_distances(v,[tuple(reversed(face)) for face in f],p)
  for x,y in zip(d1,d2):self.assertAlmostEqual(x,y,places=10)
if __name__=="__main__":unittest.main()
