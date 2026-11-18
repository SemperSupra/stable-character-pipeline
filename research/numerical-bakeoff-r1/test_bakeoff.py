import math
import unittest
import bakeoff

class NumericalTests(unittest.TestCase):
    def test_spring_stiff_baseline_fails(self):
        r=bakeoff.n01()
        self.assertTrue(r["legacy_stiff_case_falsified"])
        self.assertTrue(r["challengers_within_2e_5_m"])
        self.assertEqual(r["verdict"],"PASS_NARROW")
    def test_spring_exact_zero_force(self):
        self.assertEqual(bakeoff.spring_exact(.4,8,1,0),0)
    def test_spring_invalid_input(self):
        with self.assertRaises(ValueError):
            bakeoff.spring_integrate(float("nan"),.6,.1,.001,4,"legacy",10)
    def test_spring_nonexistent_method(self):
        with self.assertRaises(ValueError):
            bakeoff.spring_integrate(4.,.6,.1,.001,4,"fake",10)
    def test_semantic_false_pass(self):
        a={"waist":.30,"height":1.7,"volume":.060}
        b={"waist":.30,"height":1.7,"volume":.061}
        self.assertTrue(bakeoff.edit_gate(a,b,"legacy_or"))
        self.assertFalse(bakeoff.edit_gate(a,b,"target_specific"))
    def test_semantic_hostile(self):
        r=bakeoff.n02()
        self.assertEqual(r["legacy_false_passes"],1)
        self.assertTrue(r["target_specific_correct"])
        self.assertEqual(r["verdict"],"PASS_NARROW")
    def test_semantic_nonfinite_rejected(self):
        a={"waist":.3,"height":1.7,"volume":.06}
        b={"waist":float("nan"),"height":1.7,"volume":.061}
        self.assertFalse(bakeoff.edit_gate(a,b,"target_specific"))
    def test_semantic_unknown_mode(self):
        with self.assertRaises(ValueError):
            bakeoff.edit_gate({},{},"unreviewed")

if __name__=="__main__":
    unittest.main()
