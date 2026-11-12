"""Unit controls for independently designed grounded/flight jumping jacks."""
import math
import unittest
import jacks_flight_ab as j

class JacksContactPhaseTests(unittest.TestCase):
    def test_explicit_closed_open_stance_are_distinct_and_stationary(self):
        # At 20 FPS, two consecutive samples within both hold intervals.
        for phase in (.0,.0416667,.0833333):
            name,s,r,c=j.contract_state(phase*1.2)
            self.assertEqual(name,"closed_stance")
            self.assertTrue(c);self.assertEqual(s,0.);self.assertEqual(r,0.)
        for phase in (.50,.5416667,.5833333):
            name,s,r,c=j.contract_state(phase*1.2)
            self.assertEqual(name,"open_stance")
            self.assertTrue(c);self.assertEqual(s,1.);self.assertEqual(r,0.)
    def test_airborne_ankles_actually_rise(self):
        for phase in (.3125,.8125):
            state,spread,rise,c=j.contract_state(phase*1.2)
            self.assertIn(state,("opening_flight","closing_flight"))
            self.assertFalse(c)
            self.assertGreater(rise,.09)
    def test_phase_endpoints_kinematically_continuous(self):
        for p in (j.CLOSED_END,j.OPEN_TOUCHDOWN,j.OPEN_END,.999999999):
            a=j.proposed_jacks(max(0,p-1e-7)*1.2,j.gen.BODIES["female"],j.gen.FOOTWEAR["sandals"])
            b=j.proposed_jacks(p*1.2,j.gen.BODIES["female"],j.gen.FOOTWEAR["sandals"])
            self.assertLess(math.dist(a[1]["left"],b[1]["left"]),1e-5)
    def test_airborne_label_is_not_grounded(self):
        for i in range(40):
            t=i/j.FPS
            state,spread,rise,contact=j.contract_state(t)
            root,feet,c,spread2=j.proposed_jacks(t,j.gen.BODIES["female"],j.gen.FOOTWEAR["sandals"])
            self.assertEqual(c["left"],contact)
            self.assertEqual(c["right"],contact)
            self.assertAlmostEqual(feet["left"][2]-j.SUPPORT_Z,rise)
            self.assertAlmostEqual(feet["right"][2]-j.SUPPORT_Z,rise)
    def test_original_generator_pointer_is_not_mutated_by_phase_controls(self):
        self.assertIs(j.gen.jumping_jacks_motion,j.ORIGINAL)

if __name__=="__main__":
    unittest.main()
