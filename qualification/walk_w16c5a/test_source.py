"""No Blender dependency source hostile correctives."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"walk_w16c4"))
from ground_feasibility import original,verify,solve
class FirstFrameSourceAdmission(unittest.TestCase):
 def test_source_rights_and_pose(self):
  for profile in ("forward","outward"):
   p=original(profile);r=verify(p)
   self.assertEqual(r["max_source_stance_drift"],0)
   self.assertFalse(r["current_C3_can_reach_ground_with_this_rest"])
   for a in p["actors"]:
    self.assertEqual(len(a["frames"][0]["legs"]),2)
    self.assertTrue(any(l["state"]=="stance" for l in a["frames"][0]["legs"]))
 def test_wrong_source_rejected(self):
  p=original("forward");p["rights"]="PRIVATE_UNADMITTED"
  with self.assertRaises(ValueError):verify(p)
 def test_unreachable_C3_rest(self):
  with self.assertRaises(ValueError):solve((0,0,1.4),(0,0,0),(.25,.48,1.))
if __name__=="__main__":unittest.main()
