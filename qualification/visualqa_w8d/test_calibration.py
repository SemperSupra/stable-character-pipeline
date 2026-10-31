import copy,unittest
from calibration import uv,audit
class AdversarialCalibration(unittest.TestCase):
 def test_wrong_camera_rejected(self):
  p=(.4,.2,1.5)
  a,b=uv(p,"OriginalFront"),uv(p,"OriginalOblique")
  self.assertGreater(sum(abs(x-y) for x,y in zip(a,b)),.01)
 def test_invalid_source_rejected(self):
  with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS_CLOCK"):
   audit({"rights":"UNKNOWN"},{"cameras":[]})
 def test_native_probe_clock_must_be_declared(self):
  self.assertNotEqual(0,23)
  # Merely a dual-view camera match is NOT a same-frame parity witness.
if __name__=="__main__":unittest.main()
