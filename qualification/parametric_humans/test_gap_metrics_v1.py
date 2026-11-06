"""Adversarial nearest-vertex proxy metric validation; no Blender required."""
import math
import unittest
from gap_metrics_v1 import summarize,SCHEMA

class GapProxyTests(unittest.TestCase):
    def test_monotonic_quantiles_and_no_false_quality_pass(self):
        x=summarize([.11,.08,.01,.03,.0,.13])
        self.assertEqual(x["sample_count"],6)
        self.assertTrue(0<=x["min_m"]<=x["p10_m"]<=x["p50_m"]<=x["p90_m"]<=x["max_m"])
        self.assertEqual(x["near_2cm_ratio"],2/6)
        self.assertEqual(x["far_10cm_ratio"],2/6)
        self.assertFalse(x["penetration_qualified"])
        self.assertFalse(x["fit_accepted"])
        self.assertIn("NOT_SURFACE_COLLISION",x["metric"])
    def test_singleton_and_all_identical(self):
        self.assertEqual(summarize([.05])["p90_m"],.05)
        self.assertEqual(summarize([0,0,0])["near_2cm_ratio"],1.0)
        self.assertEqual(summarize([.101,.101,.101])["far_10cm_ratio"],1.0)
    def test_nan_inf_negative_and_empty_fail_closed(self):
        for input_ in ([],[-.01],[math.nan],[math.inf],[-math.inf],[.05,math.nan]):
            with self.assertRaises(ValueError):
                summarize(input_)
    def test_order_independence(self):
        self.assertEqual(summarize([.9,.4,.3,.2]),summarize([.2,.3,.4,.9]))

if __name__=="__main__":
    unittest.main(verbosity=2)
