import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from audit import summarize
def synthetic():
 return {"name":"MakeHuman","bones":{"upperleg01.L":"thigh.L","upperleg02.L":"thigh_twist.L",
 "lowerleg01.L":"shin.L","foot.L":"foot.L","upperleg01.R":"thigh.R",
 "lowerleg01.R":"shin.R","foot.R":"foot.R"}}
class Structural(unittest.TestCase):
 def test_published_gap(self):
  q=summarize(synthetic())
  self.assertEqual(q["asymmetric_leg_mapping_stems"],["upperleg02"])
  self.assertTrue(q["missing_distal_shin_both_sides"])
 def test_complete_symmetric_twist_only(self):
  x=synthetic();x["bones"]["upperleg02.R"]="thigh_twist.R"
  q=summarize(x)
  self.assertEqual(q["asymmetric_leg_mapping_stems"],[])
  self.assertTrue(q["missing_distal_shin_both_sides"])
 def test_duplicate_canonical_rejected(self):
  x=synthetic();x["bones"]["lowerleg02.L"]="shin.L"
  with self.assertRaisesRegex(ValueError,"DUPLICATE_CANONICAL"):summarize(x)
 def test_bad_name(self):
  x=synthetic();x["name"]="CUSTOM"
  with self.assertRaisesRegex(ValueError,"NOT_EXACT"):summarize(x)
 def test_absent_bones(self):
  x=synthetic();x.pop("bones")
  with self.assertRaisesRegex(ValueError,"NOT_A_BONE"):summarize(x)
 def test_source_negative_cannot_pass(self):
  self.assertFalse(summarize(synthetic())["physical_gait_accepted"])
if __name__=="__main__":unittest.main()
