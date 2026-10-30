"""Native Matroska integer PTS must match exact quantized source rational clock."""
import unittest
from independent_decode import validate_native_pts
class NativePTS(unittest.TestCase):
 def test_exact_matroska_clock(self):
  ticks=[(2*i*1000+24)//(2*24) for i in range(48)]
  self.assertEqual(str(validate_native_pts([str(t) for t in ticks],"1/1000",24)),"1/3000")
 def test_high_precision_clock(self):
  ticks=[i*2000 for i in range(48)]
  self.assertEqual(validate_native_pts([str(t) for t in ticks],"1/48000",24),0)
 def test_hostile_changes(self):
  base=[str((2*i*1000+24)//48) for i in range(48)]
  cases={
   "missing_frame":(base[:-1],"1/1000"),
   "rounded_wrong":(base[:20]+[str(int(base[20])+1)]+base[21:],"1/1000"),
   "regressed":(base[:17]+["0"]+base[18:],"1/1000"),
   "bad_clock":(base,"1/24"),
   "fake_clock":(base,"1/999"),
   "zero_den":(base,"1/0"),
   "bad_format":(base,"garbage"),
   "noninteger":(base[:5]+["foo"]+base[6:],"1/1000"),
  }
  for name,(ticks,clock) in cases.items():
   with self.subTest(name=name),self.assertRaises(ValueError):
    validate_native_pts(ticks,clock,24)
if __name__=="__main__":unittest.main()
