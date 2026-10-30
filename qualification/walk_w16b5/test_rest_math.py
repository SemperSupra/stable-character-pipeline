import json,copy,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from independent_rest import matmul,apply,verify
I=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.]
class NativeOracleTests(unittest.TestCase):
 def test_matmul_identity(self):
  self.assertEqual(matmul(I,I),I)
  self.assertEqual(apply(I,[2.,3.,4.,1.]),[2.,3.,4.,1.])
 def test_affine_compose(self):
  a=I.copy();a[3]=2
  b=I.copy();b[7]=3
  self.assertEqual(apply(matmul(a,b),[0,0,0,1])[:3],[2,3,0])
 def test_bad_schema_fail_closed(self):
  with self.assertRaisesRegex(ValueError,"SCHEMA"):
   verify({"schema":"invalid"},{"schema":"invalid"})
if __name__=="__main__":unittest.main()
