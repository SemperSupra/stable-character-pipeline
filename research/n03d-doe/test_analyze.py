import importlib.util,unittest,copy,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("analyze",Path(__file__).parent/"analyze.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec2=importlib.util.spec_from_file_location("contact_doe",Path(__file__).parent/"contact_doe.py")
c=importlib.util.module_from_spec(spec2);sys.modules["contact_doe"]=c;spec2.loader.exec_module(c)
def fixture():return {"schema":"scp.n03d.synthetic_screen.v1","qualification":"RESEARCH_ONLY_NOT_NATIVE_GAIT","observations":c.run()}
class TestDoEAnalysis(unittest.TestCase):
 def test_complete(self):self.assertEqual(len(m.analyse(fixture())["blocks"]),9)
 def test_duplicate_rejected(self):
  p=fixture();p["observations"][-1]=copy.deepcopy(p["observations"][0])
  with self.assertRaises(ValueError):m.analyse(p)
 def test_missing_rejected(self):
  p=fixture();p["observations"].pop()
  with self.assertRaises(ValueError):m.analyse(p)
 def test_nonfinite_rejected(self):
  p=fixture();p["observations"][0]["metrics"]["max_penetration_m"]=float("nan")
  with self.assertRaises(ValueError):m.analyse(p)
 def test_negative_rejected(self):
  p=fixture();p["observations"][0]["metrics"]["max_floating_m"]=-1
  with self.assertRaises(ValueError):m.analyse(p)
 def test_unqualified_schema_rejected(self):
  p=fixture();p["qualification"]="MVP_ACCEPTED"
  with self.assertRaises(ValueError):m.analyse(p)
if __name__=="__main__":unittest.main()
