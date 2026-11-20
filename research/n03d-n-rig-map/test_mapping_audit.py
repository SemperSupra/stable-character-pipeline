import unittest,json
from mapping_audit import qualified
def sample():
 return {"name":"MakeHuman","bones":{"upperleg01.L":"thigh.L","upperleg02.L":"thigh_twist.L",
 "upperleg01.R":"thigh.R","lowerleg01.L":"shin.L","lowerleg01.R":"shin.R",
 "foot.L":"foot.L","foot.R":"foot.R"}}
class Audit(unittest.TestCase):
 def test_missing_right_thigh_not_misreported_as_done(self):
  d=qualified(json.dumps(sample()).encode())
  self.assertTrue(d["missing_source_target_right_thigh_twist"])
  self.assertFalse(d["physical_contact_accepted"])
 def test_upstream_already_fixed_requires_requalification(self):
  x=sample();x["bones"]["upperleg02.R"]="thigh_twist.R"
  with self.assertRaisesRegex(ValueError,"NO_MISSING_RIGHT_TWIST"):qualified(json.dumps(x).encode())
 def test_bad_source_name(self):
  x=sample();x["name"]="Unknown"
  with self.assertRaisesRegex(ValueError,"SOURCE_MAPPING_UNSUPPORTED"):qualified(json.dumps(x).encode())
 def test_wrong_left_mapping(self):
  x=sample();x["bones"]["upperleg02.L"]="shin.L"
  with self.assertRaisesRegex(ValueError,"UPSTREAM_MAPPING_DRIFT"):qualified(json.dumps(x).encode())
 def test_unsupported_shin_subdivision(self):
  x=sample();x["bones"]["lowerleg02.L"]="shin_twist.L"
  with self.assertRaisesRegex(ValueError,"UNKNOWN_SHIN_TWIST"):qualified(json.dumps(x).encode())
 def test_oversized_source(self):
  with self.assertRaisesRegex(ValueError,"MAPPING_FILE_OVERSIZE"):qualified(b"x"*65537)
 def test_naked_json_no_bones(self):
  with self.assertRaisesRegex(ValueError,"SOURCE_MAPPING_UNSUPPORTED"):qualified(b'{"name":"MakeHuman"}')
if __name__=="__main__":unittest.main()
