"""Independent adversarial test of source hash and non-promoting V2 additive status."""
import hashlib,json,subprocess,tempfile,unittest
from pathlib import Path
from diagnose import analyze
class TestV2(unittest.TestCase):
 def create(self,root,moving=False):
  v=root/"source.mp4"
  expr="testsrc2=size=128x72:rate=12:duration=2" if moving else "color=c=white:s=128x72:r=12:d=2"
  subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-f","lavfi","-i",expr,"-pix_fmt","yuv420p","-c:v","libx264",str(v)],check=True,timeout=40)
  l=root/"l1.json"
  l.write_text(json.dumps({"schema":"scp.visualqa.l1_video.v1","source_sha256":hashlib.sha256(v.read_bytes()).hexdigest(),"status":"FAIL","failures":["FROZEN_L1_PARENT"]})+"\n")
  return v,l
 def test_valid_moving_keeps_fail(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);v,l=self.create(root,True);r=analyze(v,l,root/"v2.json")
   self.assertEqual(r["status"],"OBSERVATION_ONLY_PARENT_L1_FAIL")
   self.assertEqual(r["pairs"],23)
   self.assertFalse(r["can_override_parent_l1"])
 def test_static_keeps_fail(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);v,l=self.create(root);r=analyze(v,l,root/"v2.json")
   self.assertEqual(r["status"],"OBSERVATION_ONLY_PARENT_L1_FAIL")
   self.assertEqual(r["source_l1_failures"],["FROZEN_L1_PARENT"])
 def test_forged_source_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);v,l=self.create(root);x=json.loads(l.read_text());x["source_sha256"]="0"*64;l.write_text(json.dumps(x))
   with self.assertRaises(ValueError):analyze(v,l,root/"v2.json")
 def test_parent_status_cannot_be_rewritten(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);v,l=self.create(root);x=json.loads(l.read_text());x["status"]="PASS_PRODUCT";l.write_text(json.dumps(x))
   with self.assertRaises(ValueError):analyze(v,l,root/"v2.json")
if __name__=="__main__":unittest.main()
