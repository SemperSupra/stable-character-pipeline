"""Hostile independent source/PCM admission mutants - no provider dependency."""
import math,struct,unittest
from observe_w4k_common import source_bytes,floats,compare,SOURCE_FRAMES,OUTPUT_FRAMES
def sample():
 return b"".join(struct.pack("<h",{0:12000,4096:15000,8192:10000}.get(i,0)) for i in range(SOURCE_FRAMES))
class TestHostility(unittest.TestCase):
 def test_source_exact(self):self.assertEqual(len(source_bytes(sample())),64)
 def test_source_mutation(self):
  x=bytearray(sample());x[100]=1
  with self.assertRaises(ValueError):source_bytes(x)
 def test_source_short(self):
  with self.assertRaises(ValueError):source_bytes(sample()[:-2])
 def test_wrong_float_size(self):
  with self.assertRaises(ValueError):floats(b"\0"*4,1)
 def test_silence(self):
  with self.assertRaises(ValueError):floats(b"\0"*(OUTPUT_FRAMES*4),1)
 def test_nan(self):
  x=bytearray(b"\0"*(OUTPUT_FRAMES*4));struct.pack_into("<f",x,0,float("nan"))
  with self.assertRaises(ValueError):floats(x,1)
 def test_inf(self):
  x=bytearray(b"\0"*(OUTPUT_FRAMES*4));struct.pack_into("<f",x,0,float("inf"))
  with self.assertRaises(ValueError):floats(x,1)
 def test_clipping(self):
  x=bytearray(b"\0"*(OUTPUT_FRAMES*4));struct.pack_into("<f",x,0,3.)
  with self.assertRaises(ValueError):floats(x,1)
 def test_no_change(self):
  x=[.01]*OUTPUT_FRAMES
  with self.assertRaises(ValueError):compare(x,x,1)
 def test_early_change(self):
  a=[.01]*OUTPUT_FRAMES;b=a[:];b[0]=.2;b[4096]=.3
  with self.assertRaises(ValueError):compare(a,b,1)
 def test_wrong_pair(self):
  with self.assertRaises(ValueError):compare([0.,1.],[0.],1)
if __name__=="__main__":unittest.main()
