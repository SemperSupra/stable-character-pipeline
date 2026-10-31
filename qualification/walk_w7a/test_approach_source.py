"""Independent hostile W7 source probe; no Blender dependency."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from approach_source import generate,verify
class WorldApproach(unittest.TestCase):
 def test_both_original_profiles_are_world_anchored(self):
  for profile in ("forward","outward"):
   s=generate(profile);r=verify(s)
   self.assertEqual(r["status"],"PASS_ORIGINAL_SOURCE_X_APPROACH_PLANTED_CONTACT_ONLY")
   self.assertAlmostEqual(r["root_separation_start"],3.3)
   self.assertAlmostEqual(r["root_separation_end"],2.64)
   self.assertLessEqual(r["max_source_ankle_frame_step"],.045)
   self.assertEqual(r["max_source_planted_heel_slip"],0)
 def test_no_disguised_static_actors(self):
  s=generate("forward")
  s["actors"][0]["frames"][15]["root_x"]=s["actors"][0]["frames"][0]["root_x"]
  with self.assertRaises(ValueError):verify(s)
 def test_no_untrusted_root_or_rights(self):
  s=generate("outward");s["rights"]="UNKNOWN_RIGHTS"
  with self.assertRaisesRegex(ValueError,"SOURCE_RIGHTS"):verify(s)
 def test_no_lateral_knee_pole(self):
  s=generate("forward");f=s["actors"][0]["frames"][8]["legs"][0]
  f["pole"]=(f["hip"][0]+.25,f["pole"][1],f["pole"][2])
  with self.assertRaisesRegex(ValueError,"LATERAL_POLE"):verify(s)
 def test_no_fake_world_planted_anchor(self):
  s=generate("forward");leg=s["actors"][0]["frames"][2]["legs"][0]
  leg["anchor"]=(leg["anchor"][0]+.03,leg["anchor"][1],0)
  with self.assertRaises(ValueError):verify(s)
if __name__=="__main__":unittest.main()
