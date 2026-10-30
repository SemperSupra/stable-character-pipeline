import json,struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from source import frame,pcm,make
class Hostile(unittest.TestCase):
 def test_two_video_frames_per_motion_frame(self):
  for i in range(0,48,2):
   self.assertEqual(frame(i),frame(i+1))
   if i:self.assertNotEqual(frame(i),frame(i-2))
 def test_pcm_click_events(self):
  data=pcm()
  self.assertEqual(len(data),192000)
  for i in range(24):
   self.assertEqual(struct.unpack_from("<h",data,i*8000)[0],7500 if i%2==0 else -7500)
   self.assertEqual(struct.unpack_from("<h",data,i*8000+96)[0],0)
 def test_index_reject(self):
  for i in (-1,48):
   with self.assertRaisesRegex(ValueError,"OUTSIDE_EXACT_RANGE"):frame(i)
 def test_source_manifest_scope(self):
  with tempfile.TemporaryDirectory() as p:
   with self.assertRaisesRegex(ValueError,"PROFILE"):make(p,"unadmitted")
   make(p,"forward")
   m=json.loads((Path(p)/"source_manifest.json").read_text())
   self.assertEqual(m["source_motion_index_by_video_frame"],[i//2 for i in range(48)])
   self.assertEqual(m["source_rights"],"ORIGINAL_SELF_AUTHORED_SYNTHETIC")
if __name__=="__main__":unittest.main()
