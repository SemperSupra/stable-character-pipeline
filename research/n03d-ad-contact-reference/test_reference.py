"""Real finite, ground, IK, provenance and phase adversarial checks."""
import copy, math, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from reference import synthetic, assess, ik2, stance_point

class Reference(unittest.TestCase):
    def test_analytic_reference(self):
        x=assess(synthetic())
        self.assertEqual(x["reference_result"],"PASS_NARROW",x)
        self.assertEqual(x["state_counts"],dict(HEEL=12,FLAT=12,TOE=12,SWING=24))
        self.assertFalse(x["native_footwear_accepted"])
    def test_ik_nonstretch(self):
        k=ik2((.2,.75),(.1,0))
        self.assertAlmostEqual(math.dist(k,(.2,.75)),.45,6)
        self.assertAlmostEqual(math.dist(k,(.1,0)),.45,6)
    def test_unreachable(self):
        with self.assertRaisesRegex(ValueError,"UNREACHABLE"):ik2((0,1.5),(0,0))
    def test_bad_segment(self):
        with self.assertRaisesRegex(ValueError,"BAD_SEGMENTS"):ik2((0,.75),(0,0),0,.45)
    def test_foot_roll_does_not_penetrate(self):
        for state in ("HEEL","FLAT","TOE"):
            for i in range(11):
                heel,toe=stance_point(state,i/10)
                self.assertGreaterEqual(min(heel[1],toe[1]),0)
    def test_ground_penetration_rejected(self):
        d=synthetic();d["rows"][16]["heel_xy_m"][1]=-.01
        self.assertIn("GROUND_PENETRATION",assess(d)["violations"])
    def test_sliding_rejected(self):
        d=synthetic();d["rows"][18]["heel_xy_m"][0]+=.1
        self.assertIn("PERSISTENT_CONTACT_SLIDE",assess(d)["violations"])
    def test_false_contact_rejected(self):
        d=synthetic();d["rows"][15]["toe_xy_m"][1]+=.1
        self.assertIn("FLAT_NOT_PLANTED",assess(d)["violations"])
    def test_reachability_mutation(self):
        d=synthetic();d["rows"][17]["knee_xy_m"][0]+=.1
        self.assertIn("LEG_LENGTH",assess(d)["violations"])
    def test_illegal_skip(self):
        d=synthetic();d["rows"][14]["state"]="TOE"
        with self.assertRaisesRegex(ValueError,"ILLEGAL_CONTACT_TRANSITION"):assess(d)
    def test_unknown_is_not_pass(self):
        d=synthetic();d["rows"][16]["state"]="UNKNOWN"
        with self.assertRaisesRegex(ValueError,"UNKNOWN_NO_GROUND_TRUTH"):assess(d)
    def test_timebase(self):
        d=synthetic();d["rows"][23]["time_s"]+=.01
        with self.assertRaisesRegex(ValueError,"CLOCK"):assess(d)
    def test_source_rights(self):
        d=synthetic();d["source_class"]="PRIVATE_NAOMI"
        with self.assertRaisesRegex(ValueError,"PROVENANCE_OR_FORGED_RELEASE"):assess(d)
    def test_forged_promotion(self):
        d=synthetic();d["mvp_accepted"]=True
        with self.assertRaisesRegex(ValueError,"PROVENANCE_OR_FORGED_RELEASE"):assess(d)
    def test_nonfinite(self):
        d=synthetic();d["rows"][9]["knee_xy_m"][0]=math.nan
        with self.assertRaisesRegex(ValueError,"FINITE_GEOMETRY"):assess(d)

if __name__=="__main__":unittest.main()
