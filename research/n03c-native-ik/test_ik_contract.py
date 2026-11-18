import math,unittest
from ik_contract import chain,validate_parents,classify
def good(side):
 v=chain(side);d={a:b for a,b in zip(v,v[1:])};d[v[-1]]="pelvis."+side
 return d
class IKContract(unittest.TestCase):
 def test_chain_has_five_bones(self):
  self.assertEqual(len(chain("L")),5)
  self.assertEqual(chain("L")[0],"foot.L")
 def test_actual_structural_parentage(self):
  for side in ("L","R"):self.assertEqual(validate_parents(side,good(side)),chain(side))
 def test_missing_subdivision_rejected(self):
  q=good("L");q["lowerleg02.L"]="upperleg01.L"
  with self.assertRaisesRegex(ValueError,"UNQUALIFIED_NATIVE_CHAIN"):validate_parents("L",q)
 def test_wrong_pelvis_rejected(self):
  q=good("R");q["upperleg01.R"]="root"
  with self.assertRaises(ValueError):validate_parents("R",q)
 def test_bad_side(self):
  with self.assertRaises(ValueError):chain("A")
 def test_native_improvement_is_not_acceptance(self):
  rows=[{"before_target_error_m":x,"after_target_error_m":x*.5,
         "root_pose_drift_m":0.,"shoe_min_z_m":-.02} for x in (.02,.04,.03)]
  r=classify(rows)
  self.assertTrue(r["native_ik_effect_observed"])
  self.assertTrue(r["shoe_floor_penetration_hazard"])
  self.assertFalse(r["physical_contact_accepted"])
 def test_no_motion_does_not_pass(self):
  rows=[{"before_target_error_m":0.,"after_target_error_m":0.,"root_pose_drift_m":0.,"shoe_min_z_m":0.} for _ in range(3)]
  self.assertFalse(classify(rows)["native_ik_effect_observed"])
 def test_root_drift_refused(self):
  rows=[{"before_target_error_m":.1,"after_target_error_m":.01,
         "root_pose_drift_m":.1,"shoe_min_z_m":.0} for _ in range(3)]
  with self.assertRaisesRegex(ValueError,"ROOT_MUTATION"):classify(rows)
 def test_nan_refused(self):
  rows=[{"before_target_error_m":.1,"after_target_error_m":float('nan'),
         "root_pose_drift_m":0.,"shoe_min_z_m":.0} for _ in range(3)]
  with self.assertRaisesRegex(ValueError,"NONFINITE_POSE"):classify(rows)
if __name__=="__main__":unittest.main()
