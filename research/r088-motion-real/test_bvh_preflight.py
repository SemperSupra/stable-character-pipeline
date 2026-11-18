import sys, unittest, math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import bvh_preflight as b

def example(body=None,dt="0.016666667",count="2"):
 header="""HIERARCHY
ROOT Hips
{
 OFFSET 0 0 0
 CHANNELS 6 Xposition Yposition Zposition Yrotation Xrotation Zrotation
 JOINT LeftAnkle
 {
 OFFSET 0 -100 0
 CHANNELS 3 Yrotation Xrotation Zrotation
 End Site
 {
 OFFSET 0 -10 0
 }
 }
}
MOTION
Frames: %s
Frame Time: %s
"""%(count,dt)
 return (header+(body if body is not None else "0 100 0 0 0 0 0 0 0\n1 100 0 0 0 0 0 0 0\n")).encode()
class Contracts(unittest.TestCase):
 def test_real_fk_unit(self):
  p=b.parse_bvh(example(),strict=False)
  self.assertEqual(p["count"],2)
  self.assertAlmostEqual(b.fk(p,1)["LeftAnkle"][0],1)
  self.assertAlmostEqual(b.fk(p,1)["LeftAnkle"][1],0)
 def test_rotation_nontrivial(self):
  p=b.parse_bvh(example(body="0 100 0 0 0 0 0 0 0\n0 100 0 0 0 90 0 0 0\n"),strict=False)
  self.assertAlmostEqual(b.fk(p,1)["LeftAnkle"][0],100,places=5)
 def test_wrong_frame_count(self):
  with self.assertRaisesRegex(ValueError,"FRAME_COUNT"):b.parse_bvh(example(count="3"),strict=False)
 def test_nonfinite(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE"):b.parse_bvh(example(body="nan 100 0 0 0 0 0 0 0\n1 100 0 0 0 0 0 0 0\n"),strict=False)
 def test_bad_clock(self):
  with self.assertRaisesRegex(ValueError,"NOT_60"):b.parse_bvh(example(dt="0.033333"),strict=False)
 def test_bone_forgery(self):
  with self.assertRaisesRegex(ValueError,"SKELETON"):b.parse_bvh(example(),strict=True)
 def test_bad_source_blob(self):
  self.assertNotEqual(b.git_blob_sha(example()),b.SOURCES["Neutral_FW.bvh"])
 def test_forged_frame_number(self):
  with self.assertRaisesRegex(ValueError,"CHANNEL_VALUE_COUNT"):b.parse_bvh(example(body="0 1\n0 1\n"),strict=False)
 def test_duplicate_joints(self):
  t=example().decode().replace("End Site","JOINT LeftAnkle")
  with self.assertRaisesRegex(ValueError,"DUPLICATE_BONE"):b.parse_bvh(t.encode(),strict=False)
 def test_giant_value(self):
  with self.assertRaisesRegex(ValueError,"NONFINITE_OR_GIANT"):b.parse_bvh(example(body="1e8 100 0 0 0 0 0 0 0\n1 100 0 0 0 0 0 0 0\n"),strict=False)
 def test_bad_source_pin(self):
  with self.assertRaisesRegex(ValueError,"SOURCE_NAME_OR_BLOB_PIN"):b.qualify("not-a-source.bvh","0"*40)
if __name__=="__main__":unittest.main()
