"""Independent Python oracle negative controls, no Go import or subprocess."""
import copy,json,math,unittest
from pathlib import Path
from independent_ik import compute,process

class IndependentIKOracle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=Path(__file__).with_name("fixtures.json").read_bytes()
        cls.data=json.loads(cls.source)
    def test_cases_and_softened_state(self):
        data=process(self.source)
        self.assertEqual(len(data["cases"]),5)
        for result in data["cases"][:4]:
            self.assertTrue(result["reached"])
            self.assertEqual(result["status"],"REACHED")
            self.assertLess(result["upper_residual"],1e-8)
            self.assertLess(result["lower_residual"],1e-8)
        self.assertFalse(data["cases"][-1]["reached"])
        self.assertGreater(data["cases"][-1]["target_gap"],0)
    def test_parallel_pole_rejected(self):
        p=copy.deepcopy(self.data["cases"][0]);p["pole"]=p["target"]
        with self.assertRaises(ValueError):compute(p)
    def test_zero_direction_rejected(self):
        p=copy.deepcopy(self.data["cases"][0]);p["target"]=p["start"]
        with self.assertRaises(ValueError):compute(p)
    def test_nonfinite_rejected(self):
        p=copy.deepcopy(self.data["cases"][0]);p["pole"][0]=float("nan")
        with self.assertRaises(ValueError):compute(p)
    def test_inner_reach_rejected(self):
        p=copy.deepcopy(self.data["cases"][0]);p["upper"]=1.2;p["lower"]=.2;p["target"]=[0,1.149,0]
        with self.assertRaises(ValueError):compute(p)
    def test_wrong_rights_rejected(self):
        p=copy.deepcopy(self.data);p["source_rights"]="UNVERIFIED"
        with self.assertRaises(ValueError):process(json.dumps(p).encode())
    def test_duplicate_case_rejected(self):
        p=copy.deepcopy(self.data);p["cases"][1]["id"]=p["cases"][0]["id"]
        with self.assertRaises(ValueError):process(json.dumps(p).encode())
if __name__=="__main__":unittest.main()
