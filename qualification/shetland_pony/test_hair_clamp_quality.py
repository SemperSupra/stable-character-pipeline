import math
import unittest
from hair_clamp_quality import report,SCHEMA
FRAMES=(1,7,13)
def rows(value_fn=lambda f,g:.1):
    return [(f,g,("mane","forelock","tail")[g],value_fn(f,g)) for f in FRAMES for g in range(3)]
class ClampQualityTests(unittest.TestCase):
    def test_clear_not_scientific_acceptance(self):
        r=report(rows(),frames=FRAMES,guide_count=3)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertEqual(r["overall"]["verdict"],"NO_CLAMP_IN_SAMPLES_ONLY")
        self.assertFalse(r["visual_acceptance"])
        self.assertEqual(r,report(rows(),frames=FRAMES,guide_count=3))
    def test_always_saturated_falsifies_bad_validator(self):
        r=report(rows(lambda f,g:.675),frames=FRAMES,guide_count=3)
        self.assertEqual(r["overall"]["verdict"],"QUALITY_RED_CLAMP_DOMINATED")
        self.assertEqual(r["overall"]["saturated_count"],9)
        self.assertAlmostEqual(r["overall"]["max_lost_m"],.455)
        self.assertEqual(r["regions"]["mane"]["saturated_fraction"],1)
    def test_one_saturation_not_silent(self):
        r=report(rows(lambda f,g:.22 if f!=13 or g!=2 else .221),frames=FRAMES,guide_count=3)
        self.assertEqual(r["overall"]["saturated_count"],1)
        self.assertEqual(r["regions"]["tail"]["saturated_count"],1)
    def test_missing_region_abstains(self):
        r=report([(f,g,"tail",.1) for f in FRAMES for g in range(3)],frames=FRAMES,guide_count=3)
        self.assertEqual(r["regions"]["mane"]["verdict"],"NO_SAMPLES_ABSTAIN")
    def test_rejects_invalid_partial_forged_and_duplicate(self):
        a=rows()
        for bad in (a[:-1],a+[a[0]],a[:-1]+[a[0]],
                    a[:-1]+[(13,2,"tail",math.nan)],
                    a[:-1]+[(13,2,"tail",-1)],
                    a[:-1]+[(13,2,"invalid",.1)],
                    a[:-1]+[(13,3,"tail",.1)]):
            with self.subTest(bad=str(bad[-1])):
                with self.assertRaises(ValueError):report(bad,frames=FRAMES,guide_count=3)
        with self.assertRaises(ValueError):report(a,frames=(1,1,13),guide_count=3)
        with self.assertRaises(ValueError):report(a,frames=FRAMES,guide_count=3,cap_m=float("nan"))
if __name__=="__main__":unittest.main()
