import unittest,numpy as np
from motion import measure,EXPECTED
class OpticControls(unittest.TestCase):
 def test_pins_full_sha256_not_truncated(self):
  for profile,cameras in EXPECTED.items():
   for camera,digest in cameras.items():
    self.assertEqual(len(digest),64,profile+'/'+camera)
 def test_static(self):
  with self.assertRaisesRegex(ValueError,"STATIC"):
   measure([np.zeros((90,160),dtype=np.uint8) for _ in range(24)])
 def test_missing_frame(self):
  with self.assertRaisesRegex(ValueError,"FRAME_COUNT"):
   measure([np.zeros((90,160),dtype=np.uint8) for _ in range(23)])
 def test_changed_pixels(self):
  frames=[]
  for i in range(24):
   a=np.zeros((90,160),dtype=np.uint8);a[25:40,20+i:35+i]=255;frames.append(a)
  x=measure(frames)
  self.assertEqual(len(x),23)
  self.assertGreater(sum(row["mean_abs_luma_delta"] for row in x),0)
if __name__=="__main__":unittest.main()
,f'{profile}/{camera}')
 def test_static(self):
  with self.assertRaisesRegex(ValueError,"STATIC"):
   measure([np.zeros((90,160),dtype=np.uint8) for _ in range(24)])
 def test_missing_frame(self):
  with self.assertRaisesRegex(ValueError,"FRAME_COUNT"):
   measure([np.zeros((90,160),dtype=np.uint8) for _ in range(23)])
 def test_changed_pixels(self):
  frames=[]
  for i in range(24):
   a=np.zeros((90,160),dtype=np.uint8);a[25:40,20+i:35+i]=255;frames.append(a)
  x=measure(frames)
  self.assertEqual(len(x),23)
  self.assertGreater(sum(row["mean_abs_luma_delta"] for row in x),0)
if __name__=="__main__":unittest.main()
