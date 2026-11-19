import json,tempfile,unittest
from pathlib import Path
from admit import admit
def fake(tmp):
 a=tmp/"build.json";b=tmp/"video.json"
 a.write_text(json.dumps({"schema":"scp.r083.native"}))
 b.write_text(json.dumps({"schema":"scp.r083.dressed-144f-h264.v1","source_class":"ORIGINAL_FICTIONAL_MPFBCORE_CC0",
 "frames_decoded":144,"fps":24,"same_scene_dressed_motion":True,"biomechanics_accepted":False,
 "cloth_dynamics_accepted":False,"mvp_accepted":False,"release_authorized":False,
 "video_sha256":"a"*64,"ffmpeg_wheel_sha256":"c7e46fcec401dd990405049d2e2f475e2b397779df2519b544b8aab515195282"}))
 return a,b
class Film(unittest.TestCase):
 def check(self,change,code):
  with tempfile.TemporaryDirectory() as path:
   a,b=fake(Path(path));v=json.loads(b.read_text());change(v);b.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,code):admit(a,b,"5.2.4")
 def test_known_source(self):
  with tempfile.TemporaryDirectory() as path:
   a,b=fake(Path(path))
   self.assertEqual(admit(a,b,"5.2.4")["real_ffmpeg_decode_frames"],144)
 def test_short_video_rejected(self):self.check(lambda v:v.update(frames_decoded=143),"VIDEO_CLOCK")
 def test_third_party_source_rejected(self):self.check(lambda v:v.update(source_class="PRIVATE"),"SOURCE_SAFE")
 def test_false_mvp_rejected(self):self.check(lambda v:v.update(mvp_accepted=True),"ILLICIT_PROMOTION")
 def test_no_video_digest_rejected(self):self.check(lambda v:v.update(video_sha256=""),"MISSING_REAL_VIDEO_DIGEST")
 def test_ffmpeg_tamper_rejected(self):self.check(lambda v:v.update(ffmpeg_wheel_sha256="a"*64),"FFMPEG_WHEEL_UNTRUSTED")
 def test_runtime_mismatch(self):
  with tempfile.TemporaryDirectory() as path:
   a,b=fake(Path(path))
   with self.assertRaisesRegex(ValueError,"UNKNOWN_RUNTIME"):admit(a,b,"4.0")
if __name__=="__main__":unittest.main()
