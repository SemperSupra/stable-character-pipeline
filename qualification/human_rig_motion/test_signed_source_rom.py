import math
import os
import unittest
from signed_source_rom import FRAMES,InvalidGait,measure,sagittal,inspect

class SignedSourceGaitTests(unittest.TestCase):
    def test_exact_source_sign_axis_and_quaternion_equivalence(self):
        a=math.sin(-.7/2);w=math.cos(-.7/2)
        self.assertAlmostEqual(sagittal((a,0.,0.,w)),-.7)
        self.assertAlmostEqual(sagittal((-a,0.,0.,-w)),-.7)

    def test_source_bounded_positive_and_negative(self):
        self.assertEqual(measure([-.25]*FRAMES,(-1.3,0.))["source_limit_violations"],[])
        bad=[-.25]*FRAMES;bad[35]=.2
        self.assertEqual(measure(bad,(-1.3,0.))["source_limit_violations"],[35])

    def test_non_sagittal_rejected(self):
        for q in ((0.,.1,0.,math.sqrt(.99)),(0.,0.,.1,math.sqrt(.99))):
            with self.assertRaisesRegex(InvalidGait,"source-local X"):
                sagittal(q)

    def test_zero_norm_and_nonfinite_rejected(self):
        for q in ((0.,0.,0.,0.),(math.nan,0.,0.,1.),(0.,0.,0.,2.)):
            with self.assertRaises(InvalidGait):sagittal(q)

    def test_nonfinite_and_wrong_sample_count_rejected(self):
        with self.assertRaises(InvalidGait):measure([-.1]*(FRAMES-1),(-1.3,0.))
        vals=[-.1]*FRAMES;vals[4]=math.nan
        with self.assertRaises(InvalidGait):measure(vals,(-1.3,0.))

    def test_actual_source_glb_scientific_holds(self):
        filename=os.environ.get("SCP_ORIGINAL_HUMAN_GLB")
        if not filename:self.skipTest("source-original GLB only during native workcell")
        with open(filename,"rb") as stream:result=inspect(stream.read())
        self.assertEqual(result["tracks_observed"],12)
        self.assertEqual(result["frames_per_track"],72)
        self.assertEqual(result["source_authored_limit_verdict"],"SOURCE_LIMIT_SCREEN_PASS")
        self.assertEqual(result["independent_human_JCS"],"NOT_PROVEN")
        self.assertFalse(result["scientific_human_gait_accepted"])
        self.assertFalse(result["release_or_CPE_admission"])

if __name__=="__main__":unittest.main()
