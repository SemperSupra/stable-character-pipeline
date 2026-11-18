import math
import unittest
from geometry_contract import exact_square,exact_distance,grid,queries
class GeometryTruth(unittest.TestCase):
 def test_inside_projection(self):
  self.assertEqual(exact_square((.5,-.75,.2)),(.5,-.75,0.))
  self.assertAlmostEqual(exact_distance((.5,-.75,.2)),.2)
 def test_outside_corner(self):
  self.assertEqual(exact_square((3,-4,.5)),(1.,-1.,0.))
  self.assertAlmostEqual(exact_distance((3,-4,.5)),math.sqrt(13.25))
 def test_grid_topology(self):
  v,t=grid(6)
  self.assertEqual(len(v),49)
  self.assertEqual(len(t),72)
  self.assertTrue(all(len(face)==3 and len(set(face))==3 for face in t))
  self.assertTrue(all(0<=i<len(v) for face in t for i in face))
 def test_query_repeatability(self):
  self.assertEqual(queries(64),queries(64))
  self.assertNotEqual(queries(64,2),queries(64,3))
 def test_nonfinite_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"BAD_POINT_COORDINATE"):exact_distance((0,0,float("nan")))
 def test_boolean_number_rejected(self):
  with self.assertRaisesRegex(ValueError,"BAD_POINT_COORDINATE"):exact_square((True,1,1))
 def test_bad_grid(self):
  with self.assertRaisesRegex(ValueError,"INVALID_RESOLUTION"):grid(1)
 def test_bad_query_count(self):
  with self.assertRaisesRegex(ValueError,"INVALID_QUERY_COUNT"):queries(1)
if __name__=="__main__":unittest.main()
