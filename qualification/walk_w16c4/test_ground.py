import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from ground_feasibility import original,verify,solve,THIGH,SHIN
class Independent(unittest.TestCase):
 def test_two_original_profiles(self):
  for profile in ("forward","outward"):
   r=verify(original(profile))
   self.assertEqual(r["status"],"PASS_ABSTRACT_GROUNDED_KINEMATIC_CANDIDATE_ONLY")
   self.assertEqual((r["stance_samples"],r["swing_samples"]),(48,48))
   self.assertEqual(r["max_source_stance_drift"],0)
 def test_impossible_C3_hip_z14_to_ground(self):
  self.assertGreater(1.4,THIGH+SHIN)
  with self.assertRaisesRegex(ValueError,"UNREACHABLE"):
   solve((0.,0.,1.4),(0.,0.,0.),(.25,.35,1.0))
 def test_false_planted_slip(self):
  s=original("forward")
  s["actors"][0]["frames"][1]["legs"][0]["ankle"]=(0.,1.,0.)
  with self.assertRaisesRegex(ValueError,"STANCE_ANCHOR|PLANTED_SLIP"):verify(s)
 def test_false_stance_hover(self):
  s=original("forward")
  s["actors"][0]["frames"][0]["legs"][0]["toe"]=(0.,0.,.1)
  with self.assertRaisesRegex(ValueError,"FALSE_STANCE"):verify(s)
 def test_ground_penetration(self):
  s=original("forward")
  s["actors"][0]["frames"][0]["legs"][0]["heel"]=(0.,0.,-.1)
  with self.assertRaisesRegex(ValueError,"GROUND_PENETRATION"):verify(s)
 def test_bad_rights(self):
  s=original("forward");s["rights"]="UNADMITTED"
  with self.assertRaisesRegex(ValueError,"RIGHTS"):verify(s)
 def test_bad_clock(self):
  s=original("forward");s["actors"][1]["frames"][2]["time_den"]=24
  with self.assertRaisesRegex(ValueError,"CLOCK"):verify(s)
 def test_fake_inferred_contact(self):
  s=original("forward");s["actors"][1]["frames"][5]["legs"][1]["state"]="stance"
  with self.assertRaises(ValueError):verify(s)
if __name__=="__main__":unittest.main()
