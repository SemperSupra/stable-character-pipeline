import copy
import unittest

from test_challenge import fixture
from validator_quality import SCHEMA, compare, controls, measure


class ValidatorQuality(unittest.TestCase):
    def test_controlled_quality_ledger(self):
        report = measure(fixture())
        self.assertEqual(report["schema"], SCHEMA)
        self.assertEqual(report["case_count"], 11)
        self.assertEqual(report["rejection_detection"], {"detected": 9, "total": 9})
        self.assertEqual(report["false_acceptance_count"], 0)
        self.assertEqual(report["false_rejection_count"], 0)
        self.assertEqual(report["contract_mismatch_count"], 0)
        self.assertEqual(report["verdict"], "PASS_SYNTHETIC_VALIDATOR_CONTROLS_ONLY")
        self.assertEqual(report["confusion"]["ABSTAIN"]["ABSTAIN"], 1)
        self.assertFalse(report["model_promotion"])

    def test_meta_validator_detects_broken_accept_everything(self):
        report = measure(fixture(), validator=lambda _: {
            "decision": "RULE_ONLY_SYNTHETIC_IMPROVEMENT_OBSERVED"})
        self.assertEqual(report["false_acceptance_count"], 10)
        self.assertEqual(report["rejection_detection"]["detected"], 0)
        self.assertEqual(report["verdict"], "FAIL_VALIDATOR_CONTROLS")

    def test_meta_validator_detects_broken_reject_everything(self):
        from challenge import EvidenceError
        def reject_all(_):
            raise EvidenceError("broken")
        report = measure(fixture(), validator=reject_all)
        self.assertEqual(report["false_rejection_count"], 1)
        self.assertEqual(report["contract_mismatch_count"], 2)

    def test_comparable_quality_regression_and_hold_on_different_source(self):
        current = measure(fixture())
        previous = copy.deepcopy(current)
        previous["false_acceptance_count"] = -1
        self.assertEqual(compare(previous, current)["decision"], "FAIL_QUALITY_REGRESSION")
        previous = copy.deepcopy(current)
        previous["source_evidence_sha256"] = "f" * 64
        self.assertEqual(compare(previous, current)["decision"], "HOLD_DIFFERENT_CORPUS_OR_SOURCE")
        self.assertEqual(compare(current, current)["decision"], "NO_COUNT_REGRESSION_LATENCY_OBSERVATIONAL")

    def test_previous_receipt_cannot_lie_about_confusion(self):
        # Meta-validator: old source/fixture hashes do not make its own outcome
        # claims trustworthy. A forged expected/actual case must fail closed.
        current = measure(fixture())
        old = copy.deepcopy(current)
        old["cases"][1]["actual"] = "ACCEPT"
        self.assertEqual(compare(old, current)["decision"], "HOLD_MALFORMED_REFERENCE")

    def test_previous_receipt_cannot_lie_about_case_count(self):
        current = measure(fixture())
        old = copy.deepcopy(current)
        old["case_count"] = 1
        self.assertEqual(compare(old, current)["decision"], "HOLD_MALFORMED_REFERENCE")

    def test_corpus_has_unique_ids_and_unchanged_source(self):
        source = fixture()
        before = copy.deepcopy(source)
        controls_result = controls(source)
        self.assertEqual(source, before)
        self.assertEqual(len(set(name for name, _, _ in controls_result)), len(controls_result))


if __name__ == "__main__":
    unittest.main()
