#!/usr/bin/env python3
"""Science-control tests for non-aggregated R009 72f experimental evidence."""
import unittest
from compare_72f_v1 import classify_proxy

class ClassifyProxyTests(unittest.TestCase):
    def test_juniper_skirt_mixed_first_native_evidence(self):
        cross,strain,overall=classify_proxy(8657,1119,.012234,.013035)
        self.assertEqual(cross,"FEWER_PAIRS_UNQUALIFIED")
        self.assertEqual(strain,"HIGHER_P99_STRAIN")
        self.assertEqual(overall,"MIXED_SURFACE_AND_STRAIN_EVIDENCE_UNQUALIFIED")

    def test_aster_pants_mixed_with_existing_strain_fail(self):
        cross,strain,overall=classify_proxy(29056,26823,.688631,.698823)
        self.assertEqual(cross,"FEWER_PAIRS_UNQUALIFIED")
        self.assertEqual(strain,"HIGHER_P99_STRAIN")
        self.assertEqual(overall,"MIXED_SURFACE_AND_STRAIN_EVIDENCE_UNQUALIFIED")

    def test_both_worse_propagates_actual_proxy_red(self):
        self.assertEqual(classify_proxy(6374,7452,.005894,.006303),
                         ("MORE_PAIRS_FAIL_PROXY","HIGHER_P99_STRAIN",
                          "DIRECTIONAL_PROXY_REGRESSION"))

    def test_fully_unchanged_not_claimed_as_pass(self):
        self.assertEqual(classify_proxy(6374,6374,.005894,.005894),
                         ("UNCHANGED","UNCHANGED","NO_MEASURABLE_PROXY_CHANGE"))

    def test_both_improve_does_not_promote(self):
        self.assertEqual(classify_proxy(100,50,.1,.05),
                         ("FEWER_PAIRS_UNQUALIFIED",
                          "LOWER_P99_STRAIN_UNQUALIFIED",
                          "DIRECTIONAL_PROXY_IMPROVEMENT_UNQUALIFIED"))

    def test_strain_only_worse_is_regression(self):
        self.assertEqual(classify_proxy(100,100,.10,.12),
                         ("UNCHANGED","HIGHER_P99_STRAIN",
                          "DIRECTIONAL_PROXY_REGRESSION"))

    def test_strain_only_better_is_unqualified(self):
        self.assertEqual(classify_proxy(100,100,.12,.10),
                         ("UNCHANGED","LOWER_P99_STRAIN_UNQUALIFIED",
                          "DIRECTIONAL_PROXY_IMPROVEMENT_UNQUALIFIED"))

    def test_count_increase_and_strain_decrease_is_mixed(self):
        self.assertEqual(classify_proxy(100,110,.12,.10),
                         ("MORE_PAIRS_FAIL_PROXY","LOWER_P99_STRAIN_UNQUALIFIED",
                          "MIXED_SURFACE_AND_STRAIN_EVIDENCE_UNQUALIFIED"))

    def test_bad_numbers_never_convert_to_success(self):
        for args in [(-1,0,.1,.1),(1,-2,.1,.1),(1,2,-.1,.1),
                     (1.2,2.,.1,.1),(1,2,float('nan'),.1),
                     (1,2,float('inf'),.1),(True,2,.1,.1)]:
            with self.subTest(args=args):
                with self.assertRaisesRegex(ValueError,"FIT_COMPARATOR_BAD_PROXY_NUMBER"):
                    classify_proxy(*args)

if __name__=="__main__":
    unittest.main()
