import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from generate_map import apply
def upstream():
 return {"name":"MakeHuman","bones":{"upperleg01.L":"thigh.L","upperleg02.L":"thigh_twist.L",
   "lowerleg01.L":"shin.L","foot.L":"foot.L",
   "upperleg01.R":"thigh.R","lowerleg01.R":"shin.R","foot.R":"foot.R"}}
class NativeMap(unittest.TestCase):
 def test_symmetry_candidate(self):
  data=apply(upstream(),"symmetric_twist")
  self.assertEqual(data["bones"]["upperleg02.R"],"thigh_twist.R")
 def test_distal_shin_candidate(self):
  data=apply(upstream(),"distal_shin")
  self.assertEqual(data["bones"]["lowerleg02.L"],"shin.L")
  self.assertNotIn("lowerleg01.L",data["bones"])
 def test_distal_thigh_and_shin_candidate(self):
  data=apply(upstream(),"distal_thigh_shin")
  self.assertEqual(data["bones"]["upperleg02.R"],"thigh.R")
  self.assertEqual(data["bones"]["lowerleg02.R"],"shin.R")
 def test_upstream_input_unmutated(self):
  data=upstream();apply(data,"distal_shin")
  self.assertIn("lowerleg01.L",data["bones"])
 def test_unknown_variant(self):
  with self.assertRaisesRegex(ValueError,"UNKNOWN_MAPPING"):apply(upstream(),"fake")
 def test_bad_source(self):
  data=upstream();data["name"]="Other"
  with self.assertRaisesRegex(ValueError,"NOT_UPSTREAM"):apply(data,"symmetric_twist")
if __name__=="__main__":unittest.main()
