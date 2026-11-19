"""Original public-source R090 4.5.16 baseline regression, tamper/release negatives."""
import math,unittest
from verify_r090 import BASELINE_R090_45,compare_with_45
def fixture():
 actors=[]
 for actor,sides in BASELINE_R090_45.items():
  feet=[]
  for side,(ap,rp,asl,rsl,af,rf,flags) in sides.items():
   feet.append({"side_partition_static_rest_local_x":side,
                "authored_penetration_m":ap,"recorded_penetration_m":rp,
                "authored_slip_mps":asl,"recorded_slip_mps":rsl,
                "authored_near_ground_frames":af,"recorded_near_ground_frames":rf,
                "recorded_flags":list(flags)})
  actors.append({"actor":actor,"feet":feet})
 return {"actors":actors}
class Parity(unittest.TestCase):
 def test_original_baseline_passes(self):
  self.assertTrue(compare_with_45(fixture())["source_aware_contact_parity"])
 def test_one_micrometer_drift_allowed(self):
  f=fixture();f["actors"][0]["feet"][0]["recorded_penetration_m"]+=1e-6
  self.assertAlmostEqual(compare_with_45(f)["penetration_max_abs_delta_m"],1e-6)
 def test_large_floor_regression_refused(self):
  f=fixture();f["actors"][0]["feet"][0]["recorded_penetration_m"]+=.001
  with self.assertRaisesRegex(ValueError,"SOLe_PARITY_RED|SOLE_PARITY_RED"):compare_with_45(f)
 def test_skate_regression_refused(self):
  f=fixture();f["actors"][1]["feet"][0]["recorded_slip_mps"]+=.01
  with self.assertRaisesRegex(ValueError,"SLIP_PARITY_RED"):compare_with_45(f)
 def test_missing_foot_refused(self):
  f=fixture();f["actors"][1]["feet"].pop()
  with self.assertRaisesRegex(ValueError,"SHOE_PAIR_DRIFT"):compare_with_45(f)
 def test_unknown_anatomical_side_refused(self):
  f=fixture();f["actors"][0]["feet"][0]["side_partition_static_rest_local_x"]="left"
  with self.assertRaisesRegex(ValueError,"FOOT_INDEX_LINEAGE_DRIFT"):compare_with_45(f)
 def test_nonfinite_refused(self):
  f=fixture();f["actors"][0]["feet"][0]["recorded_penetration_m"]=float("nan")
  with self.assertRaisesRegex(ValueError,"INVALID_PENETRATION"):compare_with_45(f)
 def test_flags_refused(self):
  f=fixture();f["actors"][0]["feet"][0]["recorded_flags"]=[]
  with self.assertRaisesRegex(ValueError,"CONTACT_DIAGNOSTIC_FLAG_DRIFT"):compare_with_45(f)
 def test_no_false_slip_refused(self):
  f=fixture();f["actors"][0]["feet"][0]["recorded_slip_mps"]=.1
  with self.assertRaisesRegex(ValueError,"FALSE_SLIP_OBSERVATION"):compare_with_45(f)
if __name__=="__main__":unittest.main()
