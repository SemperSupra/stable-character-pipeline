import unittest
from independent_rest import mul
class MatrixCheck(unittest.TestCase):
 def test_identity(self):
  ident=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
  self.assertEqual(mul(ident,ident),ident)
