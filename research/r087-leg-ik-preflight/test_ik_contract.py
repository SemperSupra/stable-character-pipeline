import copy,math,unittest
from ik_contract import check_side,lineage
def bones():
 d={}
 for side in ("L","R"):
  p=None
  for stem in ("upperleg01","lowerleg01","foot"):
   n=stem+"."+side
   d[n]={"parent":p,"length":.25,"head":[0,0,1],"tail":[0,0,.75]}
   p=n
 return d
class Contract(unittest.TestCase):
 def test_connected_hierarchy_is_provisional(self):
  o=check_side(bones(),"L")
  self.assertEqual(o["status"],"STRUCTURAL_CHAIN_CANDIDATE_NOT_ANATOMICAL_IK")
  self.assertFalse(o["true_joint_centres_accepted"])
 def test_missing_leg_rejected(self):
  d=bones();del d["foot.L"]
  with self.assertRaisesRegex(ValueError,"REQUIRED_LEG_BONE_MISSING"):check_side(d,"L")
 def test_wrong_parent_chain_held(self):
  d=bones();d["foot.R"]["parent"]=None
  self.assertEqual(check_side(d,"R")["status"],"HOLD_RIG_CHAIN_HIERARCHY")
 def test_degenerate_length_rejected(self):
  d=bones();d["lowerleg01.L"]["length"]=0
  with self.assertRaisesRegex(ValueError,"BAD_RIG_BONE_LENGTH"):check_side(d,"L")
 def test_nonfinite_joint_rejected(self):
  d=bones();d["upperleg01.R"]["head"][2]=math.nan
  with self.assertRaisesRegex(ValueError,"BAD_JOINT_COORDINATE"):check_side(d,"R")
 def test_cycle_rejected(self):
  d=bones();d["upperleg01.L"]["parent"]="foot.L"
  with self.assertRaisesRegex(ValueError,"RIG_PARENT_CYCLE"):lineage(d,"foot.L")
 def test_ghost_parent_rejected(self):
  d=bones();d["foot.L"]["parent"]="foo"
  with self.assertRaisesRegex(ValueError,"RIG_PARENT_ABSENT"):lineage(d,"foot.L")
 def test_left_and_right_structural_separate(self):
  d=bones()
  self.assertNotEqual(check_side(d,"L")["bone_names"],check_side(d,"R")["bone_names"])
if __name__=="__main__":unittest.main()
